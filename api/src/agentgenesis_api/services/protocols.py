"""Contracts for the pipeline service layer.

`PipelineServices` is the single facade graph nodes consume. The four
protocols below mark the seams where the real Graph/Claude integrations
swap with stub or no-op implementations. Lifespan picks one concrete
factory; nodes never see the choice.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, TypedDict

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.msgraph import MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput
from agentgenesis_api.synthesis.schemas import MultimodalContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker


class ChatChunk(TypedDict, total=False):
    type: Literal["text", "stories"]
    text: str
    stories: dict
    removed_ids: list[str]


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
    def stream_chat(
        self,
        user_message: str,
        chat_history: list[dict],
        current_stories: StoriesOutput,
    ) -> AsyncIterator[ChatChunk]: ...


@dataclass
class PipelineServices:
    settings: Settings
    meetings: MeetingSource
    recording: RecordingFetcher
    frames: FrameExtractor
    synth: Synthesizer
    # Optional so noop/topology tests can construct without a DB. Phase 3
    # graph nodes that need persistence raise if this is None.
    db_session_factory: async_sessionmaker | None = None
