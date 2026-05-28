"""Internal types for the synthesis pipeline."""

from pydantic import BaseModel

from agentgenesis_api.mcp import MeetingRef


class FrameRef(BaseModel):
    chunk: int
    frame: int
    timestamp_sec: float
    path: str  # relative to the run's output_dir


class TimeWindow(BaseModel):
    start: float
    end: float
    transcript_text: str
    speakers: list[str]
    frame_paths: list[str]


class MultimodalContext(BaseModel):
    meeting: MeetingRef
    duration_sec: float
    detected_language: str
    windows: list[TimeWindow]
    selected_frames: list[FrameRef]
    frame_evidence_used: bool
