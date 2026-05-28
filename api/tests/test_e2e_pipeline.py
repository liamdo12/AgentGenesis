"""End-to-end test driving the full real-node graph with fake MCP + fake Claude.

Exercises real code paths in every node (VTT parse, ffmpeg frame extraction,
context merging, story ID assignment, file writes) — only the two external
service boundaries are faked.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import HttpUrl

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.runner import GraphRunner
from agentgenesis_api.mcp import (
    MeetingRef,
    RecordingArtifact,
    TranscriptArtifact,
)
from agentgenesis_api.schemas import MeetingSummary, RunStatus
from agentgenesis_api.synthesis.schemas import (
    MultimodalContext,  # noqa: F401 — keeps import side-effect chain stable
)

FIXTURE_MP4 = Path(__file__).parent / "fixtures" / "sample-5s.mp4"
FIXTURE_VTT = (Path(__file__).parent / "fixtures" / "sample.vtt").read_text()


class _FakeMCP:
    def __init__(self, recording_bytes: bytes) -> None:
        self._recording = recording_bytes

    async def list_meeting_recordings(self, limit: int = 50) -> list[MeetingRef]:
        return [
            MeetingRef(
                id="m-e2e",
                title="Sprint Planning",
                organizer="Alice",
                start_iso=datetime(2026, 8, 22, tzinfo=UTC),
                duration_sec=5.0,
            )
        ]

    async def get_transcript(self, meeting_id: str) -> TranscriptArtifact:
        return TranscriptArtifact(meeting_id=meeting_id, vtt_text=FIXTURE_VTT)

    async def get_recording(self, meeting_id: str) -> RecordingArtifact:
        # E2E uses a local "data URL"-ish trick: the fetch_recording node will
        # try to httpx.GET the URL. We patch httpx in this test via a fixture.
        return RecordingArtifact(
            meeting_id=meeting_id,
            download_url=HttpUrl("https://example.invalid/rec.mp4"),
            content_type="video/mp4",
        )

    async def aclose(self) -> None: ...


class _FakeClaude:
    """Returns canned objects keyed by the schema requested."""

    def __init__(self) -> None:
        from agentgenesis_api.graph.nodes.claude_draft_stories import _LlmStoriesOutput, _LlmStory

        self._responses: dict[type, Any] = {
            MeetingSummary: MeetingSummary(
                summary="Team aligned on the Q3 plan.",
                key_decisions=["Adopt SSO across products."],
                action_items=["Alice: draft RFC by Friday."],
                detected_language="en",
                frame_evidence_used=True,
            ),
            _LlmStoriesOutput: _LlmStoriesOutput(
                stories=[
                    _LlmStory(
                        title="Single sign-on",
                        persona="corporate user",
                        want="log in with my company SSO",
                        benefit="I don't manage separate credentials",
                        ac="Given SSO is configured, when I visit the URL, then I see the Azure AD login.",
                        tags=["auth"],
                        priority="high",
                    ),
                    _LlmStory(
                        title="Transcript auto-fetch",
                        persona="product manager",
                        want="transcripts to load automatically",
                        benefit="I can start extracting stories immediately",
                        ac="Given I'm authenticated, when I select a meeting, then the transcript loads within 3 seconds.",
                        tags=["meetings"],
                        priority="medium",
                    ),
                    _LlmStory(
                        title="Bulk DevOps export",
                        persona="BA",
                        want="push approved stories to Azure DevOps in one click",
                        benefit="I save manual data entry time",
                        ac="Given approved stories, when I click Push, then PBIs appear in DevOps.",
                        tags=["devops"],
                        priority="med",
                    ),
                ]
            ),
        }

    async def structured_json(
        self, *, system: str, user_text: str, frame_paths=None, schema, max_tokens=4096,
    ):
        if schema in self._responses:
            return self._responses[schema]
        return schema()

    async def aclose(self) -> None: ...


@pytest.fixture
def fake_httpx(monkeypatch):
    """Patch httpx.AsyncClient used by fetch_recording to serve the local fixture mp4."""
    import agentgenesis_api.graph.nodes.fetch_recording as fr_mod

    body = FIXTURE_MP4.read_bytes()

    class _Resp:
        headers = {"Content-Length": str(len(body))}

        def raise_for_status(self) -> None: ...

        async def aiter_bytes(self, chunk_size: int):
            for i in range(0, len(body), chunk_size):
                yield body[i : i + chunk_size]

    class _Stream:
        async def __aenter__(self) -> _Resp:
            return _Resp()

        async def __aexit__(self, *a): ...

    class _Client:
        def __init__(self, *a, **kw): ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a): ...

        def stream(self, method: str, url: str) -> _Stream:
            return _Stream()

    monkeypatch.setattr(fr_mod.httpx, "AsyncClient", _Client)


async def test_extraction_pipeline_end_to_end(tmp_path: Path, fake_httpx) -> None:
    settings = Settings(  # type: ignore[call-arg]
        teams_mcp_url=HttpUrl("http://localhost:3000/mcp"),
        anthropic_api_key="test",  # type: ignore[arg-type]
        data_dir=tmp_path,
        frame_interval_sec=1,
        chunk_window_sec=2,
        min_useful_frames=1,
        max_concurrent_runs=1,
        synth_max_frames_in_context=4,
    )
    fake_mcp = _FakeMCP(FIXTURE_MP4.read_bytes())
    fake_claude = _FakeClaude()

    runner = GraphRunner(settings, mcp=fake_mcp, claude=fake_claude)  # type: ignore[arg-type]
    await runner.startup()
    try:
        run = await runner.submit("m-e2e")
        # Poll until done or timeout.
        deadline = asyncio.get_event_loop().time() + 30.0
        while True:
            current = await runner.get(run.id)
            assert current is not None
            if current.status in (RunStatus.DONE, RunStatus.FAILED):
                break
            if asyncio.get_event_loop().time() > deadline:
                pytest.fail(f"run timed out; last status={current.status} err={current.error}")
            await asyncio.sleep(0.05)
        assert current.status == RunStatus.DONE, current.error
        assert current.progress == 1.0

        out_dir = tmp_path / "runs" / run.id

        # Source recording ended up on disk.
        assert (out_dir / "source" / "recording.mp4").is_file()

        # Frame manifest produced ≥1 useful frame.
        manifest = json.loads((out_dir / "manifest.json").read_text())
        assert manifest["useful_frame_count"] >= 1
        # Every claimed frame exists.
        for f in manifest["frames"]:
            assert (out_dir / f["path"]).is_file()

        # Summary and stories produced.
        summary = json.loads((out_dir / "summary.json").read_text())
        assert summary["detected_language"] == "en"

        stories = json.loads((out_dir / "stories.json").read_text())
        assert 3 <= len(stories["stories"]) <= 8
        # Server-assigned IDs starting at AG-1001.
        ids = [s["id"] for s in stories["stories"]]
        assert ids[0] == "AG-1001"
        assert all(s["id"].startswith("AG-1") and int(s["id"][3:]) >= 1001 for s in stories["stories"])
        # ac is a STRING per frontend Story type.
        assert all(isinstance(s["ac"], str) for s in stories["stories"])
        # priority "medium" coerced to "med" by claude_draft_stories.
        assert all(s["priority"] in ("high", "med", "low") for s in stories["stories"])
        # meeting label formatted from MeetingRef.
        assert stories["stories"][0]["meeting"] == "Sprint Planning · Aug 22"
    finally:
        await runner.shutdown()
