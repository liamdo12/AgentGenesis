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
from agentgenesis_api.mcp import (
    MCPToolError,
    TranscriptNotReady,
)
from agentgenesis_api.mcp.graph_client import GraphClient


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


# ───────────────────────── list_meeting_recordings ─────────────────────────


@respx.mock
async def test_list_meeting_recordings_calendar_walk() -> None:
    respx.get(url__startswith="https://graph.microsoft.com/v1.0/me/events").mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "evt-1",
                        "subject": "Sprint Planning",
                        "start": {"dateTime": "2026-08-22T14:00:00"},
                        "end": {"dateTime": "2026-08-22T14:30:00"},
                        "organizer": {"emailAddress": {"name": "Alice"}},
                        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/m1"},
                    }
                ]
            },
        )
    )
    # Resolve meeting by JoinWebUrl filter.
    respx.get(
        url__startswith="https://graph.microsoft.com/v1.0/me/onlineMeetings?"
    ).mock(return_value=httpx.Response(200, json={"value": [{"id": "m-resolved"}]}))
    respx.get(
        "https://graph.microsoft.com/v1.0/me/onlineMeetings/m-resolved/recordings"
    ).mock(return_value=httpx.Response(200, json={"value": [{"id": "r-1"}]}))

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert len(refs) == 1
        assert refs[0].id == "m-resolved"
        assert refs[0].title == "Sprint Planning"
        assert refs[0].organizer == "Alice"
    finally:
        await c.aclose()


@respx.mock
async def test_list_skips_events_with_no_recording() -> None:
    respx.get(url__startswith="https://graph.microsoft.com/v1.0/me/events").mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "evt-1",
                        "subject": "Empty meeting",
                        "start": {"dateTime": "2026-08-22T14:00:00"},
                        "end": {"dateTime": "2026-08-22T14:30:00"},
                        "organizer": {"emailAddress": {"name": "Alice"}},
                        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/m1"},
                    }
                ]
            },
        )
    )
    respx.get(url__startswith="https://graph.microsoft.com/v1.0/me/onlineMeetings?").mock(
        return_value=httpx.Response(200, json={"value": [{"id": "m-resolved"}]})
    )
    # No recordings.
    respx.get(
        "https://graph.microsoft.com/v1.0/me/onlineMeetings/m-resolved/recordings"
    ).mock(return_value=httpx.Response(200, json={"value": []}))

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        refs = await c.list_meeting_recordings(_user(), limit=5)
        assert refs == []
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
    respx.get(
        url__startswith="https://graph.microsoft.com/v1.0/me/events"
    ).mock(return_value=httpx.Response(403, text='{"error":{"code":"Forbidden"}}'))

    c = GraphClient(_settings(), _FakeBroker())  # type: ignore[arg-type]
    try:
        with pytest.raises(MCPToolError) as exc:
            await c.list_meeting_recordings(_user())
        assert exc.value.status == 403
    finally:
        await c.aclose()


@respx.mock
async def test_429_with_retry_after_then_succeeds() -> None:
    """429 → backoff (capped) → retry succeeds."""
    import agentgenesis_api.mcp.graph_client as gc

    original = gc._BASE_BACKOFF_SEC
    gc._BASE_BACKOFF_SEC = 0.0
    try:
        respx.get(url__startswith="https://graph.microsoft.com/v1.0/me/events").mock(
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
