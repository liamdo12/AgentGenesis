"""Chunked summarize + reduce for transcripts that exceed the token budget.

Used by claude_summary when the preflight estimate is over
`synth_max_input_tokens`. Stories are always extracted whole-meeting from the
reduced summary, never per-chunk.
"""

from __future__ import annotations

from agentgenesis_api.schemas import MeetingSummary
from agentgenesis_api.synthesis.claude_client import ClaudeClient
from agentgenesis_api.synthesis.prompts import REDUCE_SUMMARY_SYSTEM, SUMMARY_SYSTEM


def chunk_text(text: str, max_chars: int) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunks.append(text[start:end])
        start = end
    return chunks


async def run(
    client: ClaudeClient,
    transcript_text: str,
    max_chars_per_chunk: int,
) -> MeetingSummary:
    """Per-chunk summary, then reduce into one MeetingSummary."""
    chunks = chunk_text(transcript_text, max_chars_per_chunk)
    if not chunks:
        return MeetingSummary(summary="", frame_evidence_used=False)

    per_chunk: list[MeetingSummary] = []
    for i, ch in enumerate(chunks):
        user_text = (
            f"Per-chunk summarization. This is chunk {i + 1} of {len(chunks)}.\n\n"
            f"Transcript chunk:\n{ch}"
        )
        per_chunk.append(
            await client.structured_json(
                system=SUMMARY_SYSTEM,
                user_text=user_text,
                schema=MeetingSummary,
            )
        )

    # Reduce.
    user_text = (
        "Combine the following per-chunk meeting summaries into one. "
        "Each chunk follows the same JSON schema you must produce.\n\n"
        + "\n\n---\n\n".join(s.model_dump_json(indent=2) for s in per_chunk)
    )
    return await client.structured_json(
        system=REDUCE_SUMMARY_SYSTEM,
        user_text=user_text,
        schema=MeetingSummary,
    )
