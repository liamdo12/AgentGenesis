"""Phase 4 node tests — fetch_meeting_ref, fetch_transcript, fetch_recording.

Drives nodes against a fake `GraphClient` + fake `TokenBroker` (replacing the
deleted TeamsMCPClient fake). Each test exercises one node's contract.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes import (
    fetch_meeting_ref,
    fetch_recording,
    fetch_transcript,
)
from agentgenesis_api.msgraph import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
    TranscriptNotReady,
)


class _FakeGraph:
    def __init__(self) -> None:
        self.recordings: list[MeetingRef] = []
        self.transcript: TranscriptArtifact | None = None
        self.recording: RecordingArtifact | None = None
        self.transcript_error: Exception | None = None

    async def list_meeting_recordings(self, user, limit: int = 50) -> list[MeetingRef]:
        return self.recordings

    async def get_transcript(self, user, meeting_id: str) -> TranscriptArtifact:
        if self.transcript_error is not None:
            raise self.transcript_error
        assert self.transcript is not None
        return self.transcript

    async def get_recording(self, user, meeting_id: str) -> RecordingArtifact:
        assert self.recording is not None
        return self.recording


class _FakeBroker:
    async def acquire_graph_token(self, user, scopes) -> str:
        return "test-graph-token"


def _deps(tmp_path: Path) -> tuple[NodeDeps, _FakeGraph]:
    settings = Settings(  # type: ignore[call-arg]
        anthropic_api_key="test",  # type: ignore[arg-type]
        data_dir=tmp_path,
    )
    graph = _FakeGraph()
    deps = NodeDeps(settings=settings, graph=graph, broker=_FakeBroker(), claude=None)  # type: ignore[arg-type]
    return deps, graph


# ────────────────────────────── fetch_meeting_ref ──────────────────────────────


async def test_fetch_meeting_ref_finds_match(tmp_path: Path) -> None:
    deps, graph = _deps(tmp_path)
    graph.recordings = [
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
    deps, graph = _deps(tmp_path)
    graph.transcript = TranscriptArtifact(meeting_id="m1", vtt_text=VTT)
    node = fetch_transcript.build(deps)
    result = await node({"meeting_id": "m1"})
    assert len(result["transcript_segments"]) == 1
    assert any("language=" in w for w in result["warnings"])


async def test_fetch_transcript_not_ready_sets_pending(tmp_path: Path) -> None:
    deps, graph = _deps(tmp_path)
    graph.transcript_error = TranscriptNotReady("m1")
    node = fetch_transcript.build(deps)
    result = await node({"meeting_id": "m1"})
    assert result.get("pending_reason") == "transcript_not_ready"
    assert "transcript" not in result


async def test_fetch_transcript_is_idempotent(tmp_path: Path) -> None:
    """Resume path: segments already present → skip Graph call entirely."""
    deps, graph = _deps(tmp_path)
    node = fetch_transcript.build(deps)
    state: dict[str, Any] = {"meeting_id": "m1", "transcript_segments": [{"index": 0}]}
    result = await node(state)
    assert "transcript_segments" not in result
    assert graph.transcript is None


# ────────────────────────────── fetch_recording ──────────────────────────────


async def test_fetch_recording_streams_with_bearer(tmp_path: Path, monkeypatch) -> None:
    """Recording download MUST attach Authorization: Bearer. Per Finding 4."""
    deps, graph = _deps(tmp_path)
    graph.recording = RecordingArtifact(
        meeting_id="m1",
        download_url="https://graph.microsoft.com/v1.0/.../content",
        content_type="video/mp4",
    )

    captured_headers: dict = {}

    class _FakeResponse:
        headers = {"Content-Length": "8"}

        def raise_for_status(self) -> None: ...

        async def aiter_bytes(self, chunk_size: int):
            yield b"\x00" * 4
            yield b"\x00" * 4

    class _FakeStream:
        async def __aenter__(self) -> _FakeResponse:
            return _FakeResponse()

        async def __aexit__(self, *a: Any) -> None: ...

    class _FakeClient:
        def __init__(self, *a: Any, **kw: Any) -> None: ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a: Any) -> None: ...

        def stream(self, method: str, url: str, headers: dict | None = None) -> _FakeStream:
            captured_headers.update(headers or {})
            return _FakeStream()

    import agentgenesis_api.graph.nodes.fetch_recording as fr_mod

    monkeypatch.setattr(fr_mod.httpx, "AsyncClient", _FakeClient)

    node = fetch_recording.build(deps)
    result = await node({"run_id": "run-abc", "meeting_id": "m1"})

    path = Path(result["recording_path"])
    assert path.is_file()
    assert path.read_bytes() == b"\x00" * 8
    assert not path.with_suffix(".mp4.part").exists()
    # Authorization header must be present — this is the load-bearing assertion.
    assert captured_headers.get("Authorization") == "Bearer test-graph-token"


async def test_fetch_recording_no_url_raises(tmp_path: Path) -> None:
    deps, graph = _deps(tmp_path)
    graph.recording = RecordingArtifact(meeting_id="m1", download_url=None)
    node = fetch_recording.build(deps)
    with pytest.raises(RuntimeError, match="recordingContentUrl"):
        await node({"run_id": "run-abc", "meeting_id": "m1"})
