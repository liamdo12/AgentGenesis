"""Meeting-source clients: Microsoft Graph today, room for others later.

Renamed from `mcp` after the MCP wrapper was deleted in Phase 4 of the SSO
plan. Downstream import sites use `from agentgenesis_api.sources import ...`.
"""

from agentgenesis_api.sources.exceptions import (
    SourceCallError,
    SourceError,
    SourceTransportError,
    TranscriptNotReady,
)
from agentgenesis_api.sources.graph_client import GraphClient
from agentgenesis_api.sources.models import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
)

__all__ = [
    "GraphClient",
    "MeetingRef",
    "RecordingArtifact",
    "SourceCallError",
    "SourceError",
    "SourceTransportError",
    "TranscriptArtifact",
    "TranscriptNotReady",
]
