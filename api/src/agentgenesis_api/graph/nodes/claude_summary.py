"""Graph node: delegate Claude summarization to the services facade."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes.merge_context import (
    resolve_or_rebuild_multimodal_context,
)
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.graph.nodes.claude_summary")


def build(deps: NodeDeps):
    async def claude_summary(state: dict[str, Any]) -> dict[str, Any]:
        # Idempotent skip when LangGraph replays. Even on the skip path we
        # backfill multimodal_context if it's missing — downstream nodes
        # (claude_draft_stories) read it unconditionally.
        if state.get("summary") is not None:
            result: dict[str, Any] = {
                "phase_label": "Summarizing with Claude…",
                "progress": 0.90,
            }
            if state.get("multimodal_context") is None and "meeting_ref" in state:
                ctx, _ = resolve_or_rebuild_multimodal_context(
                    state, deps.settings, node_name="claude_summary.replay"
                )
                result["multimodal_context"] = ctx.model_dump()
            return result

        # Fresh execution: resolve (or rebuild from a partial checkpoint).
        ctx, rebuilt = resolve_or_rebuild_multimodal_context(
            state, deps.settings, node_name="claude_summary"
        )

        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        summary = await deps.services.synth.summarize(ctx, out_dir)
        result = {
            "summary": summary,
            "phase_label": "Summarizing with Claude…",
            "progress": 0.90,
        }
        if rebuilt:
            # Persist so claude_draft_stories sees a consistent slice and
            # doesn't repeat the rebuild path.
            result["multimodal_context"] = ctx.model_dump()
        return result

    claude_summary.__name__ = "claude_summary"
    return claude_summary
