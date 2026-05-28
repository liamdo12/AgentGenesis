"""Run schema and status enum for the extraction pipeline."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class RunStatus(StrEnum):
    PENDING = "pending"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    FETCHING_RECORDING = "fetching_recording"
    EXTRACTING_FRAMES = "extracting_frames"
    SYNTHESIZING = "synthesizing"
    DONE = "done"
    FAILED = "failed"
    # Transcript not yet produced by Teams. Run is paused; user resumes via
    # POST /runs/{id}/resume once the transcript is available.
    PENDING_TRANSCRIPT = "pending_transcript"


class Run(BaseModel):
    id: str
    meeting_id: str
    status: RunStatus
    progress: float = 0.0
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
    output_dir: str
