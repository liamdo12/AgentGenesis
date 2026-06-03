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

    Node bodies consume `deps.services.X`. When `deps` is None (topology
    test path) we synthesize a NoopServices-backed NodeDeps so the graph
    compiles + traverses without invoking any external system.
    """
    g: StateGraph = StateGraph(GraphState)

    if deps is None:
        from agentgenesis_api.config import Settings
        from agentgenesis_api.services.noop import NoopServices

        deps = NodeDeps(
            settings=Settings(  # type: ignore[call-arg]
                environment="test",
                use_stub_nodes=True,
                anthropic_api_key="noop",
            ),
            services=NoopServices.create(),
        )

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
