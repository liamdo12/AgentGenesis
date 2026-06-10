"""Tests for GraphClient.

`respx` stubs Graph endpoints; `_FakeBroker` returns a deterministic bearer.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import SecretStr

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.msgraph import (
    MsGraphCallError,
    TranscriptNotReady,
)
from agentgenesis_api.msgraph.graph_client import GraphClient

_GETALL_URL_PREFIX = (
    "https://graph.microsoft.com/v1.0/communications/onlineMeetings/getAllRecordings"
)


class _FakeBroker:
    """Stand-in for TokenBroker."""

    async def acquire_graph_token(self, user, scopes) -> str:
        return "graph-tkn"


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        environment="dev",
        entra_tenant_id="t-1",
        entra_client_id="c-1",
        entra_client_secret="s-1",
        anthropic_api_key="x",
        use_stub_nodes=False,
    )


def _user(oid: str = "alice") -> User:
    return User(oid=oid, tid="t-1", raw_token=SecretStr("user-jwt"))


def _recording(
    *,
    rid: str,
    meeting_id: str,
    organizer: str | None = "Alice Smith",
    created: str = "2026-08-22T14:00:00Z",
    ended: str | None = "2026-08-22T14:42:00Z",
) -> dict:
    item: dict = {
        "id": rid,
        "meetingId": meeting_id,
        "createdDateTime": created,
    }
    if ended is not None:
        item["endDateTime"] = ended
    if organizer is not None:
        item["meetingOrganizer"] = {"user": {"displayName": organizer}}
    return item


# ───────────────────────── list_meeting_recordings ─────────────────────────


@respx.mock
async def test_list_returns_one_per_unique_meeting() -> None:
    """3 recordings, 2 unique meetings → 2 refs, newest first."""
    respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    _recording(rid="r1", meeting_id="m1", created="2026-08-22T14:00:00Z"),
                    _recording(rid="r2", meeting_id="m2", created="2026-08-21T10:00:00Z"),
                    # Second recording on m1, newer → wins the dedupe.
                    _recording(rid="r3", meeting_id="m1", created="2026-08-22T15:00:00Z"),
                ]
            },
        )
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert [r.id for r in refs] == ["m1", "m2"]  # m1 first (newer)
        assert refs[0].title.startswith("Alice Smith · ")
        assert refs[0].organizer == "Alice Smith"
    finally:
        await c.aclose()


@respx.mock
async def test_list_empty_response() -> None:
    respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(200, json={"value": []})
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert refs == []
    finally:
        await c.aclose()


@respx.mock
async def test_list_missing_organizer_falls_back_to_recording_label() -> None:
    respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(
            200,
            json={"value": [_recording(rid="r1", meeting_id="m1", organizer=None)]},
        )
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert len(refs) == 1
        assert refs[0].title.startswith("Recording · ")
        assert refs[0].organizer == "Unknown"
    finally:
        await c.aclose()


@respx.mock
async def test_list_missing_end_datetime_yields_zero_duration() -> None:
    respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(
            200,
            json={"value": [_recording(rid="r1", meeting_id="m1", ended=None)]},
        )
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert refs[0].duration_sec == 0.0
    finally:
        await c.aclose()


@respx.mock
async def test_list_drops_recordings_without_meeting_id() -> None:
    respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    {"id": "r1", "createdDateTime": "2026-08-22T14:00:00Z"},  # no meetingId
                    _recording(rid="r2", meeting_id="m2"),
                ]
            },
        )
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert [r.id for r in refs] == ["m2"]
    finally:
        await c.aclose()


@respx.mock
async def test_list_passes_meeting_organizer_user_id() -> None:
    """Regression: Graph requires `meetingOrganizerUserId` query param.

    The user's `oid` is the Entra Object ID; Graph's getAllRecordings
    action 400s without it.
    """
    route = respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(200, json={"value": []})
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        await c.list_meeting_recordings(_user(oid="alice-oid"), limit=5)
        called_url = str(route.calls.last.request.url)
        assert "meetingOrganizerUserId=alice-oid" in called_url
    finally:
        await c.aclose()


@respx.mock
async def test_list_issues_exactly_one_graph_call() -> None:
    """Regression guard: the rewrite collapsed 1+2N+N calls into ONE."""
    route = respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    _recording(rid="r1", meeting_id="m1"),
                    _recording(rid="r2", meeting_id="m2"),
                    _recording(rid="r3", meeting_id="m3"),
                ]
            },
        )
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        await c.list_meeting_recordings(_user(), limit=5)
        assert route.call_count == 1
    finally:
        await c.aclose()


# ───────────────────────── get_transcript ─────────────────────────


@respx.mock
async def test_get_transcript_happy_path() -> None:
    respx.get(
        "https://graph.microsoft.com/v1.0/me/onlineMeetings/m1/transcripts"
    ).mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "t-1", "createdDateTime": "2026-08-22T14:00:00Z"}]}
        )
    )
    respx.get(
        url__startswith="https://graph.microsoft.com/v1.0/me/onlineMeetings/m1/transcripts/t-1/content"
    ).mock(return_value=httpx.Response(200, text="WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhi"))

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        artifact = await c.get_transcript(_user(), "m1")
        assert artifact.vtt_text.startswith("WEBVTT")
    finally:
        await c.aclose()


@respx.mock
async def test_get_transcript_not_ready_when_empty_list() -> None:
    respx.get(
        "https://graph.microsoft.com/v1.0/me/onlineMeetings/m1/transcripts"
    ).mock(return_value=httpx.Response(200, json={"value": []}))

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        with pytest.raises(TranscriptNotReady):
            await c.get_transcript(_user(), "m1")
    finally:
        await c.aclose()


# ───────────────────────── get_recording ─────────────────────────


@respx.mock
async def test_get_recording_returns_endpoint_url() -> None:
    respx.get(
        "https://graph.microsoft.com/v1.0/me/onlineMeetings/m1/recordings"
    ).mock(return_value=httpx.Response(200, json={"value": [{"id": "r-1"}]}))

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        artifact = await c.get_recording(_user(), "m1")
        url = str(artifact.download_url)
        assert url.endswith("/recordings/r-1/content")
        assert "graph.microsoft.com" in url
    finally:
        await c.aclose()


# ───────────────────────── error mapping ─────────────────────────


@respx.mock
async def test_403_carries_status() -> None:
    respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
        return_value=httpx.Response(403, text='{"error":{"code":"Forbidden"}}')
    )

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        with pytest.raises(MsGraphCallError) as exc:
            await c.list_meeting_recordings(_user())
        assert exc.value.status == 403
    finally:
        await c.aclose()


@respx.mock
async def test_429_with_retry_after_then_succeeds() -> None:
    """429 → backoff (capped) → retry succeeds."""
    import agentgenesis_api.msgraph.graph_client as gc

    original = gc._BASE_BACKOFF_SEC
    gc._BASE_BACKOFF_SEC = 0.0
    try:
        respx.get(url__startswith=_GETALL_URL_PREFIX).mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}, text="busy"),
                httpx.Response(200, json={"value": []}),
            ]
        )
        c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
        try:
            refs = await c.list_meeting_recordings(_user())
            assert refs == []
        finally:
            await c.aclose()
    finally:
        gc._BASE_BACKOFF_SEC = original
