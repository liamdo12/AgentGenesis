"""Fixture-backed node implementations selected when NodeDeps.stub_mode=True.

Topology when stub_mode is on:
- Real ffmpeg-backed extract_frames and merge_context (see builder.py).
- These functions handle: fixture loading (fetch_*) and canned synthesis (claude_*).

Each function returns a node callable with the same signature, return shape,
AND file-write side-effects as its real counterpart so downstream nodes — and
any /runs/{id}/files/{name} consumer — can't tell the difference.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes._shared import vtt_parser
from agentgenesis_api.logging import get_logger
from agentgenesis_api.msgraph import MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput, Story

log = get_logger("agentgenesis_api.graph.nodes._stubs_local")


def fetch_meeting_ref(deps: NodeDeps):
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("meeting_ref") is not None:
            return {"phase_label": "Resolving meeting…", "progress": 0.05}
        meeting_id = state["meeting_id"]
        return {
            "meeting_ref": MeetingRef(
                id=meeting_id,
                title="Stub: Requirements review session",
                organizer="stub-organizer@example.com",
                start_iso=datetime.now(UTC) - timedelta(hours=1),
                duration_sec=30.0,
            ),
            "phase_label": "Resolving meeting…",
            "progress": 0.05,
        }
    node.__name__ = "fetch_meeting_ref"
    return node


def fetch_transcript(deps: NodeDeps):
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("transcript_segments"):
            return {"phase_label": "Fetching transcript…", "progress": 0.20}
        vtt_path = deps.stub_vtt_path
        if vtt_path is None or not vtt_path.is_file():
            log.warning("stub.vtt.missing", path=str(vtt_path))
            return {
                "transcript": TranscriptArtifact(
                    meeting_id=state["meeting_id"], vtt_text="", detected_language="en"
                ),
                "transcript_segments": [],
                "warnings": [f"stub vtt missing: {vtt_path}", "language=en"],
                "phase_label": "Fetching transcript…",
                "progress": 0.20,
            }
        vtt_text = vtt_path.read_text(encoding="utf-8")
        result = vtt_parser.parse(vtt_text)
        return {
            "transcript": TranscriptArtifact(
                meeting_id=state["meeting_id"], vtt_text=vtt_text, detected_language="en"
            ),
            "transcript_segments": [s.model_dump() for s in result.segments],
            "warnings": (result.warnings or []) + ["language=en"],
            "phase_label": "Fetching transcript…",
            "progress": 0.20,
        }
    node.__name__ = "fetch_transcript"
    return node


def fetch_recording(deps: NodeDeps):
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        existing = state.get("recording_path")
        if existing and Path(existing).is_file():
            return {"phase_label": "Downloading recording…", "progress": 0.35}
        run_id = state["run_id"]
        dest_dir = deps.settings.data_dir / "runs" / run_id / "source"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "recording.mp4"
        src = deps.stub_video_path
        if src is None or not src.is_file():
            # Graceful degrade: missing fixture is non-fatal — extract_frames
            # picks up the canned-manifest fallback when the file is absent.
            log.warning("stub.recording.missing", path=str(src))
            return {
                "recording_path": str(dest),
                "warnings": [f"stub recording missing: {src}"],
                "phase_label": "Downloading recording…",
                "progress": 0.35,
            }
        shutil.copy(src, dest)
        return {
            "recording_path": str(dest),
            "phase_label": "Downloading recording…",
            "progress": 0.35,
        }
    node.__name__ = "fetch_recording"
    return node


def claude_summary(deps: NodeDeps):
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("summary") is not None:
            return {"phase_label": "Summarizing with Claude…", "progress": 0.90}
        useful = (state.get("frames_manifest") or {}).get("useful_frame_count", 0)
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
        # Parity with real claude_summary.py — write summary.json so the
        # /runs/{id}/files/summary.json endpoint serves the same shape.
        out_dir = deps.settings.data_dir / "runs" / state["run_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "summary.json").write_text(json.dumps(summary.model_dump(), indent=2))
        return {
            "summary": summary,
            "phase_label": "Summarizing with Claude…",
            "progress": 0.90,
        }
    node.__name__ = "claude_summary"
    return node


def claude_draft_stories(deps: NodeDeps):
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("stories_output") is not None:
            return {"phase_label": "Drafting user stories…", "progress": 1.0}
        meeting_ref = state.get("meeting_ref")
        meeting_id = state["meeting_id"]
        meeting_title = meeting_ref.title if meeting_ref else "Stub meeting"
        # Story IDs follow the AG-1001/AG-1002 contract from real
        # claude_draft_stories (frontend + test_e2e_pipeline.py assert this).
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
        # Parity with real claude_draft_stories.py — write stories.json.
        out_dir = deps.settings.data_dir / "runs" / state["run_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "stories.json").write_text(output.model_dump_json(indent=2))
        return {
            "stories_output": output,
            "phase_label": "Drafting user stories…",
            "progress": 1.0,
        }
    node.__name__ = "claude_draft_stories"
    return node
