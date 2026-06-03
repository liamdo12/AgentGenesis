"""Graph node: delegate Claude summarization to the services facade."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.logging import get_logger
from agentgenesis_api.synthesis.schemas import MultimodalContext

log = get_logger("agentgenesis_api.graph.nodes.claude_summary")


def build(deps: NodeDeps):
    async def claude_summary(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("summary") is not None:
            return {"phase_label": "Summarizing with Claude…", "progress": 0.90}

        ctx_raw = state.get("multimodal_context")
        if ctx_raw is None:
            # Surface the upstream-state shape so the operator can see which
            # parent node failed to produce its slice. Raw KeyError swallowed
            # the diagnostic that points at the actual upstream break.
            log.error(
                "claude_summary.missing_multimodal_context",
                run_id=state.get("run_id"),
                state_keys=sorted(state.keys()),
                has_meeting_ref="meeting_ref" in state,
                has_transcript_segments="transcript_segments" in state,
                has_frames_manifest="frames_manifest" in state,
                pending_reason=state.get("pending_reason"),
            )
            raise RuntimeError(
                "claude_summary: state is missing 'multimodal_context'. "
                "merge_context did not run or did not populate the field. "
                f"present state keys: {sorted(state.keys())}"
            )

        ctx = MultimodalContext.model_validate(ctx_raw)
        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        summary = await deps.services.synth.summarize(ctx, out_dir)
        return {
            "summary": summary,
            "phase_label": "Summarizing with Claude…",
            "progress": 0.90,
        }

    claude_summary.__name__ = "claude_summary"
    return claude_summary
