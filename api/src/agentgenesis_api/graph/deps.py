"""Dependency container for graph nodes.

LangGraph nodes are plain async functions; they take state and return state.
They have no obvious place to receive external dependencies (MCP client,
settings) unless we either:

  (a) close over them at graph-build time, or
  (b) read them from a context object the runner sets before invoke.

We pick (a): `build_graph` receives a `NodeDeps` and partially-applies the
real node modules. Tests inject a fake `NodeDeps` to drive nodes deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentgenesis_api.config import Settings
from agentgenesis_api.mcp import TeamsMCPClient
from agentgenesis_api.synthesis import ClaudeClient


@dataclass
class NodeDeps:
    settings: Settings
    mcp: TeamsMCPClient
    claude: ClaudeClient | None = None  # None in tests; main wires real one
