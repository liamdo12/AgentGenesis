"""Phase 6 — merge_context, claude_summary, claude_draft_stories.

Claude is stubbed (an object with a `structured_json` method). No network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, HttpUrl

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes import claude_draft_stories, claude_summary, merge_context
from agentgenesis_api.msgraph import MeetingRef
from agentgenesis_api.schemas import MeetingSummary
from agentgenesis_api.services import RealServices
from agentgenesis_api.synthesis.frame_selection import pick_evenly
from agentgenesis_api.synthesis.token_counter import (
    estimate_text_tokens,
    estimate_total_tokens,
    estimate_vision_tokens,
)


class _FakeClaude:
    """Stub for ClaudeClient: returns the next canned response per schema."""

    def __init__(self) -> None:
        self.responses: dict[type, Any] = {}
        self.calls: list[dict] = []

    async def structured_json(self, *, system, user_text, frame_paths=None, schema, max_tokens=4096):
        self.calls.append({"system": system, "user_text": user_text, "schema": schema})
        if schema in self.responses:
            return self.responses[schema]
        return schema()  # default: empty instance


def _settings(tmp_path: Path) -> Settings:
    return Settings(  # type: ignore[call-arg]
        teams_mcp_url=HttpUrl("http://localhost:3000/mcp"),
        anthropic_api_key="test",  # type: ignore[arg-type]
        data_dir=tmp_path,
        chunk_window_sec=10,
        synth_max_frames_in_context=4,
        min_useful_frames=1,
    )


def _deps(tmp_path: Path) -> tuple[NodeDeps, _FakeClaude]:
    fake = _FakeClaude()
    settings = _settings(tmp_path)
    services = RealServices.create(settings, claude=fake)  # type: ignore[arg-type]
    return NodeDeps(settings=settings, services=services), fake


# ──────────────── frame selection ────────────────


def test_frame_selection_picks_k() -> None:
    frames = [
        {"chunk": 0, "frame": i + 1, "timestamp_sec": float(i), "path": f"frames/0000/frame_{i:05d}.jpg"}
        for i in range(20)
    ]
    picked = pick_evenly(frames, k=4)
    assert len(picked) == 4
    # First and last spread.
    assert picked[0].timestamp_sec == 0.0
    assert picked[-1].timestamp_sec >= 12.0


def test_frame_selection_smaller_than_k_returns_all() -> None:
    frames = [{"chunk": 0, "frame": 1, "timestamp_sec": 0.0, "path": "f.jpg"}]
    picked = pick_evenly(frames, k=10)
    assert len(picked) == 1


# ──────────────── token estimation ────────────────


def test_token_estimator_basic() -> None:
    assert estimate_text_tokens("") == 0
    assert estimate_vision_tokens(3) == 3 * 1600
    assert estimate_total_tokens(["abcdef"], 1) > 1600


# ──────────────── merge_context ────────────────


async def test_merge_context_groups_into_windows(tmp_path: Path) -> None:
    deps, _ = _deps(tmp_path)
    state: dict[str, Any] = {
        "meeting_ref": MeetingRef(
            id="m1", title="Sprint", organizer="Alice",
            start_iso=datetime(2026, 8, 22, tzinfo=UTC), duration_sec=20,
        ),
        "frames_manifest": {
            "video": {"duration_sec": 20},
            "frames": [
                {"chunk": 0, "frame": 1, "timestamp_sec": 0.0, "path": "frames/0000/frame_00001.jpg"},
                {"chunk": 0, "frame": 2, "timestamp_sec": 10.0, "path": "frames/0000/frame_00002.jpg"},
            ],
        },
        "transcript_segments": [
            {"index": 0, "start": 0.0, "end": 5.0, "speaker": "Alice", "text": "Hello"},
            {"index": 1, "start": 12.0, "end": 14.0, "speaker": "Bob", "text": "Update"},
        ],
        "warnings": ["language=en"],
    }
    node = merge_context.build(deps)
    result = await node(state)
    ctx = result["multimodal_context"]
    assert ctx["duration_sec"] == 20
    assert ctx["detected_language"] == "en"
    # 20s duration / 10s window → 2 windows.
    assert len(ctx["windows"]) == 2
    assert ctx["frame_evidence_used"] is True


# ──────────────── claude_summary ────────────────


async def test_claude_summary_writes_file(tmp_path: Path) -> None:
    deps, fake = _deps(tmp_path)
    fake.responses[MeetingSummary] = MeetingSummary(
        summary="Brief.", detected_language="en", frame_evidence_used=True,
    )
    run_id = "r1"
    out_dir = deps.settings.data_dir / "runs" / run_id
    out_dir.mkdir(parents=True)
    state = {
        "run_id": run_id,
        "multimodal_context": {
            "meeting": {"id": "m1", "title": "Sprint", "organizer": "A",
                        "start_iso": "2026-08-22T00:00:00Z", "duration_sec": 60},
            "duration_sec": 60.0, "detected_language": "en",
            "windows": [{"start": 0, "end": 60, "transcript_text": "[Alice] Hi.",
                         "speakers": ["Alice"], "frame_paths": []}],
            "selected_frames": [],
            "frame_evidence_used": False,
        },
    }
    node = claude_summary.build(deps)
    result = await node(state)
    assert result["progress"] == 0.90
    assert (out_dir / "summary.json").is_file()


# ──────────────── claude_draft_stories ────────────────


class _StoryDraft(BaseModel):
    title: str
    persona: str
    want: str
    benefit: str
    ac: str
    tags: list[str]
    priority: str


async def test_claude_draft_stories_assigns_ids_and_writes(tmp_path: Path) -> None:
    deps, fake = _deps(tmp_path)

    # Match the internal _LlmStoriesOutput shape.
    from agentgenesis_api.graph.nodes.claude_draft_stories import _LlmStoriesOutput, _LlmStory

    fake.responses[_LlmStoriesOutput] = _LlmStoriesOutput(
        stories=[
            _LlmStory(title="SSO", persona="user", want="log in", benefit="convenience",
                      ac="Given X, when Y, then Z.", tags=["auth"], priority="high"),
            _LlmStory(title="Auto-fetch", persona="pm", want="transcripts load",
                      benefit="start sooner", ac="Given A, when B, then C.",
                      tags=["meetings"], priority="medium"),  # ← "medium" should coerce to "med"
        ]
    )

    run_id = "r2"
    out_dir = deps.settings.data_dir / "runs" / run_id
    out_dir.mkdir(parents=True)
    state = {
        "run_id": run_id,
        "summary": MeetingSummary(
            summary="x", detected_language="en", frame_evidence_used=False,
        ),
        "multimodal_context": {
            "meeting": {"id": "m1", "title": "Sprint Planning", "organizer": "A",
                        "start_iso": "2026-08-22T00:00:00Z", "duration_sec": 60},
            "duration_sec": 60.0, "detected_language": "en",
            "windows": [{"start": 0, "end": 60, "transcript_text": "x",
                         "speakers": [], "frame_paths": []}],
            "selected_frames": [],
            "frame_evidence_used": False,
        },
    }

    node = claude_draft_stories.build(deps)
    result = await node(state)

    out = result["stories_output"]
    assert [s.id for s in out.stories] == ["AG-1001", "AG-1002"]
    # priority "medium" coerced.
    assert out.stories[1].priority == "med"
    # meeting label formatted from MeetingRef.
    assert out.stories[0].meeting == "Sprint Planning · Aug 22"
    # File on disk parses.
    persisted = json.loads((out_dir / "stories.json").read_text())
    assert len(persisted["stories"]) == 2


async def test_claude_summary_raises_without_client(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    services = RealServices.create(settings)  # claude=None
    deps = NodeDeps(settings=settings, services=services)
    node = claude_summary.build(deps)
    with pytest.raises(Exception, match="not configured"):
        await node({"run_id": "r", "multimodal_context": {
            "meeting": {"id": "m", "title": "T", "organizer": "O",
                        "start_iso": "2026-01-01T00:00:00Z", "duration_sec": 0},
            "duration_sec": 0, "detected_language": "en",
            "windows": [], "selected_frames": [], "frame_evidence_used": False,
        }})
