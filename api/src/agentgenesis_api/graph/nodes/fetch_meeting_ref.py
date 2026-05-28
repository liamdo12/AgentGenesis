"""Graph node: load the MeetingRef for the run's meeting_id."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps


def build(deps: NodeDeps):
    async def fetch_meeting_ref(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("meeting_ref") is not None:
            return {"phase_label": "Resolving meeting…", "progress": 0.05}
        meeting_id = state["meeting_id"]
        # We currently list and filter; servers may add a `get_by_id` later.
        refs = await deps.mcp.list_meeting_recordings(limit=200)
        match = next((r for r in refs if r.id == meeting_id), None)
        if match is None:
            raise RuntimeError(f"Meeting {meeting_id!r} not found via MCP")
        return {
            "meeting_ref": match,
            "phase_label": "Resolving meeting…",
            "progress": 0.05,
        }

    fetch_meeting_ref.__name__ = "fetch_meeting_ref"
    return fetch_meeting_ref
