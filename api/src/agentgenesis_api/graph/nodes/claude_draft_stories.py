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

from agentgenesis_api.db import repository
from agentgenesis_api.graph.auth_context import current_user
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes.merge_context import (
    resolve_or_rebuild_multimodal_context,
)
from agentgenesis_api.logging import get_logger
from agentgenesis_api.synthesis.schemas import MultimodalContext

_log = get_logger("agentgenesis_api.graph.nodes.claude_draft_stories")


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

        # Same recovery path as claude_summary: tolerate stale-checkpoint
        # state where the LangGraph parallel-branch slice was dropped.
        ctx, rebuilt = resolve_or_rebuild_multimodal_context(
            state, deps.settings, node_name="claude_draft_stories"
        )
        if "summary" not in state:
            raise RuntimeError(
                "claude_draft_stories: state missing 'summary' — claude_summary "
                f"did not run. present state keys: {sorted(state.keys())}"
            )
        summary = state["summary"]
        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        output = await deps.services.synth.draft_stories(ctx, summary, out_dir)

        # Persist as revision 1 (idempotent under LangGraph replay) so the
        # chat-edit feature has a baseline to fork from.
        factory = deps.services.db_session_factory
        user = current_user.get()
        if factory is not None and user is not None:
            try:
                async with factory() as session:
                    await repository.add_story_revision_if_absent(
                        session,
                        run_id=run_id,
                        user_oid=user.oid,
                        content_json=output.model_dump_json(),
                        source="extraction",
                        version=1,
                    )
                    await session.commit()
            except Exception:
                _log.exception("revision_1.persist_failed", run_id=run_id)

        result: dict[str, Any] = {
            "stories_output": output,
            "phase_label": "Drafting user stories…",
            "progress": 1.0,
        }
        if rebuilt:
            result["multimodal_context"] = ctx.model_dump()
        return result

    claude_draft_stories.__name__ = "claude_draft_stories"
    return claude_draft_stories
