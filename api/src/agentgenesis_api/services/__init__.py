"""Pipeline services facade — single seam for swapping real/stub/noop providers."""

from agentgenesis_api.services.noop import NoopServices
from agentgenesis_api.services.protocols import (
    ChatChunk,
    FrameExtractor,
    MeetingSource,
    PipelineServices,
    RecordingFetcher,
    Synthesizer,
)
from agentgenesis_api.services.real import RealServices
from agentgenesis_api.services.stub import StubServices

__all__ = [
    "ChatChunk",
    "FrameExtractor",
    "MeetingSource",
    "NoopServices",
    "PipelineServices",
    "RealServices",
    "RecordingFetcher",
    "StubServices",
    "Synthesizer",
]
