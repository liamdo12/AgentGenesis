"""Graph node: fetch transcript via MCP, parse VTT, detect language.

Single attempt per node invocation. If MCP reports the transcript is not
ready, we set `pending_reason` and let the runner promote the run to
PENDING_TRANSCRIPT. The user resumes manually via POST /runs/{id}/resume
(see validate Q3 decision).
"""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes._shared import lang_detect, vtt_parser
from agentgenesis_api.mcp import TranscriptNotReady


def build(deps: NodeDeps):
    async def fetch_transcript(state: dict[str, Any]) -> dict[str, Any]:
        # Idempotent: don't re-fetch on resume after we already produced segments.
        if state.get("transcript_segments"):
            return {"phase_label": "Fetching transcript…", "progress": 0.20}

        meeting_id = state["meeting_id"]
        try:
            artifact = await deps.mcp.get_transcript(meeting_id)
        except TranscriptNotReady:
            return {
                "phase_label": "Transcript not ready",
                "pending_reason": "transcript_not_ready",
            }

        result = vtt_parser.parse(artifact.vtt_text)
        detected = artifact.detected_language or lang_detect.detect(
            " ".join(s.text for s in result.segments[:50])
        )
        return {
            "transcript": artifact,
            "transcript_segments": [s.model_dump() for s in result.segments],
            "warnings": result.warnings + [f"language={detected}"] if result.warnings else [f"language={detected}"],
            "phase_label": "Fetching transcript…",
            "progress": 0.20,
        }

    fetch_transcript.__name__ = "fetch_transcript"
    return fetch_transcript
