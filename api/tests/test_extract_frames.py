"""Integration test — drives the extract_frames node against a real ffmpeg fixture."""

import json
from pathlib import Path

import pytest
from pydantic import HttpUrl

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes import extract_frames
from agentgenesis_api.graph.nodes._shared.chunker import Chunk, plan_chunks
from agentgenesis_api.graph.nodes._shared.extractor import extract_chunk
from agentgenesis_api.graph.nodes._shared.frames_manifest import build as build_manifest

FIXTURE = Path(__file__).parent / "fixtures" / "sample-5s.mp4"


def _deps(tmp_path: Path, *, interval: int = 1, window: int = 2) -> NodeDeps:
    settings = Settings(  # type: ignore[call-arg]
        teams_mcp_url=HttpUrl("http://localhost:3000/mcp"),
        anthropic_api_key="test",  # type: ignore[arg-type]
        data_dir=tmp_path,
        frame_interval_sec=interval,
        chunk_window_sec=window,
        min_useful_frames=1,
        max_parallel_ffmpeg=2,
    )
    return NodeDeps(settings=settings, graph=None)  # type: ignore[arg-type]


async def test_extract_chunk_produces_frames(tmp_path: Path) -> None:
    out_dir = tmp_path / "frames"
    out_dir.mkdir()
    chunk = Chunk(idx=0, start=0.0, end=2.0)
    result = await extract_chunk(chunk, FIXTURE, out_dir, frame_interval_sec=1)
    assert result.status == "ok", result.error
    assert result.frame_count >= 1


async def test_extract_frames_node_e2e(tmp_path: Path) -> None:
    """Drive the full node against the 5s fixture (interval=1s, window=2s → 3 chunks)."""
    deps = _deps(tmp_path, interval=1, window=2)
    run_id = "test-run"
    out_dir = tmp_path / "runs" / run_id
    out_dir.mkdir(parents=True)
    state = {
        "run_id": run_id,
        "recording_path": str(FIXTURE),
    }

    node = extract_frames.build(deps)
    result = await node(state)
    assert result["progress"] == 0.75

    manifest_path = out_dir / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["useful_frame_count"] >= 1
    # Every claimed frame path actually exists on disk.
    for f in manifest["frames"]:
        assert (out_dir / f["path"]).is_file()
    # All chunks should succeed for this fixture.
    assert all(c["status"] == "ok" for c in manifest["chunks"])


async def test_extract_frames_missing_recording_raises(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    node = extract_frames.build(deps)
    with pytest.raises(RuntimeError, match="recording not found"):
        await node({"run_id": "r", "recording_path": str(tmp_path / "missing.mp4")})


def test_manifest_handles_partial_failure(tmp_path: Path) -> None:
    """Pure unit-test for the manifest builder with a mixed result list."""
    from agentgenesis_api.graph.nodes._shared.extractor import ChunkResult

    out_dir = tmp_path / "runs" / "x"
    (out_dir / "frames" / "0000").mkdir(parents=True)
    (out_dir / "frames" / "0000" / "frame_00001.jpg").write_bytes(b"x")
    results = [
        ChunkResult(idx=0, start=0, end=10, frame_count=1, status="ok"),
        ChunkResult(idx=1, start=10, end=20, frame_count=0, status="error", error="boom"),
    ]
    manifest = build_manifest(
        out_dir=out_dir,
        chunks_results=results,
        frame_interval_sec=5,
        chunk_window_sec=10,
        duration_sec=20,
    )
    assert manifest["chunks"][1]["status"] == "error"
    assert manifest["chunks"][1]["error"] == "boom"
    assert manifest["useful_frame_count"] == 1


def test_plan_chunks_with_window_smaller_than_duration() -> None:
    chunks = plan_chunks(5.0, 2)
    assert len(chunks) == 3
    assert chunks[-1].end == 5.0
