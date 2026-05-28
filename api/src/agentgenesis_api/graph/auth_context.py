"""Per-task user context.

Graph nodes need the calling user (for OBO + audit). We deliberately do NOT
park the user inside `GraphState` — tokens shouldn't survive in the LangGraph
checkpoint. Instead, `GraphRunner._execute` sets `current_user` as a
`ContextVar` at the top of the run task; nodes read via `current_user.get()`.

ContextVar dies with the task automatically — no parallel runner-owned dict
to clean up. Per red-team Finding 7.
"""

from contextvars import ContextVar

from agentgenesis_api.auth.models import User

current_user: ContextVar[User | None] = ContextVar("current_user", default=None)
