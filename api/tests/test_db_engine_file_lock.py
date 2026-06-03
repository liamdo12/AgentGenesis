"""Regression: file-lock around create_all_if_dev must be cross-platform.

Phase 1 originally imported `fcntl` at module top — that ImportErrored on
Windows at boot. The lock is now POSIX (fcntl) or Windows (msvcrt) with a
graceful no-op fallback. These tests cover:

1. Lock acquires when uncontended (current process).
2. Lock raises `_LockBusy` when already held by this process.
3. `create_all_if_dev` swallows the busy case and proceeds.
"""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from agentgenesis_api.config import Settings
from agentgenesis_api.db.engine import (
    _LockBusy,
    _try_acquire_file_lock,
    create_all_if_dev,
)
from agentgenesis_api.db.models import Base


def test_lock_acquires_when_uncontended(tmp_path: Path):
    lock_path = tmp_path / ".lk"
    with _try_acquire_file_lock(lock_path):
        # Lock is held; we got here.
        assert lock_path.exists()


def test_lock_busy_when_held_by_same_process(tmp_path: Path):
    lock_path = tmp_path / ".lk"
    with _try_acquire_file_lock(lock_path):
        with pytest.raises(_LockBusy):
            with _try_acquire_file_lock(lock_path):
                pytest.fail("second acquire should have raised _LockBusy")


def test_lock_releases_after_context(tmp_path: Path):
    lock_path = tmp_path / ".lk"
    with _try_acquire_file_lock(lock_path):
        pass
    # After release, a fresh acquire must succeed.
    with _try_acquire_file_lock(lock_path):
        pass


async def test_create_all_skips_when_lock_busy(env_setup, tmp_path: Path):
    """Hold the lock from this process; create_all_if_dev must log + skip
    without raising, so the boot path stays robust under contention.
    """
    settings = Settings(  # type: ignore[call-arg]
        environment="dev",
        data_dir=tmp_path,
    )
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'busy.db'}", future=True
    )
    lock_path = tmp_path / ".create_all.lock"
    try:
        with _try_acquire_file_lock(lock_path):
            await create_all_if_dev(engine, settings)
        # Lock is now released. Verify no tables were created in this run
        # (we held the lock; create_all should have skipped).
        async with engine.begin() as conn:
            def _has_tables(sync_conn):
                inspector = __import__(
                    "sqlalchemy"
                ).inspect(sync_conn)
                return inspector.get_table_names()
            tables_before = await conn.run_sync(_has_tables)
        assert tables_before == []
        # Sanity: with the lock released, create_all_if_dev DOES create.
        await create_all_if_dev(engine, settings)
        async with engine.begin() as conn:
            tables_after = await conn.run_sync(_has_tables)
        expected = {t.name for t in Base.metadata.tables.values()}
        assert set(tables_after) == expected
    finally:
        await engine.dispose()


def test_lock_path_can_be_reacquired_via_new_open(tmp_path: Path):
    """Locks must work even after a clean open/close cycle on the file."""
    lock_path = tmp_path / ".lk"
    for _ in range(3):
        with _try_acquire_file_lock(lock_path):
            pass
