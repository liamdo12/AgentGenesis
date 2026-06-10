"""Microsoft Graph HTTP client.

Per-call delegated tokens come from `TokenBroker.acquire_graph_token` (Phase 3
of the SSO plan), so every Graph request runs under the calling user's identity.

`list_meeting_recordings` calls a single Graph endpoint:

    GET /v1.0/me/onlineMeetings/getAllRecordings

This returns every cloud recording the signed-in user has access to (as
organizer) in one shot. We dedupe by `meetingId` (a meeting can have
multiple recording chunks if paused/resumed), keep the latest per meeting,
and build `MeetingRef` rows.

Why not the calendar walk anymore? It required `Calendars.Read` +
`OnlineMeetings.Read` scopes the app reg doesn't grant (→ 403), and it
returned upcoming events too. `getAllRecordings` needs only
`OnlineMeetingRecording.Read.All` (already in `graph_delegated_scopes`)
and returns recordings only by construction.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from agentgenesis_api.auth.token_broker import TokenBroker
from agentgenesis_api.config import Settings
from agentgenesis_api.logging import get_logger
from agentgenesis_api.msgraph.exceptions import (
    MsGraphCallError,
    MsGraphTransportError,
    TranscriptNotReady,
)
from agentgenesis_api.msgraph.models import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
)

log = get_logger("agentgenesis_api.msgraph.graph_client")

_MAX_RETRIES = 3
_BASE_BACKOFF_SEC = 1.0


class GraphClient:
    def __init__(self, settings: Settings, broker: TokenBroker):
        self._settings = settings
        self._broker = broker
        self._http = httpx.AsyncClient(
            timeout=30.0, base_url="https://graph.microsoft.com"
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ───────────────────────── public API ─────────────────────────

    async def list_meeting_recordings(self, user, limit: int = 50) -> list[MeetingRef]:
        """Return every meeting the user has at least one recording for.

        Single Graph call. Recordings deduped by `meetingId`, latest by
        `createdDateTime` wins. Sorted newest first; capped at `limit`.
        """
        url = f"/v1.0/me/onlineMeetings/getAllRecordings?$top={limit}"
        data = await self._authed_get_json(user, url)
        recordings = data.get("value", [])

        by_meeting: dict[str, dict[str, Any]] = {}
        for r in recordings:
            mid = r.get("meetingId")
            if not mid:
                continue
            prev = by_meeting.get(mid)
            if prev is None or r.get("createdDateTime", "") > prev.get("createdDateTime", ""):
                by_meeting[mid] = r

        refs = [_to_meeting_ref(r) for r in by_meeting.values()]
        refs.sort(key=lambda m: m.start_iso, reverse=True)
        return refs[:limit]

    async def get_transcript(self, user, meeting_id: str) -> TranscriptArtifact:
        """Latest transcript as VTT text."""
        list_url = f"/v1.0/me/onlineMeetings/{meeting_id}/transcripts"
        data = await self._authed_get_json(user, list_url)
        transcripts = data.get("value", [])
        if not transcripts:
            raise TranscriptNotReady(meeting_id)
        # Latest first by `createdDateTime` if present.
        transcripts.sort(key=lambda t: t.get("createdDateTime", ""), reverse=True)
        tid = transcripts[0]["id"]
        content_url = f"/v1.0/me/onlineMeetings/{meeting_id}/transcripts/{tid}/content?$format=text/vtt"
        token = await self._broker.acquire_graph_token(user, self._settings.graph_delegated_scopes)
        resp = await self._call(content_url, token=token, accept="text/vtt")
        if resp.status_code == 404:
            raise TranscriptNotReady(meeting_id)
        if resp.status_code >= 400:
            self._raise_tool_error("get_transcript", resp)
        return TranscriptArtifact(meeting_id=meeting_id, vtt_text=resp.text)

    async def get_recording(self, user, meeting_id: str) -> RecordingArtifact:
        """Return RecordingArtifact carrying the Graph URL.

        IMPORTANT: `download_url` is a Graph endpoint URL, NOT a signed URL —
        the caller MUST attach `Authorization: Bearer <graph-token>` when
        streaming the body. The `fetch_recording` node calls
        `broker.acquire_graph_token` itself for that bearer (it owns the
        streaming + disk-side logic). Per red-team Finding 4.
        """
        list_url = f"/v1.0/me/onlineMeetings/{meeting_id}/recordings"
        data = await self._authed_get_json(user, list_url)
        recordings = data.get("value", [])
        if not recordings:
            raise MsGraphCallError("get_recording", "no recordings on meeting", status=404)
        recordings.sort(key=lambda r: r.get("createdDateTime", ""), reverse=True)
        rid = recordings[0]["id"]
        return RecordingArtifact(
            meeting_id=meeting_id,
            download_url=f"https://graph.microsoft.com/v1.0/me/onlineMeetings/{meeting_id}/recordings/{rid}/content",
            content_type="video/mp4",
        )

    # ───────────────────────── internals ─────────────────────────

    async def _authed_get_json(self, user, url: str) -> dict[str, Any]:
        token = await self._broker.acquire_graph_token(user, self._settings.graph_delegated_scopes)
        resp = await self._call(url, token=token, accept="application/json")
        if resp.status_code >= 400:
            self._raise_tool_error(url, resp)
        return resp.json()

    async def _call(
        self, url: str, *, token: str, accept: str
    ) -> httpx.Response:
        """Single Graph call with Retry-After-aware backoff on 429/5xx."""
        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._http.get(
                    url,
                    headers={"Authorization": f"Bearer {token}", "Accept": accept},
                )
            except httpx.HTTPError as e:
                last_err = e
                await asyncio.sleep(_BASE_BACKOFF_SEC * (2**attempt))
                continue
            if resp.status_code in (429, 503) or 500 <= resp.status_code < 600:
                if attempt == _MAX_RETRIES - 1:
                    return resp
                retry_after = float(resp.headers.get("Retry-After", _BASE_BACKOFF_SEC * (2**attempt)))
                await asyncio.sleep(min(retry_after, 30.0))
                continue
            return resp
        # Exhausted retries due to transport errors only.
        raise MsGraphTransportError(f"Graph call to {url} failed: {last_err}")

    @staticmethod
    def _raise_tool_error(tool: str, resp: httpx.Response) -> None:
        body_excerpt = (resp.text or "")[:300]
        raise MsGraphCallError(tool, body_excerpt, status=resp.status_code)


# ───────────────────────── helpers ─────────────────────────


def _to_meeting_ref(recording: dict[str, Any]) -> MeetingRef:
    """Build a MeetingRef from a Graph `callRecording` item.

    Falls back gracefully when fields are missing — Graph occasionally
    omits `endDateTime` for in-progress recordings, and
    `meetingOrganizer` may be null for federated users.
    """
    started_at = _parse_iso(recording.get("createdDateTime") or "")
    ended_at = _parse_iso(recording.get("endDateTime") or "") if recording.get("endDateTime") else None
    duration = (ended_at - started_at).total_seconds() if ended_at else 0.0

    organizer_name = (
        ((recording.get("meetingOrganizer") or {}).get("user") or {}).get("displayName")
        or "Unknown"
    )
    title = f"{organizer_name} · {started_at.strftime('%b %d')}" if organizer_name != "Unknown" \
        else f"Recording · {started_at.strftime('%b %d')}"

    return MeetingRef(
        id=recording["meetingId"],
        title=title,
        organizer=organizer_name,
        start_iso=started_at,
        duration_sec=duration,
    )


def _parse_iso(value: str) -> datetime:
    # Graph emits "2026-05-28T10:00:00.0000000Z" — strip sub-second + add tz.
    if not value:
        return datetime.now(UTC)
    cleaned = value.rstrip("Z").split(".")[0]
    return datetime.fromisoformat(cleaned).replace(tzinfo=UTC)
