"""Shared pytest fixtures."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def env_setup(tmp_path: Path) -> Iterator[None]:
    """Provide the minimum required env vars so Settings() validates."""
    prev = {k: os.environ.get(k) for k in (
        "AG_TEAMS_MCP_URL",
        "AG_ANTHROPIC_API_KEY",
        "AG_DATA_DIR",
        "AG_USE_STUB_NODES",
    )}
    os.environ["AG_TEAMS_MCP_URL"] = "http://localhost:3000/mcp"
    os.environ["AG_ANTHROPIC_API_KEY"] = "test-key"
    os.environ["AG_DATA_DIR"] = str(tmp_path / "data")
    # All API-driven tests default to stub nodes so they never hit MCP/Claude.
    os.environ["AG_USE_STUB_NODES"] = "1"
    try:
        yield
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
