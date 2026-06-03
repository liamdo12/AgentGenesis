"""Builds the LangGraph StateGraph for the extraction pipeline.

Topology:

    START
      │
      ▼
    fetch_meeting_ref
      │
      ├── fetch_transcript ───┐
      │                       ▼
      └── fetch_recording ─► extract_frames
                              │
                              ▼ (join)
                        merge_context
                              │
                              ▼
                        claude_summary
                              │
                              ▼
                      claude_draft_stories
                              │
                              ▼
                             END

`fetch_transcript` and `fetch_recording → extract_frames` run as parallel
branches from `fetch_meeting_ref`. `merge_context` is the join point.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes import (
    _stubs,
    claude_draft_stories,
    claude_summary,
    extract_frames,
    fetch_meeting_ref,
    fetch_recording,
    fetch_transcript,
    merge_context,
)
from agentgenesis_api.graph.state import GraphState

NODE_NAMES = (
    "fetch_meeting_ref",
    "fetch_transcript",
    "fetch_recording",
    "extract_frames",
    "merge_context",
    "claude_summary",
    "claude_draft_stories",
)


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    deps: NodeDeps | None = None,
):
    """Compile the extraction graph.

    When `deps` is None, every node is a stub (used by tests and by Phase 3
    smoke tests). When `deps` is supplied, real implementations for the nodes
    that already exist replace the stubs; the rest stay stubbed until later
    phases land.
    """
    g: StateGraph = StateGraph(GraphState)

    if deps is None:
        # Bare-bones path: all _stubs.py no-ops. Used by existing unit tests.
        g.add_node("fetch_meeting_ref", _stubs.fetch_meeting_ref)
        g.add_node("fetch_transcript", _stubs.fetch_transcript)
        g.add_node("fetch_recording", _stubs.fetch_recording)
        g.add_node("extract_frames", _stubs.extract_frames)
        g.add_node("merge_context", _stubs.merge_context)
        g.add_node("claude_summary", _stubs.claude_summary)
        g.add_node("claude_draft_stories", _stubs.claude_draft_stories)
    elif deps.stub_mode:
        # Stub mode: fixture-backed fetch_*/claude_* bodies, REAL frames/context.
        # Lazy import so production graph compile never imports _stubs_local.
        from agentgenesis_api.graph.nodes import _stubs_local
        g.add_node("fetch_meeting_ref", _stubs_local.fetch_meeting_ref(deps))
        g.add_node("fetch_transcript", _stubs_local.fetch_transcript(deps))
        g.add_node("fetch_recording", _stubs_local.fetch_recording(deps))
        g.add_node("extract_frames", extract_frames.build(deps))
        g.add_node("merge_context", merge_context.build(deps))
        g.add_node("claude_summary", _stubs_local.claude_summary(deps))
        g.add_node("claude_draft_stories", _stubs_local.claude_draft_stories(deps))
    else:
        g.add_node("fetch_meeting_ref", fetch_meeting_ref.build(deps))
        g.add_node("fetch_transcript", fetch_transcript.build(deps))
        g.add_node("fetch_recording", fetch_recording.build(deps))
        g.add_node("extract_frames", extract_frames.build(deps))
        g.add_node("merge_context", merge_context.build(deps))
        g.add_node("claude_summary", claude_summary.build(deps))
        g.add_node("claude_draft_stories", claude_draft_stories.build(deps))

    g.add_edge(START, "fetch_meeting_ref")
    g.add_edge("fetch_meeting_ref", "fetch_transcript")
    g.add_edge("fetch_meeting_ref", "fetch_recording")
    g.add_edge("fetch_recording", "extract_frames")
    g.add_edge("fetch_transcript", "merge_context")
    g.add_edge("extract_frames", "merge_context")
    g.add_edge("merge_context", "claude_summary")
    g.add_edge("claude_summary", "claude_draft_stories")
    g.add_edge("claude_draft_stories", END)

    return g.compile(checkpointer=checkpointer)
