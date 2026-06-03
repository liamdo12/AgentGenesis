"""Graph node: delegate Claude summarization to the services facade."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.synthesis.schemas import MultimodalContext


def build(deps: NodeDeps):
    async def claude_summary(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("summary") is not None:
            return {"phase_label": "Summarizing with Claude…", "progress": 0.90}

        ctx = MultimodalContext.model_validate(state["multimodal_context"])
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
