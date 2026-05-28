"""WEBVTT → list[Segment] parser tailored to Teams' cue shape.

Teams emits cues like:

    00:00:12.340 --> 00:00:18.910
    <v Alice Doe>Let's kick off the sprint review.</v>

Edge cases handled:
- Missing `<v ...>` tag → speaker = "Unknown" (caller adds a warning).
- Nested formatting inside `<v>` → inner tags stripped, keep text.
- Malformed cue (missing `-->`) → skipped, returned in `warnings`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agentgenesis_api.schemas import Segment

# `HH:MM:SS.mmm --> HH:MM:SS.mmm` (allows optional cue settings after).
_TIMING_RE = re.compile(
    r"^\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)
# `<v Speaker Name>...</v>` (closing tag optional in some emitters).
_SPEAKER_RE = re.compile(r"<v\s+([^>]+?)>(.*?)(?:</v>|$)", re.DOTALL)
# Any remaining XML/HTML tag (for nested formatting).
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class ParseResult:
    segments: list[Segment]
    warnings: list[str]


def parse(vtt_text: str) -> ParseResult:
    """Single-pass parse. ParseResult.warnings lists every cue we skipped."""
    if not vtt_text.lstrip().upper().startswith("WEBVTT"):
        return ParseResult(segments=[], warnings=["vtt missing WEBVTT header"])

    segments: list[Segment] = []
    warnings: list[str] = []
    idx = 0

    # Split on blank lines = cue boundaries.
    for block in _split_blocks(vtt_text):
        # Strip leading cue id line if present (a non-timing first line).
        lines = block.splitlines()
        if not lines:
            continue
        timing_idx = 0
        if not _TIMING_RE.match(lines[0]):
            # First line might be a cue id; second line is timing.
            if len(lines) > 1 and _TIMING_RE.match(lines[1]):
                timing_idx = 1
            else:
                # Header (WEBVTT, NOTE blocks, etc.) — skip silently.
                if not _looks_like_cue_block(lines):
                    continue
                warnings.append(f"cue block has no timing line: {lines[0][:40]!r}")
                continue
        m = _TIMING_RE.match(lines[timing_idx])
        if m is None:
            warnings.append(f"cue block timing parse failed: {lines[timing_idx][:40]!r}")
            continue
        start = _hms_to_sec(*m.groups()[:4])
        end = _hms_to_sec(*m.groups()[4:])
        payload = "\n".join(lines[timing_idx + 1 :]).strip()
        speaker, text = _extract_speaker_and_text(payload)
        if speaker == "Unknown":
            warnings.append(f"cue at {start:.2f}s has no <v> tag")
        segments.append(Segment(index=idx, start=start, end=end, speaker=speaker, text=text))
        idx += 1

    return ParseResult(segments=segments, warnings=warnings)


def _split_blocks(text: str) -> list[str]:
    """Split on blank lines, skip the leading WEBVTT block."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if blocks and blocks[0].upper().startswith("WEBVTT"):
        blocks = blocks[1:]
    return blocks


def _looks_like_cue_block(lines: list[str]) -> bool:
    return any("-->" in line for line in lines)


def _hms_to_sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _extract_speaker_and_text(payload: str) -> tuple[str, str]:
    m = _SPEAKER_RE.search(payload)
    if m is not None:
        speaker = m.group(1).strip()
        inner = m.group(2)
        text = _TAG_RE.sub("", inner).strip()
        return speaker, text
    text = _TAG_RE.sub("", payload).strip()
    return "Unknown", text
