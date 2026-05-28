"""Verify Pydantic Story schema matches the frontend `Story` shape.

The fixture below mirrors `design-system/src/lib/seed-data.tsx:AG_STORIES[0]`
field-for-field. If this test ever fails, the frontend type drifted and the
LLM output will no longer drop in cleanly.
"""

import json
from datetime import UTC, datetime

from agentgenesis_api.schemas import (
    MeetingSummary,
    Run,
    RunStatus,
    StoriesOutput,
    Story,
)

FRONTEND_STORY_FIXTURE = {
    "id": "AG-024",
    "title": "User authentication with SSO",
    "persona": "corporate user",
    "want": "log in using my company SSO",
    "benefit": "I don't manage separate credentials",
    "ac": "Given SSO is configured, when I visit the URL, then I see the Azure AD login prompt.",
    "tags": ["Auth"],
    "priority": "high",
    "meeting": "Sprint Planning · Aug 22",
}


def test_story_matches_frontend_shape() -> None:
    s = Story.model_validate(FRONTEND_STORY_FIXTURE)
    # Round-trip should equal the source dict (field-for-field).
    assert s.model_dump() == FRONTEND_STORY_FIXTURE


def test_ac_field_is_string_not_list() -> None:
    """The frontend Story.ac is `string`. Anything else breaks the UI."""
    s = Story.model_validate(FRONTEND_STORY_FIXTURE)
    assert isinstance(s.ac, str)


def test_stories_output_round_trip() -> None:
    out = StoriesOutput(
        stories=[Story.model_validate(FRONTEND_STORY_FIXTURE)],
        source_meeting_id="m-sprint-22",
        source_meeting_title="Sprint Planning",
        generated_at=datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC),
    )
    json_text = out.model_dump_json()
    reloaded = StoriesOutput.model_validate(json.loads(json_text))
    assert reloaded == out


def test_summary_defaults() -> None:
    s = MeetingSummary(summary="Brief.", frame_evidence_used=True)
    assert s.detected_language == "en"
    assert s.key_decisions == []


def test_summary_requires_frame_evidence_used() -> None:
    """frame_evidence_used has no default so audio-only runs can't be silently misreported."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MeetingSummary(summary="Brief.")  # type: ignore[call-arg]


def test_run_status_enum_values() -> None:
    # Spot-check the load-bearing PENDING_TRANSCRIPT value.
    assert RunStatus.PENDING_TRANSCRIPT == "pending_transcript"
    assert RunStatus.DONE == "done"


def test_run_round_trip() -> None:
    r = Run(
        id="abc123",
        meeting_id="m-1",
        status=RunStatus.PENDING,
        progress=0.0,
        error=None,
        created_at=datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC),
        finished_at=None,
        output_dir="data/runs/abc123",
    )
    assert Run.model_validate_json(r.model_dump_json()) == r
