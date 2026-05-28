"""Graph node: call Claude for draft user stories matching the frontend Story schema."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.logging import get_logger
from agentgenesis_api.schemas import StoriesOutput, Story
from agentgenesis_api.synthesis.claude_client import ClaudeError
from agentgenesis_api.synthesis.prompts import build_stories_system
from agentgenesis_api.synthesis.schemas import MultimodalContext

log = get_logger("agentgenesis_api.graph.nodes.claude_draft_stories")


class _LlmStory(BaseModel):
    """Story shape we *accept* from the LLM. id and meeting are server-assigned."""

    title: str
    persona: str
    want: str
    benefit: str
    ac: str
    tags: list[str] = Field(default_factory=list)
    priority: str  # validated to literal at Story-construction time


class _LlmStoriesOutput(BaseModel):
    stories: list[_LlmStory] = Field(default_factory=list)


def build(deps: NodeDeps):
    async def claude_draft_stories(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("stories_output") is not None:
            return {"phase_label": "Drafting user stories…", "progress": 1.0}

        if deps.claude is None:
            raise ClaudeError("Claude client not configured")

        ctx = MultimodalContext.model_validate(state["multimodal_context"])
        summary = state["summary"]
        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id

        schema_excerpt = _story_schema_excerpt()
        user_text = _build_user_text(ctx, summary)

        frame_paths = [out_dir / f.path for f in ctx.selected_frames]

        llm_output = await deps.claude.structured_json(
            system=build_stories_system(schema_excerpt),
            user_text=user_text,
            frame_paths=frame_paths,
            schema=_LlmStoriesOutput,
        )

        meeting_label = _format_meeting_label(ctx)
        stories: list[Story] = []
        for idx, ls in enumerate(llm_output.stories):
            stories.append(
                Story(
                    id=f"AG-{1001 + idx}",
                    title=ls.title,
                    persona=ls.persona,
                    want=ls.want,
                    benefit=ls.benefit,
                    ac=ls.ac,
                    tags=ls.tags,
                    priority=_coerce_priority(ls.priority),
                    meeting=meeting_label,
                )
            )

        output = StoriesOutput(
            stories=stories,
            source_meeting_id=ctx.meeting.id,
            source_meeting_title=ctx.meeting.title,
            generated_at=datetime.now(UTC),
        )
        (out_dir / "stories.json").write_text(output.model_dump_json(indent=2))
        log.info("claude_draft_stories.done", run_id=run_id, count=len(stories))
        return {
            "stories_output": output,
            "phase_label": "Drafting user stories…",
            "progress": 1.0,
        }

    claude_draft_stories.__name__ = "claude_draft_stories"
    return claude_draft_stories


def _story_schema_excerpt() -> str:
    # Trim noise from the Pydantic JSON schema for the prompt.
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


def _build_user_text(ctx: MultimodalContext, summary) -> str:
    summary_text = summary.model_dump_json(indent=2) if hasattr(summary, "model_dump_json") else json.dumps(summary, indent=2)
    transcript = "\n".join(w.transcript_text for w in ctx.windows if w.transcript_text)
    return (
        "Use the summary and underlying transcript+frames to extract user stories.\n\n"
        f"--- Summary ---\n{summary_text}\n\n"
        f"--- Transcript ---\n{transcript}\n"
    )


def _format_meeting_label(ctx: MultimodalContext) -> str:
    # e.g. "Sprint Planning · Aug 22"
    return f"{ctx.meeting.title} · {ctx.meeting.start_iso.strftime('%b %d')}"


def _coerce_priority(p: str) -> str:
    p = (p or "").strip().lower()
    if p in ("high", "med", "low"):
        return p
    # Map common variants the LLM might emit.
    return {"medium": "med", "normal": "med", "p1": "high", "p2": "med", "p3": "low"}.get(p, "med")
