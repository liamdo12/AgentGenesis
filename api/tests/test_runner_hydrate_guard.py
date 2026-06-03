"""Regression: hydrate_from_db must invalidate non-terminal runs.

Prevents the stale-checkpoint footgun where a code revision that changed
state shape causes claude_summary to KeyError on resume. Runs in
DONE / FAILED / PENDING_TRANSCRIPT are preserved as-is; everything else
flips to FAILED so /resume can't re-enter a stale LangGraph checkpoint.
"""

from datetime import UTC, datetime

import pytest

from agentgenesis_api.config import Settings
from agentgenesis_api.db import repository
from agentgenesis_api.db.models import RunRow
from agentgenesis_api.graph.runner import GraphRunner
from agentgenesis_api.schemas import RunStatus


async def _make_row(session_factory, *, run_id: str, status: str) -> None:
    async with session_factory() as session:
        await repository.upsert_run(
            session,
            run=RunRow(
                id=run_id,
                meeting_id="m-1",
                user_oid="u-alice",
                status=status,
                progress=0.5,
                error=None,
                output_dir=f"./runs/{run_id}",
                created_at=datetime.now(UTC),
            ),
        )
        await session.commit()


@pytest.mark.parametrize(
    ("status_in", "expected_invalidated"),
    [
        ("done", False),
        ("failed", False),
        ("pending_transcript", False),
        ("pending", True),
        ("fetching_transcript", True),
        ("fetching_recording", True),
        ("extracting_frames", True),
        ("synthesizing", True),
    ],
)
async def test_hydrate_invalidates_non_terminal(
    db_session_factory, env_setup, status_in, expected_invalidated
):
    await _make_row(db_session_factory, run_id="r1", status=status_in)
    settings = Settings()  # type: ignore[call-arg]
    runner = GraphRunner(settings)
    runner.attach_db(db_session_factory)
    await runner.hydrate_from_db()

    run = runner._runs["r1"]
    if expected_invalidated:
        assert run.status == RunStatus.FAILED
        assert "checkpoint invalidated" in (run.error or "")
        # Persisted back to DB so a second hydrate sees the terminal state.
        async with db_session_factory() as session:
            row = await repository.get_run(
                session, run_id="r1", user_oid="u-alice"
            )
            assert row is not None
            assert row.status == "failed"
    else:
        assert run.status == RunStatus(status_in)
        assert run.error is None
