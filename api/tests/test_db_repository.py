"""Round-trip + isolation tests for the db.repository module."""

from datetime import UTC, datetime, timedelta

import pytest

from agentgenesis_api.db import repository
from agentgenesis_api.db.models import RunRow


async def _make_run(session_factory, run_id: str, user_oid: str = "u-alice") -> None:
    async with session_factory() as session:
        await repository.upsert_run(
            session,
            run=RunRow(
                id=run_id,
                meeting_id="m-1",
                user_oid=user_oid,
                status="pending",
                progress=0.0,
                error=None,
                output_dir=f"./runs/{run_id}",
                created_at=datetime.now(UTC),
                finished_at=None,
            ),
        )
        await session.commit()


async def test_run_upsert_roundtrip(db_session_factory):
    await _make_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        row = await repository.get_run(session, run_id="r1", user_oid="u-alice")
        assert row is not None
        assert row.meeting_id == "m-1"


async def test_run_cross_user_isolation(db_session_factory):
    await _make_run(db_session_factory, "r1", user_oid="u-alice")
    async with db_session_factory() as session:
        row = await repository.get_run(session, run_id="r1", user_oid="u-bob")
        assert row is None


async def test_approvals_upsert_and_delete(db_session_factory):
    await _make_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        await repository.set_approvals(
            session,
            run_id="r1",
            user_oid="u-alice",
            changes={"AG-1001": True, "AG-1002": True},
        )
        await session.commit()
        ids = await repository.get_approvals(session, run_id="r1", user_oid="u-alice")
        assert ids == {"AG-1001", "AG-1002"}

        await repository.set_approvals(
            session, run_id="r1", user_oid="u-alice", changes={"AG-1001": False}
        )
        await session.commit()
        ids = await repository.get_approvals(session, run_id="r1", user_oid="u-alice")
        assert ids == {"AG-1002"}


async def test_story_revision_versioning(db_session_factory):
    await _make_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        v1 = await repository.add_story_revision(
            session,
            run_id="r1",
            user_oid="u-alice",
            content_json='{"v":1}',
            source="extraction",
        )
        v2 = await repository.add_story_revision(
            session,
            run_id="r1",
            user_oid="u-alice",
            content_json='{"v":2}',
            source="chat",
        )
        await session.commit()
        assert v1 == 1
        assert v2 == 2
        latest = await repository.get_latest_revision(
            session, run_id="r1", user_oid="u-alice"
        )
        assert latest is not None
        assert latest.version == 2


async def test_story_revision_if_absent_is_idempotent(db_session_factory):
    await _make_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        a = await repository.add_story_revision_if_absent(
            session,
            run_id="r1",
            user_oid="u-alice",
            content_json='{"a":1}',
            source="extraction",
        )
        await session.commit()
        b = await repository.add_story_revision_if_absent(
            session,
            run_id="r1",
            user_oid="u-alice",
            content_json='{"a":2}',
            source="extraction",
        )
        await session.commit()
        assert a == b == 1
        rev = await repository.get_revision(
            session, run_id="r1", user_oid="u-alice", version=1
        )
        assert rev is not None
        # First write wins; second is a no-op.
        assert rev.content_json == '{"a":1}'


async def test_chat_turns_round_trip_and_sweep(db_session_factory):
    await _make_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        await repository.append_chat_turn(
            session, run_id="r1", user_oid="u-alice", role="user", content="hi"
        )
        t = await repository.append_chat_turn(
            session,
            run_id="r1",
            user_oid="u-alice",
            role="assistant",
            content="",
            status="streaming",
        )
        await session.commit()
        # Backdate the streaming row to look like a crash leftover.
        t.created_at = datetime.now(UTC) - timedelta(minutes=10)
        await session.commit()

    async with db_session_factory() as session:
        n = await repository.sweep_stale_streaming_turns(
            session, older_than=datetime.now(UTC) - timedelta(minutes=5)
        )
        await session.commit()
        assert n == 1

    async with db_session_factory() as session:
        turns = await repository.list_chat_turns(
            session, run_id="r1", user_oid="u-alice"
        )
        statuses = [t.status for t in turns]
        assert "error" in statuses


async def test_delete_approvals_not_in(db_session_factory):
    await _make_run(db_session_factory, "r1")
    async with db_session_factory() as session:
        await repository.set_approvals(
            session,
            run_id="r1",
            user_oid="u-alice",
            changes={"AG-1": True, "AG-2": True, "AG-3": True},
        )
        await session.commit()
        n = await repository.delete_approvals_not_in(
            session,
            run_id="r1",
            user_oid="u-alice",
            keep_story_ids=["AG-2"],
        )
        await session.commit()
        assert n == 2
        ids = await repository.get_approvals(session, run_id="r1", user_oid="u-alice")
        assert ids == {"AG-2"}


@pytest.mark.asyncio
async def test_in_memory_isolation_between_fixtures(db_session_factory):
    """Sanity check: this fixture instance gets a clean DB.

    Tests in this file write `r1` repeatedly; the fact that no `add_story_revision`
    in this test collides with prior ones proves the in-memory DB is per-test.
    """
    async with db_session_factory() as session:
        rows = await repository.list_runs_all(session)
        assert rows == []
