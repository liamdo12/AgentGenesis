"""Exceptions raised by the Teams MCP client wrapper.

Distinct types so graph nodes can branch on cause:
- Transport errors → retry / mark run failed with a clear "MCP unreachable" message.
- Tool errors    → arbitrary server-side failures; surface as-is.
- TranscriptNotReady → expected branch for Teams' async transcript processing;
  fetch_transcript node catches this and transitions to PENDING_TRANSCRIPT
  instead of failing the run.
"""


class MCPError(Exception):
    """Base for all MCP-related errors."""


class MCPTransportError(MCPError):
    """Connection / transport-level failure (server unreachable, auth, etc.)."""


class MCPToolError(MCPError):
    """A tool call returned an error result."""

    def __init__(self, tool: str, message: str):
        super().__init__(f"MCP tool {tool!r} failed: {message}")
        self.tool = tool
        self.message = message


class TranscriptNotReady(MCPError):
    """Teams has not yet produced a transcript for this meeting."""

    def __init__(self, meeting_id: str):
        super().__init__(f"Transcript not ready for meeting {meeting_id!r}")
        self.meeting_id = meeting_id
