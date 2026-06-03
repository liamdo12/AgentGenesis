"""Versioned story revisions — DB is source of truth, disk is cache.

`commit_revision` inserts a new `StoryRevision` row (the authoritative
copy), atomically swaps `stories.json` on disk, snapshots the prior
version best-effort, then cleans up approvals whose story_id is no longer
present in the new revision.

Order is DB-first so a disk failure leaves the DB consistent and recovery
can rebuild the on-disk cache. Per-run `asyncio.Lock`s serialize chat
commits within one process; multi-worker uvicorn would race the locks
(out of scope for v1 — main.py refuses multi-worker boot).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from agentgenesis_api.db import repository
from agentgenesis_api.logging import get_logger
from agentgenesis_api.schemas import StoriesOutput

log = get_logger("agentgenesis_api.services.revisions")

_run_locks: dict[str, asyncio.Lock] = {}


def get_run_lock(run_id: str) -> asyncio.Lock:
    lock = _run_locks.get(run_id)
    if lock is None:
        lock = asyncio.Lock()
        _run_locks[run_id] = lock
    return lock


async def commit_revision(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    run_dir: Path,
    new: StoriesOutput,
    source: str,
) -> int:
    """Persist a new revision; return its version. Caller holds the per-run lock."""
    content_json = new.model_dump_json()
    # DB first: if this raises, disk stays untouched.
    version = await repository.add_story_revision(
        session,
        run_id=run_id,
        user_oid=user_oid,
        content_json=content_json,
        source=source,
    )

    # Cleanup approvals for stories no longer present.
    keep_ids = [s.id for s in new.stories]
    await repository.delete_approvals_not_in(
        session,
        run_id=run_id,
        user_oid=user_oid,
        keep_story_ids=keep_ids,
    )
    await session.commit()

    # Disk swap is a cache update — failures are logged but never abort the
    # commit. The DB row is the recovery target.
    try:
        _atomic_swap_stories_json(run_dir, content_json, prior_version=version - 1)
    except Exception:  # noqa: BLE001 — disk is a cache; swallow + log
        log.exception(
            "revisions.disk_swap_failed", run_id=run_id, version=version,
        )

    return version


def _atomic_swap_stories_json(run_dir: Path, content_json: str, prior_version: int) -> None:
    """Atomically replace `<run_dir>/stories.json`; best-effort snapshot prior."""
    run_dir.mkdir(parents=True, exist_ok=True)
    target = run_dir / "stories.json"
    tmp = run_dir / "stories.json.tmp"
    if target.is_file() and prior_version > 0:
        snapshot = run_dir / f"stories.v{prior_version}.json"
        with contextlib.suppress(OSError):
            shutil.copy2(target, snapshot)
    tmp.write_text(content_json)
    os.replace(tmp, target)
