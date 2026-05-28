"""Graph node: load the MeetingRef for the run's meeting_id."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.auth.models import STUB_USER
from agentgenesis_api.graph.auth_context import current_user
from agentgenesis_api.graph.deps import NodeDeps


def build(deps: NodeDeps):
    async def fetch_meeting_ref(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("meeting_ref") is not None:
            return {"phase_label": "Resolving meeting…", "progress": 0.05}
        meeting_id = state["meeting_id"]
        user = current_user.get() or STUB_USER  # ContextVar set by GraphRunner._execute
        if deps.graph is None:
            raise RuntimeError("graph client not configured (stub mode without user?)")
        refs = await deps.graph.list_meeting_recordings(user, limit=200)
        match = next((r for r in refs if r.id == meeting_id), None)
        if match is None:
            raise RuntimeError(f"Meeting {meeting_id!r} not found")
        return {
            "meeting_ref": match,
            "phase_label": "Resolving meeting…",
            "progress": 0.05,
        }

    fetch_meeting_ref.__name__ = "fetch_meeting_ref"
    return fetch_meeting_ref
