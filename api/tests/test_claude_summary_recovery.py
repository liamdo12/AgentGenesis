"""Regression: claude_summary AND claude_draft_stories both rebuild
multimodal_context from upstream state when a partial LangGraph
checkpoint lands them without that slice.

Failure shape mirrors the user-reported state on /resume after a paused
pending_transcript run:
    has: meeting_ref, transcript_segments, recording_path, pending_reason
    missing: frames_manifest, multimodal_context (and sometimes summary)

Both downstream nodes share the recovery via
`resolve_or_rebuild_multimodal_context` so the second node can't dead-end
even if the first node's idempotent-skip path didn't backfill the slice.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes.claude_draft_stories import (
    build as build_claude_draft_stories,
)
from agentgenesis_api.graph.nodes.claude_summary import build as build_claude_summary
from agentgenesis_api.graph.nodes.merge_context import (
    build_multimodal_context_from_state,
    resolve_or_rebuild_multimodal_context,
)
from agentgenesis_api.msgraph import MeetingRef
from agentgenesis_api.schemas import MeetingSummary
from agentgenesis_api.services import NoopServices


def _make_deps(tmp_path: Path) -> NodeDeps:
    settings = Settings(  # type: ignore[call-arg]
        environment="test",
        data_dir=tmp_path,
        use_stub_nodes=True,
        anthropic_api_key="t",
    )
    return NodeDeps(settings=settings, services=NoopServices.create(settings))


def _partial_resume_state() -> dict:
    """Exactly the keys reported by the user — pending_reason coexists
    with transcript_segments (proving resume); frames_manifest and
    multimodal_context are dropped."""
    return {
        "run_id": "r-recover",
        "meeting_id": "m-1",
        "meeting_ref": MeetingRef(
            id="m-1",
            title="Sprint Planning",
            organizer="Alice",
            start_iso=datetime(2026, 8, 22, tzinfo=UTC),
            duration_sec=30.0,
        ),
        "transcript_segments": [
            {"start": 0.0, "end": 5.0, "speaker": "Alice", "text": "hello"},
        ],
        "recording_path": "/tmp/never-read",
        "pending_reason": "transcript_not_ready",
        "phase_label": "Summarizing with Claude…",
        "progress": 0.85,
        "warnings": ["language=en"],
        "errors": [],
    }


# ── claude_summary ────────────────────────────────────────────────────


async def test_claude_summary_rebuilds_when_slice_missing(tmp_path: Path):
    deps = _make_deps(tmp_path)
    os.makedirs(tmp_path / "runs" / "r-recover", exist_ok=True)
    node = build_claude_summary(deps)
    state = _partial_resume_state()
    result = await node(state)
    assert "multimodal_context" in result
    assert "summary" in result
    assert result["phase_label"] == "Summarizing with Claude…"


async def test_claude_summary_idempotent_skip_backfills_missing_slice(tmp_path: Path):
    """If summary is already in state but multimodal_context isn't, the
    idempotent-skip path must still emit the slice so claude_draft_stories
    doesn't blow up."""
    deps = _make_deps(tmp_path)
    node = build_claude_summary(deps)
    state = _partial_resume_state()
    state["summary"] = MeetingSummary(
        summary="cached",
        key_decisions=[],
        action_items=[],
        detected_language="en",
        frame_evidence_used=False,
    )
    result = await node(state)
    assert "summary" not in result  # not re-emitted (idempotent)
    assert "multimodal_context" in result  # but slice backfilled


async def test_claude_summary_unrecoverable_when_meeting_ref_also_missing(
    tmp_path: Path,
):
    deps = _make_deps(tmp_path)
    node = build_claude_summary(deps)
    state = _partial_resume_state()
    del state["meeting_ref"]
    with pytest.raises(RuntimeError) as excinfo:
        await node(state)
    msg = str(excinfo.value)
    assert "multimodal_context" in msg
    assert "meeting_ref" in msg


async def test_claude_summary_normal_path_when_slice_present(tmp_path: Path):
    deps = _make_deps(tmp_path)
    node = build_claude_summary(deps)
    state = _partial_resume_state()
    ctx = build_multimodal_context_from_state(state, deps.settings)
    state["multimodal_context"] = ctx.model_dump()
    result = await node(state)
    assert "multimodal_context" not in result  # not rebuilt (already present)
    assert "summary" in result


# ── claude_draft_stories ──────────────────────────────────────────────


async def test_claude_draft_stories_rebuilds_when_slice_missing(tmp_path: Path):
    """The exact follow-on failure user hit after claude_summary's fix:
    KeyError at claude_draft_stories.py:73 when checkpoint shape drops
    multimodal_context. Now should rebuild + complete."""
    deps = _make_deps(tmp_path)
    node = build_claude_draft_stories(deps)
    state = _partial_resume_state()
    # claude_summary already produced the summary in this checkpoint.
    state["summary"] = MeetingSummary(
        summary="cached summary",
        key_decisions=[],
        action_items=[],
        detected_language="en",
        frame_evidence_used=False,
    )
    result = await node(state)
    assert "stories_output" in result
    assert "multimodal_context" in result  # propagated for downstream cache


async def test_claude_draft_stories_idempotent_skip(tmp_path: Path):
    deps = _make_deps(tmp_path)
    node = build_claude_draft_stories(deps)
    state = _partial_resume_state()
    # Pretend stories_output already exists — full replay.
    state["stories_output"] = "anything"
    result = await node(state)
    assert "stories_output" not in result  # not re-emitted


async def test_claude_draft_stories_clear_error_when_summary_missing(
    tmp_path: Path,
):
    deps = _make_deps(tmp_path)
    node = build_claude_draft_stories(deps)
    state = _partial_resume_state()
    # No summary in state and no stories_output either.
    with pytest.raises(RuntimeError) as excinfo:
        await node(state)
    assert "summary" in str(excinfo.value)


# ── shared helper ─────────────────────────────────────────────────────


def test_resolve_helper_returns_existing_without_rebuild(tmp_path: Path):
    deps = _make_deps(tmp_path)
    state = _partial_resume_state()
    ctx = build_multimodal_context_from_state(state, deps.settings)
    state["multimodal_context"] = ctx.model_dump()
    out, rebuilt = resolve_or_rebuild_multimodal_context(
        state, deps.settings, node_name="t"
    )
    assert rebuilt is False
    assert out.meeting.id == "m-1"


def test_resolve_helper_rebuilds_when_missing(tmp_path: Path):
    deps = _make_deps(tmp_path)
    state = _partial_resume_state()
    out, rebuilt = resolve_or_rebuild_multimodal_context(
        state, deps.settings, node_name="t"
    )
    assert rebuilt is True
    assert out.meeting.id == "m-1"
