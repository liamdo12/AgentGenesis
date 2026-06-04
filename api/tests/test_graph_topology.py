"""Compile the graph and assert nodes + edges match the documented topology.

Cheap defense against silently rearranging the pipeline. No business logic
runs — just compilation + structural inspection.
"""

from agentgenesis_api.graph.builder import NODE_NAMES, build_graph


def test_nodes_present() -> None:
    g = build_graph()
    # Compiled graph exposes its node names via `nodes` attribute (langgraph internals).
    declared = set(g.get_graph().nodes.keys()) - {"__start__", "__end__"}
    assert declared == set(NODE_NAMES)


def test_topology_edges() -> None:
    """Every edge in the documented diagram must exist on the compiled graph."""
    g = build_graph()
    edges = {(e.source, e.target) for e in g.get_graph().edges}

    # Serialized topology (June 2026). LangGraph 1.x BSP parallel-join
    # semantics fired merge_context before extract_frames completed,
    # producing empty multimodal_context. See builder.py header for why.
    expected = {
        ("__start__", "fetch_meeting_ref"),
        ("fetch_meeting_ref", "fetch_transcript"),
        ("fetch_transcript", "fetch_recording"),
        ("fetch_recording", "extract_frames"),
        ("extract_frames", "merge_context"),
        ("merge_context", "claude_summary"),
        ("claude_summary", "claude_draft_stories"),
        ("claude_draft_stories", "__end__"),
    }
    missing = expected - edges
    assert not missing, f"missing edges: {missing}"
