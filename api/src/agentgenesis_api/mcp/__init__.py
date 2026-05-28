"""Microsoft Teams MCP client wrapper.

Talks to a community Teams MCP server (see docs/teams-mcp-setup.md for which
server and how to set it up). Downstream graph nodes consume the typed client
methods here and never touch raw MCP transport.
"""

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
from agentgenesis_api.mcp.teams_client import TeamsMCPClient

__all__ = [
    "MCPToolError",
    "MCPTransportError",
    "MeetingRef",
    "RecordingArtifact",
    "TeamsMCPClient",
    "TranscriptArtifact",
    "TranscriptNotReady",
]
