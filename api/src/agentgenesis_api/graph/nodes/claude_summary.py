"""Graph node: delegate Claude summarization to the services facade."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes.merge_context import (
    build_multimodal_context_from_state,
)
from agentgenesis_api.logging import get_logger
from agentgenesis_api.synthesis.schemas import MultimodalContext

log = get_logger("agentgenesis_api.graph.nodes.claude_summary")


def build(deps: NodeDeps):
    async def claude_summary(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("summary") is not None:
            return {"phase_label": "Summarizing with Claude…", "progress": 0.90}

        ctx_raw = state.get("multimodal_context")
        rebuilt = False
        if ctx_raw is None:
            # Idempotent recovery: LangGraph parallel-branch checkpoints can
            # land us here with merge_context's slice missing after a
            # server-restart pause. Rebuild from whatever the upstream
            # nodes did persist; merge_context's logic tolerates missing
            # frames_manifest / empty transcript_segments.
            if "meeting_ref" not in state:
                # No way to recover — surface a clear error with state shape
                # so the operator can identify which upstream branch failed.
                log.error(
                    "claude_summary.missing_multimodal_context_and_meeting_ref",
                    run_id=state.get("run_id"),
                    state_keys=sorted(state.keys()),
                    pending_reason=state.get("pending_reason"),
                )
                raise RuntimeError(
                    "claude_summary: state is missing 'multimodal_context' AND "
                    "'meeting_ref'. Cannot recover. "
                    f"present state keys: {sorted(state.keys())}"
                )
            log.warning(
                "claude_summary.rebuilding_multimodal_context",
                run_id=state.get("run_id"),
                state_keys=sorted(state.keys()),
                has_transcript_segments="transcript_segments" in state,
                has_frames_manifest="frames_manifest" in state,
                pending_reason=state.get("pending_reason"),
            )
            ctx = build_multimodal_context_from_state(state, deps.settings)
            rebuilt = True
        else:
            ctx = MultimodalContext.model_validate(ctx_raw)

        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        summary = await deps.services.synth.summarize(ctx, out_dir)
        result: dict[str, Any] = {
            "summary": summary,
            "phase_label": "Summarizing with Claude…",
            "progress": 0.90,
        }
        if rebuilt:
            # Persist the rebuilt slice so claude_draft_stories reads a
            # consistent state and doesn't repeat the recovery path.
            result["multimodal_context"] = ctx.model_dump()
        return result

    claude_summary.__name__ = "claude_summary"
    return claude_summary
