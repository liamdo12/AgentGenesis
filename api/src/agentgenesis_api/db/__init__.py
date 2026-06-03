"""SQLAlchemy 2.x async data layer for AgentGenesis.

Re-exports the four declarative tables, the engine factory, and the
repository module so callers can `from agentgenesis_api.db import …`.
"""

from agentgenesis_api.db import repository
from agentgenesis_api.db.engine import build_engine, create_all_if_dev
from agentgenesis_api.db.models import Approval, Base, ChatTurn, RunRow, StoryRevision

__all__ = [
    "Approval",
    "Base",
    "ChatTurn",
    "RunRow",
    "StoryRevision",
    "build_engine",
    "create_all_if_dev",
    "repository",
]
