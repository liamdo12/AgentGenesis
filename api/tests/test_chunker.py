"""Unit tests for plan_chunks (pure function, no IO)."""

from agentgenesis_api.graph.nodes._shared.chunker import plan_chunks


def test_single_chunk_when_duration_under_window() -> None:
    chunks = plan_chunks(120, 600)
    assert len(chunks) == 1
    assert chunks[0].start == 0.0
    assert chunks[0].end == 120


def test_exact_multiple() -> None:
    chunks = plan_chunks(1800, 600)
    assert len(chunks) == 3
    assert [c.end for c in chunks] == [600, 1200, 1800]


def test_remainder_chunk_is_shorter() -> None:
    chunks = plan_chunks(1234, 600)
    assert len(chunks) == 3
    assert chunks[-1].start == 1200
    assert chunks[-1].end == 1234
    assert chunks[-1].duration == 34


def test_zero_or_negative_duration_returns_empty() -> None:
    assert plan_chunks(0, 600) == []
    assert plan_chunks(-5, 600) == []


def test_zero_window_returns_empty() -> None:
    assert plan_chunks(100, 0) == []


def test_indices_are_sequential() -> None:
    chunks = plan_chunks(2500, 600)
    assert [c.idx for c in chunks] == [0, 1, 2, 3, 4]
