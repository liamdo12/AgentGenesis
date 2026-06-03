"""Real pipeline services — wrap GraphClient + ClaudeClient + ffmpeg.

Bodies lifted verbatim from the corresponding graph nodes so behavior is
unchanged. The graph nodes flip to `deps.services.X` in Phase 3.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from agentgenesis_api.auth.models import User
from agentgenesis_api.auth.token_broker import TokenBroker
from agentgenesis_api.config import Settings
from agentgenesis_api.graph.nodes._shared import ffprobe, frames_manifest
from agentgenesis_api.graph.nodes._shared.chunker import plan_chunks
from agentgenesis_api.graph.nodes._shared.extractor import ChunkResult, extract_chunk
from agentgenesis_api.graph.nodes.claude_draft_stories import (
    _coerce_priority,
    _format_meeting_label,
    _LlmStoriesOutput,
    _story_schema_excerpt,
)
from agentgenesis_api.logging import get_logger
from agentgenesis_api.msgraph import GraphClient, MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput, Story
from agentgenesis_api.services.protocols import PipelineServices
from agentgenesis_api.synthesis import ClaudeClient, map_reduce
from agentgenesis_api.synthesis.claude_client import ClaudeError
from agentgenesis_api.synthesis.prompts import SUMMARY_SYSTEM, build_stories_system
from agentgenesis_api.synthesis.schemas import MultimodalContext
from agentgenesis_api.synthesis.token_counter import estimate_total_tokens

log = get_logger("agentgenesis_api.services.real")


@dataclass
class _RealMeetings:
    graph: GraphClient | None

    async def list_meetings(self, user: User, limit: int = 200) -> list[MeetingRef]:
        if self.graph is None:
            raise RuntimeError("graph client not configured")
        return await self.graph.list_meeting_recordings(user, limit=limit)

    async def get_meeting_ref(self, user: User, meeting_id: str) -> MeetingRef:
        refs = await self.list_meetings(user, limit=200)
        match = next((r for r in refs if r.id == meeting_id), None)
        if match is None:
            raise RuntimeError(f"Meeting {meeting_id!r} not found")
        return match

    async def get_transcript(self, user: User, meeting_id: str) -> TranscriptArtifact:
        if self.graph is None:
            raise RuntimeError("graph client not configured")
        return await self.graph.get_transcript(user, meeting_id)


@dataclass
class _RealRecording:
    graph: GraphClient | None
    broker: TokenBroker | None
    settings: Settings

    async def fetch_to(self, user: User, meeting_id: str, dest: Path) -> None:
        if self.graph is None:
            raise RuntimeError("graph client not configured")
        if self.broker is None:
            raise RuntimeError("TokenBroker required to download recording content")
        artifact = await self.graph.get_recording(user, meeting_id)
        if artifact.download_url is None:
            raise RuntimeError("Graph returned no recordingContentUrl")
        bearer = await self.broker.acquire_graph_token(user, self.settings.graph_delegated_scopes)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        timeout = httpx.Timeout(self.settings.recording_download_timeout_sec)
        headers = {"Authorization": f"Bearer {bearer}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", str(artifact.download_url), headers=headers) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", "0"))
                _ensure_free_space(dest.parent, total)
                with tmp.open("wb") as f:
                    async for chunk in r.aiter_bytes(self.settings.recording_chunk_bytes):
                        f.write(chunk)
        tmp.rename(dest)


def _ensure_free_space(path: Path, needed_bytes: int) -> None:
    if needed_bytes <= 0:
        return
    usage = shutil.disk_usage(path)
    if usage.free < 2 * needed_bytes:
        raise RuntimeError(
            f"Insufficient disk: {usage.free} free, need {2 * needed_bytes} (2x recording size)"
        )


@dataclass
class _RealFrames:
    async def extract(
        self, recording_path: Path, run_dir: Path, settings: Settings
    ) -> dict:
        src = recording_path
        if not src.is_file():
            raise RuntimeError(f"recording not found at {src}")
        duration = await ffprobe.get_duration(src)
        chunks = plan_chunks(duration, settings.chunk_window_sec)
        if not chunks:
            raise RuntimeError(f"video has non-positive duration: {duration}")

        frames_root = run_dir / "frames"
        frames_root.mkdir(parents=True, exist_ok=True)

        sem = asyncio.Semaphore(min(os.cpu_count() or 1, settings.max_parallel_ffmpeg))

        async def run_one(c) -> ChunkResult:
            async with sem:
                return await extract_chunk(c, src, frames_root, settings.frame_interval_sec)

        raw = await asyncio.gather(*(run_one(c) for c in chunks), return_exceptions=True)
        results: list[ChunkResult] = []
        for c, r in zip(chunks, raw, strict=True):
            if isinstance(r, ChunkResult):
                results.append(r)
            else:
                results.append(
                    ChunkResult(
                        idx=c.idx,
                        start=c.start,
                        end=c.end,
                        frame_count=0,
                        status="error",
                        error=f"{type(r).__name__}: {r}",
                    )
                )
        manifest = frames_manifest.build(
            out_dir=run_dir,
            chunks_results=results,
            frame_interval_sec=settings.frame_interval_sec,
            chunk_window_sec=settings.chunk_window_sec,
            duration_sec=duration,
        )
        useful = manifest["useful_frame_count"]
        if useful == 0 and all(r.status == "error" for r in results):
            raise RuntimeError(
                "All ffmpeg chunks failed; no frames extracted. "
                f"First error: {results[0].error if results else 'no chunks'}"
            )
        return manifest


@dataclass
class _RealSynth:
    claude: ClaudeClient | None
    settings: Settings

    async def summarize(
        self, ctx: MultimodalContext, run_dir: Path
    ) -> MeetingSummary:
        if self.claude is None:
            raise ClaudeError("Claude client not configured; set AG_ANTHROPIC_API_KEY")
        transcript_text = "\n".join(w.transcript_text for w in ctx.windows if w.transcript_text)
        n_frames = len(ctx.selected_frames)
        estimated = estimate_total_tokens([transcript_text, SUMMARY_SYSTEM], n_frames)
        run_id = run_dir.name
        log.info("claude_summary.preflight", run_id=run_id, est_tokens=estimated, frames=n_frames)
        if estimated > self.settings.synth_max_input_tokens:
            log.info("claude_summary.map_reduce", run_id=run_id, est_tokens=estimated)
            summary = await map_reduce.run(
                self.claude,
                transcript_text=transcript_text,
                max_chars_per_chunk=self.settings.synth_max_input_tokens * 2,
            )
        else:
            frame_paths = [run_dir / f.path for f in ctx.selected_frames]
            user_text = _build_summary_user_text(ctx, transcript_text)
            summary = await self.claude.structured_json(
                system=SUMMARY_SYSTEM,
                user_text=user_text,
                frame_paths=frame_paths,
                schema=MeetingSummary,
            )
        (run_dir / "summary.json").write_text(json.dumps(summary.model_dump(), indent=2))
        return summary

    async def draft_stories(
        self, ctx: MultimodalContext, summary: MeetingSummary, run_dir: Path
    ) -> StoriesOutput:
        if self.claude is None:
            raise ClaudeError("Claude client not configured")
        schema_excerpt = _story_schema_excerpt()
        user_text = _build_stories_user_text(ctx, summary)
        frame_paths = [run_dir / f.path for f in ctx.selected_frames]
        llm_output = await self.claude.structured_json(
            system=build_stories_system(schema_excerpt),
            user_text=user_text,
            frame_paths=frame_paths,
            schema=_LlmStoriesOutput,
        )
        meeting_label = _format_meeting_label(ctx)
        stories: list[Story] = []
        for idx, ls in enumerate(llm_output.stories):
            stories.append(
                Story(
                    id=f"AG-{1001 + idx}",
                    title=ls.title,
                    persona=ls.persona,
                    want=ls.want,
                    benefit=ls.benefit,
                    ac=ls.ac,
                    tags=ls.tags,
                    priority=_coerce_priority(ls.priority),
                    meeting=meeting_label,
                )
            )
        output = StoriesOutput(
            stories=stories,
            source_meeting_id=ctx.meeting.id,
            source_meeting_title=ctx.meeting.title,
            generated_at=datetime.now(UTC),
        )
        (run_dir / "stories.json").write_text(output.model_dump_json(indent=2))
        log.info("claude_draft_stories.done", run_id=run_dir.name, count=len(stories))
        return output


def _build_summary_user_text(ctx: MultimodalContext, transcript_text: str) -> str:
    return (
        f"Meeting: {ctx.meeting.title}\n"
        f"Organizer: {ctx.meeting.organizer}\n"
        f"Duration: {ctx.duration_sec:.0f}s\n"
        f"Detected language (so far): {ctx.detected_language}\n"
        f"Frame evidence available: {ctx.frame_evidence_used}\n\n"
        f"--- Transcript ---\n{transcript_text}\n"
    )


def _build_stories_user_text(ctx: MultimodalContext, summary: MeetingSummary) -> str:
    summary_text = summary.model_dump_json(indent=2)
    transcript = "\n".join(w.transcript_text for w in ctx.windows if w.transcript_text)
    return (
        "Use the summary and underlying transcript+frames to extract user stories.\n\n"
        f"--- Summary ---\n{summary_text}\n\n"
        f"--- Transcript ---\n{transcript}\n"
    )


class RealServices:
    @classmethod
    def create(
        cls,
        settings: Settings,
        *,
        graph: GraphClient | None = None,
        broker: TokenBroker | None = None,
        claude: ClaudeClient | None = None,
    ) -> PipelineServices:
        return PipelineServices(
            settings=settings,
            meetings=_RealMeetings(graph),
            recording=_RealRecording(graph, broker, settings),
            frames=_RealFrames(),
            synth=_RealSynth(claude, settings),
        )
