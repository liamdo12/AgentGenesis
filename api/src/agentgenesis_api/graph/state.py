"""GraphState TypedDict shared across all extraction-pipeline nodes.

`total=False` means partial states checkpoint cleanly: each node returns only
the fields it produces. Phase-3 stubs touch `phase_label`/`progress`; later
phases fill in the typed payload fields.

Several fields are typed as `Any` for now to avoid premature coupling with
schemas owned by later phases (Segment, FramesManifest, MultimodalContext).
Those schemas will be tightened phase-by-phase as they're added.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from agentgenesis_api.mcp import MeetingRef, TranscriptArtifact
from agentgenesis_api.schemas import MeetingSummary, StoriesOutput


def _take_last(_a, b):
    """Reducer for fields written from parallel branches — keep latest."""
    return b


def _take_max(a: float | None, b: float | None) -> float:
    """Reducer for progress: monotonic across parallel branches."""
    if a is None:
        return float(b or 0.0)
    if b is None:
        return float(a)
    return max(float(a), float(b))


class GraphState(TypedDict, total=False):
    # Inputs
    run_id: str
    meeting_id: str

    # Populated during execution (typed where the schema exists)
    meeting_ref: MeetingRef
    transcript: TranscriptArtifact
    transcript_segments: list[Any]
    recording_path: str
    frames_manifest: dict[str, Any]
    multimodal_context: dict[str, Any]
    summary: MeetingSummary
    stories_output: StoriesOutput

    # Progress signaling — written from parallel branches, so reducers required.
    phase_label: Annotated[str, _take_last]
    progress: Annotated[float, _take_max]

    # Diagnostics — accumulate across nodes.
    warnings: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]

    # Sentinel used by Phase 4's fetch_transcript when Teams hasn't produced
    # the VTT yet — runner promotes the run to RunStatus.PENDING_TRANSCRIPT.
    pending_reason: Annotated[str, _take_last]
