"""Graph node: call Claude for a structured MeetingSummary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.logging import get_logger
from agentgenesis_api.schemas import MeetingSummary
from agentgenesis_api.synthesis import map_reduce
from agentgenesis_api.synthesis.claude_client import ClaudeError
from agentgenesis_api.synthesis.prompts import SUMMARY_SYSTEM
from agentgenesis_api.synthesis.schemas import MultimodalContext
from agentgenesis_api.synthesis.token_counter import estimate_total_tokens

log = get_logger("agentgenesis_api.graph.nodes.claude_summary")


def build(deps: NodeDeps):
    async def claude_summary(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("summary") is not None:
            return {"phase_label": "Summarizing with Claude…", "progress": 0.90}

        if deps.claude is None:
            raise ClaudeError("Claude client not configured; set AG_ANTHROPIC_API_KEY")

        ctx = MultimodalContext.model_validate(state["multimodal_context"])
        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        transcript_text = "\n".join(w.transcript_text for w in ctx.windows if w.transcript_text)
        n_frames = len(ctx.selected_frames)
        estimated = estimate_total_tokens([transcript_text, SUMMARY_SYSTEM], n_frames)
        log.info("claude_summary.preflight", run_id=run_id, est_tokens=estimated, frames=n_frames)

        if estimated > deps.settings.synth_max_input_tokens:
            log.info("claude_summary.map_reduce", run_id=run_id, est_tokens=estimated)
            summary = await map_reduce.run(
                deps.claude,
                transcript_text=transcript_text,
                max_chars_per_chunk=deps.settings.synth_max_input_tokens * 2,
            )
        else:
            frame_paths = _resolve_frame_paths(out_dir, ctx.selected_frames)
            user_text = _build_user_text(ctx, transcript_text)
            summary = await deps.claude.structured_json(
                system=SUMMARY_SYSTEM,
                user_text=user_text,
                frame_paths=frame_paths,
                schema=MeetingSummary,
            )

        (out_dir / "summary.json").write_text(json.dumps(summary.model_dump(), indent=2))
        return {
            "summary": summary,
            "phase_label": "Summarizing with Claude…",
            "progress": 0.90,
        }

    claude_summary.__name__ = "claude_summary"
    return claude_summary


def _resolve_frame_paths(out_dir: Path, frames) -> list[Path]:
    return [out_dir / f.path for f in frames]


def _build_user_text(ctx: MultimodalContext, transcript_text: str) -> str:
    return (
        f"Meeting: {ctx.meeting.title}\n"
        f"Organizer: {ctx.meeting.organizer}\n"
        f"Duration: {ctx.duration_sec:.0f}s\n"
        f"Detected language (so far): {ctx.detected_language}\n"
        f"Frame evidence available: {ctx.frame_evidence_used}\n\n"
        f"--- Transcript ---\n{transcript_text}\n"
    )
