"""Async SQLAlchemy engine factory + dev-only DDL bootstrap.

`build_engine` returns a `create_async_engine` configured for either SQLite
(`sqlite+aiosqlite`) or SQL Server (`mssql+aioodbc`). `create_all_if_dev`
runs `Base.metadata.create_all` ONLY when `settings.environment != "prod"`,
serialized by a non-blocking file-lock so multi-worker dev boots don't
race the DDL. Prod must provision schema out-of-band — see `api/README.md`.

POSIX uses `fcntl.flock`; Windows uses `msvcrt.locking`. If neither stdlib
module is importable (exotic platform), the lock is skipped — `create_all`
is idempotent and the boot-time `WEB_CONCURRENCY > 1` refusal in `main.py`
makes the lock belt-and-suspenders, not a hard correctness guarantee.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agentgenesis_api.config import Settings
from agentgenesis_api.db.models import Base
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.db.engine")


def build_engine(database_url: str) -> AsyncEngine:
    """Create the async engine. Caller is responsible for `dispose()`."""
    return create_async_engine(database_url, future=True, pool_pre_ping=True)


class _LockBusy(Exception):
    """Raised when the file is locked by another process."""


@contextlib.contextmanager
def _try_acquire_file_lock(path: Path):
    """Non-blocking exclusive file lock. Yields if acquired; raises
    `_LockBusy` if another process holds it. Cross-platform: fcntl on
    POSIX, msvcrt on Windows.
    """
    path.touch(exist_ok=True)
    f = open(path, "w")
    try:
        if sys.platform == "win32":
            try:
                import msvcrt
            except ImportError:  # pragma: no cover — Windows-only path
                yield
                return
            try:
                # Non-blocking exclusive lock on the first byte.
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as e:
                raise _LockBusy() from e
            try:
                yield
            finally:
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
        else:
            try:
                import fcntl
            except ImportError:  # pragma: no cover — exotic platform
                yield
                return
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise _LockBusy() from e
            try:
                yield
            finally:
                try:
                    fcntl.flock(f, fcntl.LOCK_UN)
                except OSError:
                    pass
    finally:
        f.close()


async def create_all_if_dev(engine: AsyncEngine, settings: Settings) -> None:
    """Create tables in dev/test only. Prod schema must be provisioned out-of-band.

    File-locks the create_all call so multi-worker dev boots don't race
    the DDL. If another worker holds the lock, we skip — tables are
    idempotent and the holder is creating them.
    """
    if settings.environment == "prod":
        return

    # In-memory SQLite uses ":memory:" — no on-disk lock applies; just create.
    if ":memory:" in str(engine.url):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    lock_path = settings.data_dir / ".create_all.lock"

    try:
        with _try_acquire_file_lock(lock_path):
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    except _LockBusy:
        # Another worker is creating the schema; tables will exist by the
        # time we actually need them.
        log.info("db.create_all.skipped_locked")
