"""Pydantic models returned by TeamsMCPClient methods.

Decouples graph nodes from MCP server response shapes. If a different server
returns different field names, normalization happens in teams_client.py — these
models stay stable.
"""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class MeetingRef(BaseModel):
    id: str
    title: str
    organizer: str
    start_iso: datetime
    duration_sec: float


class TranscriptArtifact(BaseModel):
    meeting_id: str
    vtt_text: str
    detected_language: str | None = None


class RecordingArtifact(BaseModel):
    meeting_id: str
    # MCP servers vary: some return a short-lived signed URL, others stream
    # bytes via a follow-up tool call. We always carry the URL when available;
    # fetch_recording_node falls back to a follow-up call when None.
    download_url: HttpUrl | None = None
    content_type: str = "video/mp4"
