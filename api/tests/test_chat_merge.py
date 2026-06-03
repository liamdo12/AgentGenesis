"""Unit tests for services/chat.merge_revise_into_envelope — the missing piece
that turns Claude's `_LlmReviseStory` shape (no id/meeting/source_*) into a
valid `StoriesOutput` envelope. Without this the real-Claude path 500s on
`StoriesOutput.model_validate`.
"""

from datetime import UTC, datetime

from agentgenesis_api.schemas import StoriesOutput, Story
from agentgenesis_api.services.chat import (
    LlmStoriesReviseOutput,
    merge_revise_into_envelope,
)


def _envelope(*ids: str) -> StoriesOutput:
    return StoriesOutput(
        stories=[
            Story(
                id=i,
                title=f"t{i}",
                persona="user",
                want="x",
                benefit="y",
                ac="Given x when y then z",
                tags=[],
                priority="med",
                meeting="m-1",
            )
            for i in ids
        ],
        source_meeting_id="m-1",
        source_meeting_title="M One",
        generated_at=datetime.now(UTC),
    )


def test_merge_preserves_envelope_and_round_trips_ids():
    current = _envelope("AG-1001", "AG-1002")
    revised = LlmStoriesReviseOutput.model_validate({
        "stories": [
            {
                "id": "AG-1001",
                "title": "Updated title",
                "persona": "user",
                "want": "w",
                "benefit": "b",
                "ac": "Given x when y then z",
                "tags": [],
                "priority": "high",
            },
        ],
        "removed_ids": ["AG-1002"],
    })
    out = merge_revise_into_envelope(revised, current)
    # Round-trips through StoriesOutput validation (the real bug).
    serialized = out.model_dump_json()
    rebuilt = StoriesOutput.model_validate_json(serialized)
    assert rebuilt.source_meeting_id == "m-1"
    assert rebuilt.source_meeting_title == "M One"
    assert [s.id for s in rebuilt.stories] == ["AG-1001"]
    assert rebuilt.stories[0].title == "Updated title"


def test_merge_assigns_new_id_to_idless_stories():
    current = _envelope("AG-1001", "AG-1002")
    revised = LlmStoriesReviseOutput.model_validate({
        "stories": [
            {
                "id": "AG-1001",
                "title": "kept", "persona": "u", "want": "w", "benefit": "b",
                "ac": "Given x when y then z", "tags": [], "priority": "med",
            },
            {
                # New story (no id) — server must assign one.
                "title": "new", "persona": "u", "want": "w", "benefit": "b",
                "ac": "Given x when y then z", "tags": [], "priority": "low",
            },
        ],
        "removed_ids": [],
    })
    out = merge_revise_into_envelope(revised, current)
    ids = [s.id for s in out.stories]
    assert ids[0] == "AG-1001"
    assert ids[1].startswith("AG-") and ids[1] not in {"AG-1001", "AG-1002"}


def test_merge_coerces_invalid_priority():
    current = _envelope("AG-1001")
    revised = LlmStoriesReviseOutput.model_validate({
        "stories": [
            {
                "id": "AG-1001",
                "title": "x", "persona": "u", "want": "w", "benefit": "b",
                "ac": "Given x when y then z", "tags": [], "priority": "P1",
            },
        ],
        "removed_ids": [],
    })
    out = merge_revise_into_envelope(revised, current)
    assert out.stories[0].priority == "med"  # invalid → med
