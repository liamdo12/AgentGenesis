"""WEBVTT parser tests against the four Teams-realistic cue shapes."""

from pathlib import Path

from agentgenesis_api.graph.nodes._shared import vtt_parser

FIXTURE = Path(__file__).parent / "fixtures" / "sample.vtt"


def test_parse_fixture() -> None:
    result = vtt_parser.parse(FIXTURE.read_text())
    assert len(result.segments) == 4
    # Speakers come through.
    assert result.segments[0].speaker == "Alice Doe"
    assert result.segments[1].speaker == "Bob Smith"
    # No <v> tag → Unknown + warning.
    assert result.segments[2].speaker == "Unknown"
    assert any("no <v> tag" in w for w in result.warnings)
    # Nested formatting stripped.
    assert result.segments[3].speaker == "Carol Lee"
    assert "<b>" not in result.segments[3].text
    assert result.segments[3].text == "Bold nested formatting"


def test_parse_timing() -> None:
    result = vtt_parser.parse(FIXTURE.read_text())
    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 4.5
    assert result.segments[1].start == 5.0


def test_parse_missing_header() -> None:
    result = vtt_parser.parse("00:00:00.000 --> 00:00:01.000\n<v X>Hi.</v>\n")
    assert result.segments == []
    assert "WEBVTT" in result.warnings[0]


def test_parse_empty() -> None:
    result = vtt_parser.parse("WEBVTT\n")
    assert result.segments == []
