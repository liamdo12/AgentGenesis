"""Graph node: resolve the MeetingRef for the run's meeting_id via services facade."""

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
        user = current_user.get() or STUB_USER
        ref = await deps.services.meetings.get_meeting_ref(user, meeting_id)
        return {
            "meeting_ref": ref,
            "phase_label": "Resolving meeting…",
            "progress": 0.05,
        }

    fetch_meeting_ref.__name__ = "fetch_meeting_ref"
    return fetch_meeting_ref
