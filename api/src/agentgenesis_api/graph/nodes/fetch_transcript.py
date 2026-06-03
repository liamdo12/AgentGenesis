"""Graph node: fetch + parse transcript via services facade.

Single attempt per node invocation. If the source reports the transcript is
not ready, we set `pending_reason` and let the runner promote the run to
PENDING_TRANSCRIPT for manual resume (POST /runs/{id}/resume).
"""

from __future__ import annotations

from typing import Any

from agentgenesis_api.auth.models import STUB_USER
from agentgenesis_api.graph.auth_context import current_user
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes._shared import lang_detect, vtt_parser
from agentgenesis_api.msgraph import TranscriptNotReady


def build(deps: NodeDeps):
    async def fetch_transcript(state: dict[str, Any]) -> dict[str, Any]:
        # Idempotent on resume — segments already produced → skip the fetch.
        if state.get("transcript_segments"):
            return {"phase_label": "Fetching transcript…", "progress": 0.20}

        meeting_id = state["meeting_id"]
        user = current_user.get() or STUB_USER
        try:
            artifact = await deps.services.meetings.get_transcript(user, meeting_id)
        except TranscriptNotReady:
            return {
                "phase_label": "Transcript not ready",
                "pending_reason": "transcript_not_ready",
            }

        result = vtt_parser.parse(artifact.vtt_text)
        detected = artifact.detected_language or lang_detect.detect(
            " ".join(s.text for s in result.segments[:50])
        )
        warnings = list(result.warnings or [])
        if not artifact.vtt_text:
            warnings.append("transcript empty")
        warnings.append(f"language={detected}")
        return {
            "transcript": artifact,
            "transcript_segments": [s.model_dump() for s in result.segments],
            "warnings": warnings,
            "phase_label": "Fetching transcript…",
            "progress": 0.20,
        }

    fetch_transcript.__name__ = "fetch_transcript"
    return fetch_transcript
