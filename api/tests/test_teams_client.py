"""Tests for TeamsMCPClient.

We stub the `_session` async context manager so tests run without a live MCP
server. The wrapper guarantees three behaviors that matter downstream:

1. JSON / VTT payloads are normalized into our Pydantic models.
2. Tool errors map to MCPToolError; "not ready" messages map to TranscriptNotReady.
3. SDK exceptions (McpError) are mapped to MCPToolError consistently.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import (
    CallToolResult,
    ErrorData,
    ListToolsResult,
    TextContent,
    Tool,
)
from pydantic import HttpUrl

from agentgenesis_api.config import Settings
from agentgenesis_api.mcp import (
    MCPToolError,
    TeamsMCPClient,
    TranscriptNotReady,
)


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        teams_mcp_url=HttpUrl("http://localhost:3000/mcp"),
        anthropic_api_key="test",  # type: ignore[arg-type]
    )


class _FakeSession:
    """Minimal stand-in for mcp.ClientSession used in tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.tool_results: dict[str, CallToolResult] = {}
        self.tool_errors: dict[str, Exception] = {}
        self.list_tools_result: ListToolsResult = ListToolsResult(
            tools=[
                Tool(name="list_meeting_recordings", description="x", inputSchema={}),
                Tool(name="get_meeting_transcript", description="x", inputSchema={}),
                Tool(name="get_meeting_recording", description="x", inputSchema={}),
            ]
        )

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        self.calls.append((name, arguments))
        if name in self.tool_errors:
            raise self.tool_errors[name]
        return self.tool_results[name]

    async def list_tools(self) -> ListToolsResult:
        return self.list_tools_result


@pytest.fixture
def fake_client(monkeypatch) -> tuple[TeamsMCPClient, _FakeSession]:
    """Returns (client, fake_session) with `_session` patched to yield the fake."""
    fake = _FakeSession()
    client = TeamsMCPClient(_settings())

    @asynccontextmanager
    async def _session():
        yield fake

    monkeypatch.setattr(client, "_session", _session)
    return client, fake


async def test_list_tools(fake_client) -> None:
    client, _ = fake_client
    tools = await client.list_tools()
    assert tools == ["list_meeting_recordings", "get_meeting_transcript", "get_meeting_recording"]


async def test_list_meeting_recordings_normalizes(fake_client) -> None:
    client, fake = fake_client
    fake.tool_results["list_meeting_recordings"] = CallToolResult(
        content=[
            TextContent(
                type="text",
                text='[{"id":"m1","title":"Sprint","organizer":"Alice",'
                '"start_iso":"2026-05-28T10:00:00Z","duration_sec":1800}]',
            )
        ]
    )
    refs = await client.list_meeting_recordings()
    assert len(refs) == 1
    assert refs[0].id == "m1"
    assert refs[0].title == "Sprint"
    assert refs[0].start_iso == datetime(2026, 5, 28, 10, 0, 0, tzinfo=UTC)


async def test_list_meeting_recordings_wrapped_object(fake_client) -> None:
    """Some servers wrap the list in `{"recordings": [...]}`. The wrapper unwraps."""
    client, fake = fake_client
    fake.tool_results["list_meeting_recordings"] = CallToolResult(
        content=[
            TextContent(
                type="text",
                text='{"recordings": [{"id":"m1","title":"S","organizer":"A",'
                '"start_iso":"2026-05-28T10:00:00Z","duration_sec":0}]}',
            )
        ]
    )
    refs = await client.list_meeting_recordings()
    assert len(refs) == 1


async def test_get_transcript_returns_vtt(fake_client) -> None:
    client, fake = fake_client
    vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n<v Alice>Hi.</v>\n"
    fake.tool_results["get_meeting_transcript"] = CallToolResult(
        content=[TextContent(type="text", text=vtt)]
    )
    art = await client.get_transcript("m1")
    assert art.meeting_id == "m1"
    assert art.vtt_text.startswith("WEBVTT")


async def test_get_transcript_not_ready_maps_to_typed_exception(fake_client) -> None:
    """`isError=true` with a 'not ready' message → TranscriptNotReady, not MCPToolError."""
    client, fake = fake_client
    fake.tool_results["get_meeting_transcript"] = CallToolResult(
        content=[TextContent(type="text", text="transcript not ready yet")],
        isError=True,
    )
    with pytest.raises(TranscriptNotReady):
        await client.get_transcript("m1")


async def test_get_transcript_generic_error_maps_to_tool_error(fake_client) -> None:
    client, fake = fake_client
    fake.tool_results["get_meeting_transcript"] = CallToolResult(
        content=[TextContent(type="text", text="something exploded")],
        isError=True,
    )
    with pytest.raises(MCPToolError) as exc:
        await client.get_transcript("m1")
    assert exc.value.tool == "get_meeting_transcript"


async def test_get_recording_returns_signed_url(fake_client) -> None:
    client, fake = fake_client
    fake.tool_results["get_meeting_recording"] = CallToolResult(
        content=[
            TextContent(
                type="text",
                text='{"download_url":"https://example.com/rec.mp4","content_type":"video/mp4"}',
            )
        ]
    )
    art = await client.get_recording("m1")
    assert str(art.download_url) == "https://example.com/rec.mp4"
    assert art.content_type == "video/mp4"


async def test_mcp_error_from_sdk_maps_to_tool_error(fake_client) -> None:
    """McpError from the SDK is caught at the call_tool boundary."""
    client, fake = fake_client
    fake.tool_errors["list_meeting_recordings"] = McpError(
        ErrorData(code=-32603, message="server exploded")
    )
    with pytest.raises(MCPToolError):
        await client.list_meeting_recordings()
