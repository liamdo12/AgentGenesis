"""Dependency container for graph nodes.

LangGraph nodes are plain async functions; they take state and return state.
They have no obvious place to receive external dependencies (Graph client,
token broker, settings) unless we either:

  (a) close over them at graph-build time, or
  (b) read them from a context object the runner sets before invoke.

We pick (a): `build_graph` receives a `NodeDeps` and partially-applies the
node modules. Nodes only see `services` (the pipeline facade) and `settings`;
they never touch GraphClient/TokenBroker/ClaudeClient directly — those live
inside the services implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agentgenesis_api.config import Settings

if TYPE_CHECKING:
    from agentgenesis_api.services import PipelineServices


@dataclass
class NodeDeps:
    settings: Settings
    services: PipelineServices
