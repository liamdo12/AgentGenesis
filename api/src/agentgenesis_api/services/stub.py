"""Fixture-backed pipeline services — provider for `AG_USE_STUB_NODES=1`.

Reads fixtures from `api/data/stub/` and produces the same on-disk artifacts
the real pipeline writes (manifest.json, summary.json, stories.json). Unplug
stub mode by deleting this file and updating the lifespan to always call
`RealServices` (see `api/data/stub/README.md`).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.logging import get_logger
from agentgenesis_api.msgraph import MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput, Story
from agentgenesis_api.services.protocols import PipelineServices
from agentgenesis_api.services.real import _RealFrames
from agentgenesis_api.synthesis.schemas import MultimodalContext

log = get_logger("agentgenesis_api.services.stub")

_STUB_MEETING_ID = "stub-meeting-1"
_STUB_MEETING_TITLE = "Stub: Requirements review session"
_STUB_ORGANIZER = "stub-organizer@example.com"


def _stub_meeting_ref(meeting_id: str) -> MeetingRef:
    return MeetingRef(
        id=meeting_id,
        title=_STUB_MEETING_TITLE,
        organizer=_STUB_ORGANIZER,
        start_iso=datetime.now(UTC) - timedelta(hours=1),
        duration_sec=30.0,
    )


@dataclass
class _StubMeetings:
    vtt_path: Path | None

    async def list_meetings(self, user: User, limit: int = 200) -> list[MeetingRef]:
        # One canned meeting keeps the frontend picker functional without Graph.
        return [_stub_meeting_ref(_STUB_MEETING_ID)]

    async def get_meeting_ref(self, user: User, meeting_id: str) -> MeetingRef:
        return _stub_meeting_ref(meeting_id)

    async def get_transcript(self, user: User, meeting_id: str) -> TranscriptArtifact:
        if self.vtt_path is None or not self.vtt_path.is_file():
            log.warning("stub.vtt.missing", path=str(self.vtt_path))
            return TranscriptArtifact(
                meeting_id=meeting_id, vtt_text="", detected_language="en"
            )
        return TranscriptArtifact(
            meeting_id=meeting_id,
            vtt_text=self.vtt_path.read_text(encoding="utf-8"),
            detected_language="en",
        )


@dataclass
class _StubRecording:
    video_path: Path | None

    async def fetch_to(self, user: User, meeting_id: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.video_path is None or not self.video_path.is_file():
            # Graceful degrade — extract_frames stub handles the missing file.
            log.warning("stub.recording.missing", path=str(self.video_path))
            return
        shutil.copy(self.video_path, dest)


@dataclass
class _StubFrames:
    real_frames: _RealFrames  # delegated when ffmpeg + recording are usable

    async def extract(
        self, recording_path: Path, run_dir: Path, settings: Settings
    ) -> dict:
        if shutil.which("ffmpeg") is None or not recording_path.is_file():
            reason = "ffmpeg unavailable" if shutil.which("ffmpeg") is None else "fixture mp4 missing"
            run_dir.mkdir(parents=True, exist_ok=True)
            canned: dict = {
                "video": {
                    "duration_sec": 30.0,
                    "frame_interval_sec": settings.frame_interval_sec,
                    "chunk_window_sec": settings.chunk_window_sec,
                },
                "chunks": [],
                "frames": [],
                "useful_frame_count": 0,
                # Picked up by the extract_frames node and surfaced as a run warning.
                "_warnings": [f"{reason} in stub mode; canned frames manifest used"],
            }
            (run_dir / "manifest.json").write_text(json.dumps(canned, indent=2))
            log.warning("stub.frames.using_canned_manifest", run_dir=str(run_dir), reason=reason)
            return canned
        return await self.real_frames.extract(recording_path, run_dir, settings)


@dataclass
class _StubSynth:
    async def summarize(
        self, ctx: MultimodalContext, run_dir: Path
    ) -> MeetingSummary:
        useful = len(ctx.selected_frames)
        summary = MeetingSummary(
            summary=(
                "Team reviewed two requirements: a dashboard date-range filter "
                "and improvements to the export feature. Decisions and an owner "
                "for the export work were captured."
            ),
            key_decisions=[
                "Date-range filter must support 7/30/custom ranges.",
                "Export will chunk at 10k rows per request and stream the response.",
            ],
            action_items=[
                "Sarah: implement export chunking; due end of sprint.",
            ],
            detected_language="en",
            frame_evidence_used=bool(useful),
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(json.dumps(summary.model_dump(), indent=2))
        return summary

    async def draft_stories(
        self, ctx: MultimodalContext, summary: MeetingSummary, run_dir: Path
    ) -> StoriesOutput:
        meeting_id = ctx.meeting.id
        meeting_title = ctx.meeting.title or "Stub meeting"
        stories = [
            Story(
                id="AG-1001",
                title="Dashboard date-range filter",
                persona="Dashboard user",
                want="filter dashboard data by 7 days, 30 days, or a custom range",
                benefit="I can focus on the timeframe relevant to my analysis",
                ac=(
                    "Given the dashboard is open, when I pick 7 days, 30 days, "
                    "or a custom range, then the metrics refresh to that window."
                ),
                tags=["dashboard", "filter"],
                priority="high",
                meeting=meeting_id,
            ),
            Story(
                id="AG-1002",
                title="Streamed, chunked CSV export",
                persona="Analyst exporting large datasets",
                want="export results in 10k-row chunks streamed back",
                benefit="I get the file faster and the server stays responsive",
                ac=(
                    "Given an export request larger than 10k rows, when I submit it, "
                    "then the server streams sequential 10k-row chunks instead of "
                    "buffering the full result."
                ),
                tags=["export", "performance"],
                priority="med",
                meeting=meeting_id,
            ),
        ]
        output = StoriesOutput(
            stories=stories,
            source_meeting_id=meeting_id,
            source_meeting_title=meeting_title,
            generated_at=datetime.now(UTC),
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "stories.json").write_text(output.model_dump_json(indent=2))
        return output


class StubServices:
    @classmethod
    def create(
        cls,
        settings: Settings,
        *,
        stub_video_path: Path | None,
        stub_vtt_path: Path | None,
    ) -> PipelineServices:
        return PipelineServices(
            settings=settings,
            meetings=_StubMeetings(stub_vtt_path),
            recording=_StubRecording(stub_video_path),
            frames=_StubFrames(_RealFrames()),
            synth=_StubSynth(),
        )
