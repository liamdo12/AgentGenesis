"""Teams MCP client wrapper over the official Python MCP SDK.

Each public method opens a fresh `ClientSession` for the duration of the call
and closes it on exit. We deliberately do NOT cache the session across calls:
caching forces the close to happen in the same anyio task that opened it,
which is fragile under concurrent graph nodes (Phase 4+). The per-call TCP +
initialize cost is negligible against ffmpeg / Claude latency.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult, TextContent

from agentgenesis_api.config import Settings
from agentgenesis_api.logging import get_logger
from agentgenesis_api.mcp.exceptions import (
    MCPToolError,
    MCPTransportError,
    TranscriptNotReady,
)
from agentgenesis_api.mcp.models import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
)

log = get_logger("agentgenesis_api.mcp")

# How long we wait for the MCP server to accept a streamable HTTP connection
# and complete the protocol handshake. Tuned conservative; downstream calls
# have their own timeouts via read_timeout_seconds on call_tool.
_CONNECT_TIMEOUT_SEC = 10.0

# Substrings the chosen MCP server might use to indicate "transcript still
# processing". Detected against tool-error messages, case-insensitive.
_TRANSCRIPT_NOT_READY_HINTS = (
    "not ready",
    "still processing",
    "transcript pending",
    "not yet available",
)


class TeamsMCPClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def aclose(self) -> None:
        """No persistent connection to close — kept on the interface so
        `app.state.mcp.aclose()` works without callers caring."""
        return None

    @asynccontextmanager
    async def _session(self):
        headers: dict[str, str] = {}
        if self._settings.teams_mcp_auth_token is not None:
            token = self._settings.teams_mcp_auth_token.get_secret_value()
            headers["Authorization"] = f"Bearer {token}"
        url = str(self._settings.teams_mcp_url)
        try:
            async with asyncio.timeout(_CONNECT_TIMEOUT_SEC):
                async with streamablehttp_client(url, headers=headers) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        yield session
        except (MCPToolError, TranscriptNotReady):
            # Bubble up domain exceptions raised inside the `yield` block.
            raise
        except TimeoutError as e:
            raise MCPTransportError(f"Timed out connecting to MCP at {url}") from e
        except Exception as e:
            raise MCPTransportError(f"Failed to reach MCP at {url}: {e}") from e

    async def list_tools(self) -> list[str]:
        async with self._session() as session:
            try:
                result = await session.list_tools()
            except McpError as e:
                raise MCPTransportError(f"list_tools failed: {e}") from e
        return [t.name for t in result.tools]

    async def list_meeting_recordings(self, limit: int = 50) -> list[MeetingRef]:
        tool = self._settings.mcp_tool_list_recordings
        result = await self._call_tool(tool, {"limit": limit})
        items = _extract_json_payload(result)
        # Some servers wrap the list in `{"recordings": [...]}` or `{"value": [...]}`.
        if isinstance(items, dict):
            items = items.get("recordings") or items.get("value") or items.get("items") or []
        if not isinstance(items, list):
            raise MCPToolError(tool, f"expected list, got {type(items).__name__}")
        return [MeetingRef.model_validate(item) for item in items]

    async def get_transcript(self, meeting_id: str) -> TranscriptArtifact:
        tool = self._settings.mcp_tool_get_transcript
        try:
            result = await self._call_tool(tool, {"meeting_id": meeting_id})
        except MCPToolError as e:
            if _looks_like_transcript_pending(e.message):
                raise TranscriptNotReady(meeting_id) from e
            raise
        text = _extract_text_payload(result)
        if text and text.lstrip().upper().startswith("WEBVTT"):
            return TranscriptArtifact(meeting_id=meeting_id, vtt_text=text)
        payload = _extract_json_payload(result)
        if isinstance(payload, dict) and "vtt_text" in payload:
            return TranscriptArtifact(
                meeting_id=meeting_id,
                vtt_text=payload["vtt_text"],
                detected_language=payload.get("detected_language"),
            )
        raise MCPToolError(tool, "no vtt_text in tool response")

    async def get_recording(self, meeting_id: str) -> RecordingArtifact:
        tool = self._settings.mcp_tool_get_recording
        result = await self._call_tool(tool, {"meeting_id": meeting_id})
        payload = _extract_json_payload(result)
        if not isinstance(payload, dict):
            raise MCPToolError(tool, "expected json object")
        return RecordingArtifact(
            meeting_id=meeting_id,
            download_url=payload.get("download_url"),
            content_type=payload.get("content_type", "video/mp4"),
        )

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        async with self._session() as session:
            try:
                result = await session.call_tool(name, arguments)
            except McpError as e:
                msg = getattr(e, "error", None)
                text = getattr(msg, "message", None) or str(e)
                raise MCPToolError(name, text) from e
        if result.isError:
            text = _extract_text_payload(result) or "tool returned isError=true"
            raise MCPToolError(name, text)
        return result


def _extract_text_payload(result: CallToolResult) -> str | None:
    for block in result.content:
        if isinstance(block, TextContent):
            return block.text
    return None


def _extract_json_payload(result: CallToolResult) -> Any:
    """Pull a JSON payload out of a tool result. Prefers structuredContent (MCP
    1.x), falls back to parsing the first TextContent block."""
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    text = _extract_text_payload(result)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def _looks_like_transcript_pending(message: str) -> bool:
    msg = (message or "").lower()
    return any(hint in msg for hint in _TRANSCRIPT_NOT_READY_HINTS)
