"""Microsoft Graph HTTP client.

Per-call delegated tokens come from `TokenBroker.acquire_graph_token` (Phase 3
of the SSO plan), so every Graph request runs under the calling user's identity.

`list_meeting_recordings` does a calendar walk:
  1. GET /me/events filtered by isOnlineMeeting + start date window.
  2. For each event, resolve the meeting via JoinWebUrl filter.
  3. For each meeting, GET /recordings.

Per red-team Finding 1: `/me/onlineMeetings` is NOT a listable collection.
The only supported filters are `JoinWebUrl eq '<url>'` and
`joinMeetingIdSettings/joinMeetingId eq '<id>'`. Time-window filtering happens
on `/me/events`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
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

# Calendar-walk window. Hardcoded per red-team Scope F9 (no operator knob).
_LOOKBACK_DAYS = 30
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
        """Calendar walk: events with isOnlineMeeting → resolve meeting → list recordings."""
        since = (datetime.now(UTC) - timedelta(days=_LOOKBACK_DAYS)).isoformat().replace("+00:00", "Z")
        events_url = (
            f"/v1.0/me/events?$filter=isOnlineMeeting eq true and start/dateTime ge '{since}'"
            f"&$top={min(limit, 100)}&$select=id,subject,start,organizer,onlineMeeting"
        )
        events_data = await self._authed_get_json(user, events_url)
        events = events_data.get("value", [])

        refs: list[MeetingRef] = []
        for ev in events:
            online = ev.get("onlineMeeting") or {}
            join_url = online.get("joinUrl")
            if not join_url:
                continue
            try:
                meeting = await self._resolve_meeting(user, join_url)
                # Skip meetings with no recordings — caller wants recordings only.
                if not await self._has_any_recording(user, meeting["id"]):
                    continue
            except MsGraphCallError as e:
                # Per-meeting 403/404 → skip this row, keep walking.
                log.info("graph.list.skip", meeting_id=online.get("conferenceId"), status=e.status)
                continue
            refs.append(
                MeetingRef(
                    id=meeting["id"],
                    title=ev.get("subject") or "(no subject)",
                    organizer=(ev.get("organizer") or {}).get("emailAddress", {}).get("name") or "Unknown",
                    start_iso=_parse_iso(ev["start"]["dateTime"]),
                    duration_sec=_event_duration_sec(ev),
                )
            )
            if len(refs) >= limit:
                break
        return refs

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

    async def _resolve_meeting(self, user, join_url: str) -> dict[str, Any]:
        # Single-meeting lookup by JoinWebUrl (the only supported filter).
        escaped = join_url.replace("'", "''")
        url = f"/v1.0/me/onlineMeetings?$filter=JoinWebUrl eq '{escaped}'"
        data = await self._authed_get_json(user, url)
        items = data.get("value", [])
        if not items:
            raise MsGraphCallError("resolve_meeting", "no match for join_url", status=404)
        return items[0]

    async def _has_any_recording(self, user, meeting_id: str) -> bool:
        url = f"/v1.0/me/onlineMeetings/{meeting_id}/recordings"
        data = await self._authed_get_json(user, url)
        return bool(data.get("value"))

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


def _parse_iso(value: str) -> datetime:
    # Graph emits "2026-05-28T10:00:00.0000000" — strip sub-second + add tz.
    cleaned = value.rstrip("Z").split(".")[0]
    return datetime.fromisoformat(cleaned).replace(tzinfo=UTC)


def _event_duration_sec(ev: dict[str, Any]) -> float:
    try:
        start = _parse_iso(ev["start"]["dateTime"])
        end = _parse_iso(ev["end"]["dateTime"])
        return (end - start).total_seconds()
    except (KeyError, ValueError):
        return 0.0
