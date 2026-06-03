"""Contracts for the pipeline service layer.

`PipelineServices` is the single facade graph nodes consume. The four
protocols below mark the seams where the real Graph/Claude integrations
swap with stub or no-op implementations. Lifespan picks one concrete
factory; nodes never see the choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.msgraph import MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput
from agentgenesis_api.synthesis.schemas import MultimodalContext


class MeetingSource(Protocol):
    async def list_meetings(self, user: User, limit: int = 200) -> list[MeetingRef]: ...
    async def get_meeting_ref(self, user: User, meeting_id: str) -> MeetingRef: ...
    async def get_transcript(self, user: User, meeting_id: str) -> TranscriptArtifact: ...


class RecordingFetcher(Protocol):
    async def fetch_to(self, user: User, meeting_id: str, dest: Path) -> None: ...


class FrameExtractor(Protocol):
    async def extract(
        self, recording_path: Path, run_dir: Path, settings: Settings
    ) -> dict: ...


class Synthesizer(Protocol):
    async def summarize(
        self, ctx: MultimodalContext, run_dir: Path
    ) -> MeetingSummary: ...
    async def draft_stories(
        self, ctx: MultimodalContext, summary: MeetingSummary, run_dir: Path
    ) -> StoriesOutput: ...


@dataclass
class PipelineServices:
    settings: Settings
    meetings: MeetingSource
    recording: RecordingFetcher
    frames: FrameExtractor
    synth: Synthesizer
