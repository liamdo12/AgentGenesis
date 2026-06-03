"""HTTP tests for the /runs/{id}/stories/approvals endpoints."""

import time

from fastapi.testclient import TestClient

from agentgenesis_api.config import Settings
from agentgenesis_api.main import create_app


def _poll_until_done(client: TestClient, run_id: str, timeout_sec: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(0.05)
    raise AssertionError(f"Run {run_id} did not finish within {timeout_sec}s")


def _make_run(client: TestClient) -> str:
    resp = client.post("/runs", json={"meeting_id": "m-stub"})
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]
    _poll_until_done(client, run_id)
    return run_id


def test_get_empty_then_post_then_get(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _make_run(client)

        # Initial GET: empty
        r = client.get(f"/runs/{run_id}/stories/approvals")
        assert r.status_code == 200
        assert r.json() == {"approved_ids": []}

        # POST approve two stories
        r = client.post(
            f"/runs/{run_id}/stories/approvals",
            json={"changes": {"AG-1001": True, "AG-1002": True}},
        )
        assert r.status_code == 200
        assert r.json() == {"approved_ids": ["AG-1001", "AG-1002"]}

        # GET reflects the writes
        r = client.get(f"/runs/{run_id}/stories/approvals")
        assert r.json() == {"approved_ids": ["AG-1001", "AG-1002"]}


def test_post_unapprove_deletes_row(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _make_run(client)
        client.post(
            f"/runs/{run_id}/stories/approvals",
            json={"changes": {"AG-1001": True}},
        )
        r = client.post(
            f"/runs/{run_id}/stories/approvals",
            json={"changes": {"AG-1001": False}},
        )
        assert r.json() == {"approved_ids": []}


def test_unknown_run_returns_404(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        r = client.get("/runs/does-not-exist/stories/approvals")
        assert r.status_code == 404
        r = client.post(
            "/runs/does-not-exist/stories/approvals",
            json={"changes": {"AG-1": True}},
        )
        assert r.status_code == 404


def test_idempotent_reapply(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _make_run(client)
        for _ in range(3):
            r = client.post(
                f"/runs/{run_id}/stories/approvals",
                json={"changes": {"AG-1001": True}},
            )
            assert r.json() == {"approved_ids": ["AG-1001"]}


def test_malformed_body_returns_422(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _make_run(client)
        # `changes` must be a dict[str, bool]; pass garbage
        r = client.post(
            f"/runs/{run_id}/stories/approvals",
            json={"changes": "not a dict"},
        )
        assert r.status_code == 422
