"""Phase 4 node tests — fetch_meeting_ref, fetch_transcript, fetch_recording.

We construct a fake `TeamsMCPClient` (just object()-with-async-methods) so
node code paths run without network. Each test exercises one node's contract.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import HttpUrl

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes import (
    fetch_meeting_ref,
    fetch_recording,
    fetch_transcript,
)
from agentgenesis_api.mcp import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
    TranscriptNotReady,
)


class _FakeMCP:
    def __init__(self) -> None:
        self.recordings: list[MeetingRef] = []
        self.transcript: TranscriptArtifact | None = None
        self.recording: RecordingArtifact | None = None
        self.transcript_error: Exception | None = None

    async def list_meeting_recordings(self, limit: int = 50) -> list[MeetingRef]:
        return self.recordings

    async def get_transcript(self, meeting_id: str) -> TranscriptArtifact:
        if self.transcript_error is not None:
            raise self.transcript_error
        assert self.transcript is not None
        return self.transcript

    async def get_recording(self, meeting_id: str) -> RecordingArtifact:
        assert self.recording is not None
        return self.recording


def _deps(tmp_path: Path) -> tuple[NodeDeps, _FakeMCP]:
    settings = Settings(  # type: ignore[call-arg]
        teams_mcp_url=HttpUrl("http://localhost:3000/mcp"),
        anthropic_api_key="test",  # type: ignore[arg-type]
        data_dir=tmp_path,
    )
    mcp = _FakeMCP()
    return NodeDeps(settings=settings, mcp=mcp), mcp  # type: ignore[arg-type]


# ────────────────────────────── fetch_meeting_ref ──────────────────────────────


async def test_fetch_meeting_ref_finds_match(tmp_path: Path) -> None:
    deps, mcp = _deps(tmp_path)
    mcp.recordings = [
        MeetingRef(
            id="m1",
            title="Sprint",
            organizer="Alice",
            start_iso=datetime(2026, 5, 28, tzinfo=UTC),
            duration_sec=1800,
        )
    ]
    node = fetch_meeting_ref.build(deps)
    result = await node({"meeting_id": "m1"})
    assert result["meeting_ref"].id == "m1"


async def test_fetch_meeting_ref_not_found_raises(tmp_path: Path) -> None:
    deps, _ = _deps(tmp_path)
    node = fetch_meeting_ref.build(deps)
    with pytest.raises(RuntimeError, match="not found"):
        await node({"meeting_id": "missing"})


# ────────────────────────────── fetch_transcript ──────────────────────────────


VTT = (
    "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n<v Alice>Hello, this is a sentence in English.</v>\n"
)


async def test_fetch_transcript_parses_and_detects_language(tmp_path: Path) -> None:
    deps, mcp = _deps(tmp_path)
    mcp.transcript = TranscriptArtifact(meeting_id="m1", vtt_text=VTT)
    node = fetch_transcript.build(deps)
    result = await node({"meeting_id": "m1"})
    assert len(result["transcript_segments"]) == 1
    assert any("language=" in w for w in result["warnings"])


async def test_fetch_transcript_not_ready_sets_pending(tmp_path: Path) -> None:
    deps, mcp = _deps(tmp_path)
    mcp.transcript_error = TranscriptNotReady("m1")
    node = fetch_transcript.build(deps)
    result = await node({"meeting_id": "m1"})
    assert result.get("pending_reason") == "transcript_not_ready"
    # Importantly: no exception raised. Runner is responsible for promoting status.
    assert "transcript" not in result


async def test_fetch_transcript_is_idempotent(tmp_path: Path) -> None:
    """A resumed run with segments already present skips the MCP call."""
    deps, mcp = _deps(tmp_path)
    node = fetch_transcript.build(deps)
    state: dict[str, Any] = {"meeting_id": "m1", "transcript_segments": [{"index": 0}]}
    result = await node(state)
    # No segments returned (skip path), and no MCP call attempted.
    assert "transcript_segments" not in result
    assert mcp.transcript is None  # never set, never accessed


# ────────────────────────────── fetch_recording ──────────────────────────────


async def test_fetch_recording_streams_to_disk(tmp_path: Path, monkeypatch) -> None:
    deps, mcp = _deps(tmp_path)
    mcp.recording = RecordingArtifact(
        meeting_id="m1",
        download_url=HttpUrl("https://example.com/rec.mp4"),
        content_type="video/mp4",
    )

    # Stub httpx so we don't hit the network.
    class _FakeResponse:
        headers = {"Content-Length": "8"}

        def raise_for_status(self) -> None:
            return None

        async def aiter_bytes(self, chunk_size: int):
            yield b"\x00" * 4
            yield b"\x00" * 4

    class _FakeStream:
        async def __aenter__(self) -> _FakeResponse:
            return _FakeResponse()

        async def __aexit__(self, *a: Any) -> None:
            return None

    class _FakeClient:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        def stream(self, method: str, url: str) -> _FakeStream:
            return _FakeStream()

    import agentgenesis_api.graph.nodes.fetch_recording as fr_mod

    monkeypatch.setattr(fr_mod.httpx, "AsyncClient", _FakeClient)

    node = fetch_recording.build(deps)
    result = await node({"run_id": "run-abc", "meeting_id": "m1"})
    path = Path(result["recording_path"])
    assert path.is_file()
    assert path.read_bytes() == b"\x00" * 8
    # No leftover .part file.
    assert not path.with_suffix(".mp4.part").exists()


async def test_fetch_recording_no_url_raises(tmp_path: Path) -> None:
    deps, mcp = _deps(tmp_path)
    mcp.recording = RecordingArtifact(meeting_id="m1", download_url=None)
    node = fetch_recording.build(deps)
    with pytest.raises(RuntimeError, match="download_url"):
        await node({"run_id": "run-abc", "meeting_id": "m1"})
