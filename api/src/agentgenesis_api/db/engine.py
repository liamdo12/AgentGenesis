"""Async SQLAlchemy engine factory + dev-only DDL bootstrap.

`build_engine` returns a `create_async_engine` configured for either SQLite
(`sqlite+aiosqlite`) or SQL Server (`mssql+aioodbc`). `create_all_if_dev`
runs `Base.metadata.create_all` ONLY when `settings.environment != "prod"`,
serialized by a file-lock so multi-worker boots don't race the DDL. Prod
must provision schema out-of-band — see `api/README.md`.
"""

from __future__ import annotations

import fcntl

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agentgenesis_api.config import Settings
from agentgenesis_api.db.models import Base
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.db.engine")


def build_engine(database_url: str) -> AsyncEngine:
    """Create the async engine. Caller is responsible for `dispose()`."""
    return create_async_engine(database_url, future=True, pool_pre_ping=True)


async def create_all_if_dev(engine: AsyncEngine, settings: Settings) -> None:
    """Create tables in dev/test only. Prod schema must be provisioned out-of-band.

    File-locks the create_all call so multi-worker uvicorn boots don't
    race the DDL. If another worker holds the lock, we skip — tables are
    idempotent and the holder is creating them.
    """
    if settings.environment == "prod":
        return

    # In-memory SQLite uses ":memory:" — no on-disk lock applies; just create.
    if ":memory:" in str(engine.url):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    lock_path = settings.data_dir / ".create_all.lock"
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)
    try:
        with open(lock_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    except BlockingIOError:
        # Another worker is creating the schema; tables will exist by the
        # time we actually need them.
        log.info("db.create_all.skipped_locked")
