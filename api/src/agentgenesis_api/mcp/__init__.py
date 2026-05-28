"""Microsoft Graph client + shared exceptions for the meetings source.

The package name is `mcp` for legacy reasons — the original Teams MCP client
was deleted in Phase 4 of the SSO plan; `GraphClient` replaced it. Downstream
import sites keep using `from agentgenesis_api.mcp import GraphClient`.
"""

from agentgenesis_api.mcp.exceptions import (
    MCPToolError,
    MCPTransportError,
    TranscriptNotReady,
)
from agentgenesis_api.mcp.graph_client import GraphClient
from agentgenesis_api.mcp.models import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
)

__all__ = [
    "GraphClient",
    "MCPToolError",
    "MCPTransportError",
    "MeetingRef",
    "RecordingArtifact",
    "TranscriptArtifact",
    "TranscriptNotReady",
]
