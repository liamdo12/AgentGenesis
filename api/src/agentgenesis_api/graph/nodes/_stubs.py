"""Stub node bodies used until phases 4-6 wire the real implementations.

Each stub:
- Sleeps briefly to simulate work (so progress polling is meaningful).
- Returns a partial state update with the next `phase_label` and `progress`.

The topology is fixed in Phase 3 even though the bodies are placeholders, so
later phases can drop in real implementations without touching the builder.
"""

import asyncio

# Progress budget per node, summing to 1.0 across the graph. The stub values
# here mirror the eventual real distribution so polling looks realistic.
PROGRESS_AFTER = {
    "fetch_meeting_ref": 0.05,
    "fetch_transcript": 0.20,
    "fetch_recording": 0.35,
    "extract_frames": 0.75,
    "merge_context": 0.80,
    "claude_summary": 0.90,
    "claude_draft_stories": 1.00,
}

LABELS = {
    "fetch_meeting_ref": "Resolving meeting…",
    "fetch_transcript": "Fetching transcript…",
    "fetch_recording": "Downloading recording…",
    "extract_frames": "Extracting frames…",
    "merge_context": "Building multimodal context…",
    "claude_summary": "Summarizing with Claude…",
    "claude_draft_stories": "Drafting user stories…",
}


def _stub(name: str):
    """Build a stub node function for the given graph node name."""

    async def node(state):  # noqa: ANN001 — TypedDict shape varies
        await asyncio.sleep(0.05)
        return {
            "phase_label": LABELS[name],
            "progress": PROGRESS_AFTER[name],
        }

    node.__name__ = name
    return node


fetch_meeting_ref = _stub("fetch_meeting_ref")
fetch_transcript = _stub("fetch_transcript")
fetch_recording = _stub("fetch_recording")
extract_frames = _stub("extract_frames")
merge_context = _stub("merge_context")
claude_summary = _stub("claude_summary")
claude_draft_stories = _stub("claude_draft_stories")
