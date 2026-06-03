"""Regression: claude_summary rebuilds multimodal_context from upstream
state when a partial LangGraph checkpoint lands it without that slice.

Triggering shape (mirrors user-reported failure on /resume after a paused
pending_transcript run):
    state has: meeting_ref, transcript_segments, recording_path,
               pending_reason
    state missing: frames_manifest, multimodal_context

Expected behaviour:
    claude_summary logs a warning, rebuilds multimodal_context inline via
    `build_multimodal_context_from_state`, calls the synthesizer, and
    returns the slice so downstream nodes don't re-trigger the recovery.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes.claude_summary import build as build_claude_summary
from agentgenesis_api.msgraph import MeetingRef
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
    """Exactly the keys reported by the user (pending_reason + segments
    co-exist; frames_manifest + multimodal_context are missing)."""
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
        "pending_reason": "transcript_not_ready",  # stale carryover
        "phase_label": "Summarizing with Claude…",
        "progress": 0.85,
        "warnings": ["language=en"],
        "errors": [],
    }


async def test_rebuilds_multimodal_context_when_missing(tmp_path: Path):
    deps = _make_deps(tmp_path)
    os.makedirs(tmp_path / "runs" / "r-recover", exist_ok=True)
    node = build_claude_summary(deps)
    state = _partial_resume_state()

    result = await node(state)

    # Recovery slice persisted so downstream nodes don't re-trigger.
    assert "multimodal_context" in result
    assert "summary" in result
    # Noop synth returns an empty MeetingSummary.
    assert result["summary"].summary == ""
    # Phase signalling still mirrors the normal path.
    assert result["phase_label"] == "Summarizing with Claude…"
    assert result["progress"] == 0.90


async def test_idempotent_skip_when_summary_already_set(tmp_path: Path):
    deps = _make_deps(tmp_path)
    node = build_claude_summary(deps)
    # When summary is already in state (LangGraph replay), short-circuit
    # without touching multimodal_context (even if it's missing).
    from agentgenesis_api.schemas import MeetingSummary

    state = _partial_resume_state()
    state["summary"] = MeetingSummary(
        summary="cached",
        key_decisions=[],
        action_items=[],
        detected_language="en",
        frame_evidence_used=False,
    )
    result = await node(state)
    assert "multimodal_context" not in result
    assert "summary" not in result  # not re-emitted on replay


async def test_raises_when_both_meeting_ref_and_multimodal_context_missing(
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
    # State shape leaked into the message for operator triage.
    assert "transcript_segments" in msg


async def test_existing_multimodal_context_is_used_as_is(tmp_path: Path):
    """Normal path: when multimodal_context IS present, no rebuild."""
    deps = _make_deps(tmp_path)
    node = build_claude_summary(deps)

    from agentgenesis_api.graph.nodes.merge_context import (
        build_multimodal_context_from_state,
    )

    state = _partial_resume_state()
    ctx = build_multimodal_context_from_state(state, deps.settings)
    state["multimodal_context"] = ctx.model_dump()

    result = await node(state)
    # No fresh multimodal_context slice — node read the existing one.
    assert "multimodal_context" not in result
    assert "summary" in result
