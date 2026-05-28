"""IDOR test — Alice's runs must NOT be readable by Bob.

Direct GraphRunner tests (no HTTP layer) because we want to exercise the
user-scoping logic without also fighting the stub-user dependency.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.graph.runner import GraphRunner
from agentgenesis_api.schemas import Run, RunStatus


def _settings(tmp_path: Path) -> Settings:
    return Settings(  # type: ignore[call-arg]
        environment="test",
        use_stub_nodes=True,
        anthropic_api_key="x",
        data_dir=tmp_path,
    )


def _user(oid: str) -> User:
    return User(oid=oid, tid="t-1", raw_token=SecretStr("token"))


def _seed_run(runner: GraphRunner, run_id: str, owner_oid: str, output_dir: Path) -> Run:
    output_dir.mkdir(parents=True, exist_ok=True)
    run = Run(
        id=run_id,
        meeting_id="m-1",
        user_oid=owner_oid,
        status=RunStatus.DONE,
        progress=1.0,
        error=None,
        created_at=datetime.now(UTC),
        finished_at=None,
        output_dir=str(output_dir),
    )
    runner._runs[run_id] = run
    return run


async def test_get_other_users_run_returns_none(tmp_path: Path) -> None:
    runner = GraphRunner(_settings(tmp_path))
    _seed_run(runner, "alice-run", owner_oid="alice", output_dir=tmp_path / "alice-run")
    # Alice gets her run.
    assert (await runner.get("alice-run", "alice")) is not None
    # Bob does NOT.
    assert (await runner.get("alice-run", "bob")) is None


async def test_list_only_users_own_runs(tmp_path: Path) -> None:
    runner = GraphRunner(_settings(tmp_path))
    _seed_run(runner, "alice-1", "alice", tmp_path / "alice-1")
    _seed_run(runner, "alice-2", "alice", tmp_path / "alice-2")
    _seed_run(runner, "bob-1",   "bob",   tmp_path / "bob-1")
    alice_runs = await runner.list("alice")
    assert {r.id for r in alice_runs} == {"alice-1", "alice-2"}
    bob_runs = await runner.list("bob")
    assert {r.id for r in bob_runs} == {"bob-1"}


async def test_safe_resolve_blocks_cross_user(tmp_path: Path) -> None:
    runner = GraphRunner(_settings(tmp_path))
    _seed_run(runner, "alice-run", "alice", tmp_path / "alice-run")
    assert runner.safe_resolve("alice-run", "transcript.json", "alice") is not None
    assert runner.safe_resolve("alice-run", "transcript.json", "bob") is None


async def test_resume_other_users_run_raises(tmp_path: Path) -> None:
    runner = GraphRunner(_settings(tmp_path))
    _seed_run(runner, "alice-run", "alice", tmp_path / "alice-run")
    with pytest.raises(KeyError):
        await runner.resume("alice-run", _user("bob"))
