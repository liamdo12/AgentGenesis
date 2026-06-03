"""No-op pipeline services — used by topology tests that compile the graph
without invoking any node body.

Every method does a short asyncio.sleep then returns the empty shape the
protocol declares. `build_graph()` synthesizes a NoopServices-backed
NodeDeps when called with `deps=None` (e.g. `test_graph_topology` inspects
node/edge structure only).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.msgraph import MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput
from agentgenesis_api.services.protocols import PipelineServices
from agentgenesis_api.synthesis.schemas import MultimodalContext

_NOOP_SLEEP_SEC = 0.05


def _empty_meeting_ref(meeting_id: str = "noop") -> MeetingRef:
    return MeetingRef(
        id=meeting_id,
        title="",
        organizer="",
        start_iso=datetime.now(UTC),
        duration_sec=0.0,
    )


@dataclass
class _NoopMeetings:
    async def list_meetings(self, user: User, limit: int = 200) -> list[MeetingRef]:
        await asyncio.sleep(_NOOP_SLEEP_SEC)
        return []

    async def get_meeting_ref(self, user: User, meeting_id: str) -> MeetingRef:
        await asyncio.sleep(_NOOP_SLEEP_SEC)
        return _empty_meeting_ref(meeting_id)

    async def get_transcript(self, user: User, meeting_id: str) -> TranscriptArtifact:
        await asyncio.sleep(_NOOP_SLEEP_SEC)
        return TranscriptArtifact(meeting_id=meeting_id, vtt_text="", detected_language="en")


@dataclass
class _NoopRecording:
    async def fetch_to(self, user: User, meeting_id: str, dest: Path) -> None:
        await asyncio.sleep(_NOOP_SLEEP_SEC)


@dataclass
class _NoopFrames:
    async def extract(
        self, recording_path: Path, run_dir: Path, settings: Settings
    ) -> dict:
        await asyncio.sleep(_NOOP_SLEEP_SEC)
        return {
            "video": {
                "duration_sec": 0.0,
                "frame_interval_sec": settings.frame_interval_sec,
                "chunk_window_sec": settings.chunk_window_sec,
            },
            "chunks": [],
            "frames": [],
            "useful_frame_count": 0,
        }


@dataclass
class _NoopSynth:
    async def summarize(
        self, ctx: MultimodalContext, run_dir: Path
    ) -> MeetingSummary:
        await asyncio.sleep(_NOOP_SLEEP_SEC)
        return MeetingSummary(
            summary="",
            key_decisions=[],
            action_items=[],
            detected_language="en",
            frame_evidence_used=False,
        )

    async def draft_stories(
        self, ctx: MultimodalContext, summary: MeetingSummary, run_dir: Path
    ) -> StoriesOutput:
        await asyncio.sleep(_NOOP_SLEEP_SEC)
        return StoriesOutput(
            stories=[],
            source_meeting_id=ctx.meeting.id if ctx else "",
            source_meeting_title=ctx.meeting.title if ctx else "",
            generated_at=datetime.now(UTC),
        )


class NoopServices:
    @classmethod
    def create(cls, settings: Settings | None = None) -> PipelineServices:
        # settings is optional — topology tests construct without one. We
        # synthesize a minimal Settings only if not provided; nothing reads it.
        if settings is None:
            settings = Settings(  # type: ignore[call-arg]
                environment="test",
                use_stub_nodes=True,
                anthropic_api_key="noop",
            )
        return PipelineServices(
            settings=settings,
            meetings=_NoopMeetings(),
            recording=_NoopRecording(),
            frames=_NoopFrames(),
            synth=_NoopSynth(),
        )
