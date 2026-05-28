"""Tiny wrapper around `langdetect` with a deterministic seed.

`langdetect` is non-deterministic by default. We seed once at import so
repeated test runs yield the same answer for the same input.
"""

from langdetect import DetectorFactory
from langdetect import detect as _detect

DetectorFactory.seed = 0


def detect(text: str, default: str = "en") -> str:
    """Return ISO-639-1 code, or `default` if detection fails / text is too short."""
    sample = (text or "").strip()
    if len(sample) < 20:
        return default
    try:
        return _detect(sample)
    except Exception:
        return default
