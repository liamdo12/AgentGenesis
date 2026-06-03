"""Unit tests for services/revisions.py: commit_revision DB-first + lock + cleanup."""

import asyncio
import json
from datetime import UTC, datetime

import pytest

from agentgenesis_api.db import repository
from agentgenesis_api.db.models import RunRow
from agentgenesis_api.schemas import StoriesOutput, Story
from agentgenesis_api.services import revisions


def _story(sid: str, title: str = "t") -> Story:
    return Story(
        id=sid,
        title=title,
        persona="user",
        want="x",
        benefit="y",
        ac="Given x when y then z",
        tags=[],
        priority="med",
        meeting="m-1",
    )


def _stories(*ids: str) -> StoriesOutput:
    return StoriesOutput(
        stories=[_story(i) for i in ids],
        source_meeting_id="m-1",
        source_meeting_title="m1",
        generated_at=datetime.now(UTC),
    )


async def _seed_run(session_factory, run_id: str) -> None:
    async with session_factory() as session:
        await repository.upsert_run(
            session,
            run=RunRow(
                id=run_id,
                meeting_id="m-1",
                user_oid="u-alice",
                status="done",
                progress=1.0,
                output_dir=f"./runs/{run_id}",
                created_at=datetime.now(UTC),
            ),
        )
        await session.commit()


async def test_commit_revision_db_first_and_disk_swap(db_session_factory, tmp_path):
    await _seed_run(db_session_factory, "r1")
    run_dir = tmp_path / "r1"

    async with db_session_factory() as session:
        v = await revisions.commit_revision(
            session,
            run_id="r1",
            user_oid="u-alice",
            run_dir=run_dir,
            new=_stories("AG-1", "AG-2"),
            source="extraction",
        )
    assert v == 1
    on_disk = json.loads((run_dir / "stories.json").read_text())
    assert {s["id"] for s in on_disk["stories"]} == {"AG-1", "AG-2"}

    async with db_session_factory() as session:
        latest = await repository.get_latest_revision(
            session, run_id="r1", user_oid="u-alice"
        )
        assert latest is not None
        assert latest.version == 1
        assert latest.source == "extraction"


async def test_commit_revision_cleans_orphaned_approvals(db_session_factory, tmp_path):
    await _seed_run(db_session_factory, "r1")
    run_dir = tmp_path / "r1"
    async with db_session_factory() as session:
        await repository.set_approvals(
            session,
            run_id="r1",
            user_oid="u-alice",
            changes={"AG-1": True, "AG-2": True, "AG-3": True},
        )
        await session.commit()

    # New revision drops AG-3
    async with db_session_factory() as session:
        await revisions.commit_revision(
            session,
            run_id="r1",
            user_oid="u-alice",
            run_dir=run_dir,
            new=_stories("AG-1", "AG-2"),
            source="chat",
        )

    async with db_session_factory() as session:
        ids = await repository.get_approvals(
            session, run_id="r1", user_oid="u-alice"
        )
        assert ids == {"AG-1", "AG-2"}


async def test_concurrent_commits_serialize_via_per_run_lock(
    db_session_factory, tmp_path
):
    await _seed_run(db_session_factory, "r1")
    run_dir = tmp_path / "r1"
    started = asyncio.Event()
    proceed = asyncio.Event()

    async def first_commit():
        lock = revisions.get_run_lock("r1")
        async with lock:
            async with db_session_factory() as session:
                started.set()
                await proceed.wait()
                await revisions.commit_revision(
                    session,
                    run_id="r1",
                    user_oid="u-alice",
                    run_dir=run_dir,
                    new=_stories("AG-1"),
                    source="extraction",
                )

    async def second_commit():
        await started.wait()
        proceed.set()
        lock = revisions.get_run_lock("r1")
        async with lock:
            async with db_session_factory() as session:
                await revisions.commit_revision(
                    session,
                    run_id="r1",
                    user_oid="u-alice",
                    run_dir=run_dir,
                    new=_stories("AG-1", "AG-2"),
                    source="chat",
                )

    await asyncio.gather(first_commit(), second_commit())

    async with db_session_factory() as session:
        revs = await repository.list_revisions(
            session, run_id="r1", user_oid="u-alice"
        )
    versions = sorted(r.version for r in revs)
    assert versions == [1, 2]


async def test_extraction_revision_one_is_idempotent(db_session_factory):
    """Two `add_story_revision_if_absent` calls produce a single row."""
    await _seed_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        for _ in range(3):
            await repository.add_story_revision_if_absent(
                session,
                run_id="r1",
                user_oid="u-alice",
                content_json='{"stories":[],"source_meeting_id":"m","source_meeting_title":"m","generated_at":"2026-06-03T00:00:00Z"}',
                source="extraction",
                version=1,
            )
            await session.commit()

    async with db_session_factory() as session:
        revs = await repository.list_revisions(
            session, run_id="r1", user_oid="u-alice"
        )
        assert len(revs) == 1
        assert revs[0].version == 1


@pytest.fixture(autouse=True)
def _clear_run_locks():
    """Each test gets a fresh lock map so prior `r1` locks don't leak."""
    revisions._run_locks.clear()
    yield
    revisions._run_locks.clear()
