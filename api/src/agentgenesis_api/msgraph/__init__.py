"""Microsoft Graph integration.

Houses the HTTP client that talks to Microsoft Graph for Teams meetings,
transcripts, and recordings, plus the domain models and exceptions used by
the rest of the codebase. Import: `from agentgenesis_api.msgraph import ...`.
"""

from agentgenesis_api.msgraph.exceptions import (
    MsGraphCallError,
    MsGraphError,
    MsGraphTransportError,
    TranscriptNotReady,
)
from agentgenesis_api.msgraph.graph_client import GraphClient
from agentgenesis_api.msgraph.models import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
)

__all__ = [
    "GraphClient",
    "MeetingRef",
    "RecordingArtifact",
    "MsGraphCallError",
    "MsGraphError",
    "MsGraphTransportError",
    "TranscriptArtifact",
    "TranscriptNotReady",
]
