"""Exceptions raised by the meetings/recording source clients.

Originally introduced for the MCP wrapper; reused for `GraphClient` (Phase 4)
so the consuming nodes don't need source-specific branching. The names retain
the `MCP` prefix for back-compat with downstream imports — they're effectively
"source-of-meetings" exceptions now.

Distinct types so graph nodes can branch on cause:
- Transport errors → retry / mark run failed with a clear "source unreachable" message.
- Tool errors      → arbitrary server-side failures; carry HTTP status so routers
                     can map cleanly (per red-team Finding 8).
- TranscriptNotReady → expected branch for Teams' async transcript processing;
  fetch_transcript node catches this and transitions to PENDING_TRANSCRIPT
  instead of failing the run.
"""


class MCPError(Exception):
    """Base for all source-client errors."""


class MCPTransportError(MCPError):
    """Connection / transport-level failure (server unreachable, network)."""


class MCPToolError(MCPError):
    """A source call returned an error result.

    `status` carries the originating HTTP status code when available
    (Phase 4 GraphClient sets it; older MCP code paths pass None). The
    runs router and fetch nodes use it to distinguish "user lacks permission"
    (403) from "Graph is down" (5xx) without string-matching the message.
    Per red-team Finding 8.
    """

    def __init__(self, tool: str, message: str, status: int | None = None):
        super().__init__(f"{tool!r} failed: {message}")
        self.tool = tool
        self.message = message
        self.status = status


class TranscriptNotReady(MCPError):
    """Teams has not yet produced a transcript for this meeting."""

    def __init__(self, meeting_id: str):
        super().__init__(f"Transcript not ready for meeting {meeting_id!r}")
        self.meeting_id = meeting_id
