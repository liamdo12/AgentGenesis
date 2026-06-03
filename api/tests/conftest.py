"""Shared pytest fixtures."""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Set stub-auth defaults BEFORE any test imports `agentgenesis_api.config`.
# Without this, tests that construct `Settings(...)` directly (e.g.
# test_phase4_nodes) trip the new "Entra config required" validator added in
# Phase 1 of the SSO plan.
os.environ.setdefault("AG_USE_STUB_NODES", "1")
os.environ.setdefault("AG_ENVIRONMENT", "test")
# Force in-memory SQLite so tests don't pollute ./data/agentgenesis.db.
# Each test acquires its own session factory via the `db_session_factory`
# fixture below — STUB_USER's shared oid won't cross-pollute because tables
# live in per-fixture connections.
os.environ.setdefault("AG_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
def env_setup(tmp_path: Path) -> Iterator[None]:
    """Provide the minimum required env vars so Settings() validates."""
    prev = {k: os.environ.get(k) for k in (
        "AG_TEAMS_MCP_URL",
        "AG_ANTHROPIC_API_KEY",
        "AG_DATA_DIR",
        "AG_USE_STUB_NODES",
        "AG_DATABASE_URL",
    )}
    os.environ["AG_TEAMS_MCP_URL"] = "http://localhost:3000/mcp"
    os.environ["AG_ANTHROPIC_API_KEY"] = "test-key"
    os.environ["AG_DATA_DIR"] = str(tmp_path / "data")
    # All API-driven tests default to stub nodes so they never hit MCP/Claude.
    os.environ["AG_USE_STUB_NODES"] = "1"
    os.environ["AG_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    try:
        yield
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest_asyncio.fixture
async def db_session_factory() -> AsyncIterator[async_sessionmaker]:
    """Per-test in-memory SQLAlchemy session factory.

    A fresh in-memory database per test means STUB_USER's shared oid can't
    pollute across tests; each invocation gets clean tables.
    """
    from agentgenesis_api.db.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()
