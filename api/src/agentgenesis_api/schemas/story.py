"""Story schema.

Must mirror `design-system/src/lib/seed-data.tsx:Story` exactly so the LLM's
output drops into the frontend without translation. Notably `ac` is a single
string (Given/When/Then in one sentence), not a list.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Story(BaseModel):
    id: str
    title: str
    persona: str
    want: str
    benefit: str
    ac: str
    tags: list[str] = Field(default_factory=list)
    priority: Literal["high", "med", "low"]
    meeting: str


class StoriesOutput(BaseModel):
    stories: list[Story] = Field(default_factory=list)
    source_meeting_id: str
    source_meeting_title: str
    generated_at: datetime
