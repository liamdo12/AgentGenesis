"""ffprobe wrapper for reading video duration."""

import asyncio
from pathlib import Path


class FFProbeError(RuntimeError):
    pass


async def get_duration(path: Path) -> float:
    """Return duration in seconds, or raise FFProbeError."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "csv=p=0",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise FFProbeError(f"ffprobe failed: {err.decode(errors='replace').strip()}")
    text = out.decode(errors="replace").strip()
    try:
        return float(text)
    except ValueError as e:
        raise FFProbeError(f"ffprobe returned unparseable duration: {text!r}") from e
