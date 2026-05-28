"""Meeting summary schema, produced by the Claude summary node (Phase 6)."""

from pydantic import BaseModel, Field


class MeetingSummary(BaseModel):
    summary: str
    key_decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    detected_language: str = "en"
    # No default: synthesis node MUST set this explicitly so an audio-only run
    # can't be silently misreported as having frame evidence.
    frame_evidence_used: bool
