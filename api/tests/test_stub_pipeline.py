"""Smoke tests for fixture-backed stub pipeline (`AG_USE_STUB_NODES=1`).

Skipped automatically if `api/data/stub/sample.mp4` is absent — CI without the
fixture stays green; once the contributor drops a sample in, the suite locks
in stub behavior end-to-end.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentgenesis_api.config import Settings
from agentgenesis_api.main import create_app

FIXTURE_MP4 = Path(__file__).resolve().parents[1] / "data" / "stub" / "sample.mp4"
FIXTURE_EXAMPLE_VTT = FIXTURE_MP4.parent / "sample.example.vtt"


def _prep_stub_dir(tmp_path: Path) -> Path:
    """Copy the repo fixtures into tmp_path/stub so the test is hermetic."""
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    shutil.copy(FIXTURE_MP4, stub_dir / "sample.mp4")
    src_vtt = FIXTURE_MP4.parent / "sample.vtt"
    if src_vtt.is_file():
        shutil.copy(src_vtt, stub_dir / "sample.vtt")
    else:
        shutil.copy(FIXTURE_EXAMPLE_VTT, stub_dir / "sample.vtt")
    return stub_dir


def _poll_until_done(client: TestClient, run_id: str, *, timeout_sec: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        r = client.get(f"/runs/{run_id}")
        assert r.status_code == 200, r.text
        payload = r.json()
        if payload["status"] in ("done", "failed"):
            return payload
        time.sleep(0.25)
    raise AssertionError(f"run {run_id} did not reach terminal status in {timeout_sec}s: {payload}")


def test_stub_run_completes_with_canned_synthesis(tmp_path: Path, monkeypatch) -> None:
    """POST /runs → status=done → summary.json + stories.json on disk."""
    if not FIXTURE_MP4.is_file():
        pytest.skip(f"stub fixture missing at {FIXTURE_MP4}; see api/data/stub/README.md")
    _prep_stub_dir(tmp_path)
    monkeypatch.setenv("AG_USE_STUB_NODES", "1")
    monkeypatch.setenv("AG_ANTHROPIC_API_KEY", "stub")
    monkeypatch.setenv("AG_DATA_DIR", str(tmp_path))

    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        r = client.post("/runs", json={"meeting_id": "stub-meeting-1"})
        # runs_router declares status_code=status.HTTP_202_ACCEPTED.
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]

        payload = _poll_until_done(client, run_id)
        assert payload["status"] == "done", payload

        # The Run schema doesn't embed synthesis; fetch via the files endpoint
        # that nodes' on-disk writes feed.
        rs = client.get(f"/runs/{run_id}/files/summary.json")
        assert rs.status_code == 200, rs.text
        summary = rs.json()
        assert summary["summary"], "summary text is empty"
        assert len(summary["key_decisions"]) >= 1

        rs = client.get(f"/runs/{run_id}/files/stories.json")
        assert rs.status_code == 200, rs.text
        stories = rs.json()
        assert len(stories["stories"]) >= 2
        assert all(s["id"].startswith("AG-") for s in stories["stories"]), stories
        assert stories["stories"][0]["ac"], "story AC is empty"


def test_stub_extract_frames_branches_on_ffmpeg(tmp_path: Path, monkeypatch) -> None:
    """Force the canned-manifest branch via monkeypatched shutil.which."""
    if not FIXTURE_MP4.is_file():
        pytest.skip(f"stub fixture missing at {FIXTURE_MP4}")
    _prep_stub_dir(tmp_path)
    monkeypatch.setenv("AG_USE_STUB_NODES", "1")
    monkeypatch.setenv("AG_ANTHROPIC_API_KEY", "stub")
    monkeypatch.setenv("AG_DATA_DIR", str(tmp_path))

    # Scope the patch tightly so other `which` lookups behave normally.
    real_which = shutil.which
    monkeypatch.setattr(
        "agentgenesis_api.graph.nodes.extract_frames.shutil.which",
        lambda name: None if name == "ffmpeg" else real_which(name),
    )
    # Also patch the main module's `shutil.which` so the lifespan check sees
    # ffmpeg-missing and logs the warning instead of refusing to boot.
    monkeypatch.setattr(
        "agentgenesis_api.main.shutil.which",
        lambda name: None if name == "ffmpeg" else real_which(name),
    )

    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        r = client.post("/runs", json={"meeting_id": "stub-meeting-ffmpeg"})
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]
        payload = _poll_until_done(client, run_id)
        assert payload["status"] == "done", payload

        rm = client.get(f"/runs/{run_id}/files/manifest.json")
        assert rm.status_code == 200, rm.text
        manifest = json.loads(rm.text)
        assert manifest["useful_frame_count"] == 0, manifest
