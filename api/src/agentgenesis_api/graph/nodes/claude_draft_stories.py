"""Graph node: delegate user-story drafting to the services facade.

Keeps the LLM input/output contract types (`_LlmStory`, `_LlmStoriesOutput`)
and helpers (`_coerce_priority`, `_format_meeting_label`,
`_story_schema_excerpt`) co-located here because `services.real` and
`test_e2e_pipeline` both consume them.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.synthesis.schemas import MultimodalContext


class _LlmStory(BaseModel):
    """Story shape we accept from the LLM. id and meeting are server-assigned."""

    title: str
    persona: str
    want: str
    benefit: str
    ac: str
    tags: list[str] = Field(default_factory=list)
    priority: str  # validated to literal at Story-construction time


class _LlmStoriesOutput(BaseModel):
    stories: list[_LlmStory] = Field(default_factory=list)


def _story_schema_excerpt() -> str:
    return json.dumps(
        {
            "title": "string",
            "persona": "string (e.g. 'corporate user')",
            "want": "string (e.g. 'log in using SSO')",
            "benefit": "string (e.g. \"I don't manage separate credentials\")",
            "ac": "string in Given/When/Then format, single sentence",
            "tags": ["string", "..."],
            "priority": "'high' | 'med' | 'low'",
        },
        indent=2,
    )


def _format_meeting_label(ctx: MultimodalContext) -> str:
    # e.g. "Sprint Planning · Aug 22"
    return f"{ctx.meeting.title} · {ctx.meeting.start_iso.strftime('%b %d')}"


def _coerce_priority(p: str) -> str:
    p = (p or "").strip().lower()
    if p in ("high", "med", "low"):
        return p
    return {"medium": "med", "normal": "med", "p1": "high", "p2": "med", "p3": "low"}.get(p, "med")


def build(deps: NodeDeps):
    async def claude_draft_stories(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("stories_output") is not None:
            return {"phase_label": "Drafting user stories…", "progress": 1.0}

        ctx = MultimodalContext.model_validate(state["multimodal_context"])
        summary = state["summary"]
        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        output = await deps.services.synth.draft_stories(ctx, summary, out_dir)
        return {
            "stories_output": output,
            "phase_label": "Drafting user stories…",
            "progress": 1.0,
        }

    claude_draft_stories.__name__ = "claude_draft_stories"
    return claude_draft_stories
