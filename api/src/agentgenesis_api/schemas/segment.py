"""Transcript segment (one VTT cue, parsed)."""

from pydantic import BaseModel


class Segment(BaseModel):
    index: int
    start: float       # seconds
    end: float         # seconds
    speaker: str       # "Unknown" if VTT cue lacked a <v> tag
    text: str
