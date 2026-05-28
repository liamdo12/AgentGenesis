"""HTTP-level IDOR tests.

Existing `test_idor_isolation.py` exercises GraphRunner directly. This file
hits the FastAPI routers via TestClient with two distinct users to make
sure the `Depends(require_user)` + user_oid filter combine correctly.

We override `require_user` via FastAPI dependency_overrides so we can switch
between Alice and Bob without minting JWTs.
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from agentgenesis_api.auth import User, require_user
from agentgenesis_api.config import Settings
from agentgenesis_api.main import create_app
from agentgenesis_api.schemas import Run, RunStatus


def _user(oid: str) -> User:
    return User(oid=oid, tid="t-1", upn=f"{oid}@example.com", name=oid, scp=["access_as_user"], raw_token=SecretStr("tok"))


def _seed_run(runner, run_id: str, owner: str, output_dir: Path) -> Run:
    output_dir.mkdir(parents=True, exist_ok=True)
    run = Run(
        id=run_id,
        meeting_id="m-1",
        user_oid=owner,
        status=RunStatus.DONE,
        progress=1.0,
        error=None,
        created_at=datetime.now(UTC),
        finished_at=None,
        output_dir=str(output_dir),
    )
    runner._runs[run_id] = run
    return run


def test_cross_user_get_returns_404(env_setup, tmp_path) -> None:
    app = create_app(Settings())  # type: ignore[call-arg]
    with TestClient(app) as client:
        runner = app.state.runner
        _seed_run(runner, "alice-run", "alice", tmp_path / "alice-run")
        # Override require_user to act as Bob.
        app.dependency_overrides[require_user] = lambda: _user("bob")
        resp = client.get("/runs/alice-run")
        assert resp.status_code == 404
        app.dependency_overrides.clear()


def test_cross_user_files_returns_404(env_setup, tmp_path) -> None:
    app = create_app(Settings())  # type: ignore[call-arg]
    with TestClient(app) as client:
        runner = app.state.runner
        out = tmp_path / "alice-run"
        _seed_run(runner, "alice-run", "alice", out)
        # Make a real file Alice could read.
        (out / "transcript.json").write_text("{}")
        app.dependency_overrides[require_user] = lambda: _user("bob")
        resp = client.get("/runs/alice-run/files/transcript.json")
        assert resp.status_code == 404
        app.dependency_overrides.clear()


def test_list_runs_filters_to_caller(env_setup, tmp_path) -> None:
    app = create_app(Settings())  # type: ignore[call-arg]
    with TestClient(app) as client:
        runner = app.state.runner
        _seed_run(runner, "alice-1", "alice", tmp_path / "alice-1")
        _seed_run(runner, "bob-1",   "bob",   tmp_path / "bob-1")
        # As Alice.
        app.dependency_overrides[require_user] = lambda: _user("alice")
        alice_resp = client.get("/runs")
        assert alice_resp.status_code == 200
        alice_ids = {r["id"] for r in alice_resp.json()}
        assert alice_ids == {"alice-1"}
        # As Bob.
        app.dependency_overrides[require_user] = lambda: _user("bob")
        bob_resp = client.get("/runs")
        bob_ids = {r["id"] for r in bob_resp.json()}
        assert bob_ids == {"bob-1"}
        app.dependency_overrides.clear()


def test_cross_user_resume_returns_404(env_setup, tmp_path) -> None:
    app = create_app(Settings())  # type: ignore[call-arg]
    with TestClient(app) as client:
        runner = app.state.runner
        _seed_run(runner, "alice-run", "alice", tmp_path / "alice-run")
        app.dependency_overrides[require_user] = lambda: _user("bob")
        resp = client.post("/runs/alice-run/resume")
        assert resp.status_code == 404
        app.dependency_overrides.clear()
