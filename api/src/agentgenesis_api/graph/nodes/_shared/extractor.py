"""ffmpeg invocation that emits frames for a single chunk.

Each call spawns one ffmpeg process. Cancellation sends SIGTERM, then SIGKILL
after a grace period so a cancelled graph node never leaks subprocesses.
"""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass
from pathlib import Path

from agentgenesis_api.graph.nodes._shared.chunker import Chunk

_SIGKILL_GRACE_SEC = 5.0


@dataclass
class ChunkResult:
    idx: int
    start: float
    end: float
    frame_count: int
    status: str           # "ok" | "error"
    error: str | None = None


async def extract_chunk(
    chunk: Chunk,
    src: Path,
    out_dir: Path,
    frame_interval_sec: int,
    timeout_sec: float | None = None,
) -> ChunkResult:
    """Run ffmpeg for one chunk; return a ChunkResult (never raises for ffmpeg failures)."""
    chunk_dir = out_dir / f"{chunk.idx:04d}"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(chunk_dir / "frame_%05d.jpg")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{chunk.start}",
        "-to",
        f"{chunk.end}",
        "-i",
        str(src),
        "-vf",
        f"fps=1/{frame_interval_sec}",
        "-q:v",
        "4",
        pattern,
    ]

    if timeout_sec is None:
        # Generous default: 10× real-time, with a 30s floor for short chunks.
        timeout_sec = max(30.0, 10 * chunk.duration)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        try:
            async with asyncio.timeout(timeout_sec):
                _, stderr_bytes = await proc.communicate()
        except TimeoutError:
            await _terminate(proc)
            return ChunkResult(
                idx=chunk.idx,
                start=chunk.start,
                end=chunk.end,
                frame_count=_count_frames(chunk_dir),
                status="error",
                error=f"ffmpeg timed out after {timeout_sec}s",
            )
    except asyncio.CancelledError:
        await _terminate(proc)
        raise

    frame_count = _count_frames(chunk_dir)
    if proc.returncode != 0:
        return ChunkResult(
            idx=chunk.idx,
            start=chunk.start,
            end=chunk.end,
            frame_count=frame_count,
            status="error",
            error=stderr_bytes.decode(errors="replace").strip()[:2000],
        )

    return ChunkResult(
        idx=chunk.idx,
        start=chunk.start,
        end=chunk.end,
        frame_count=frame_count,
        status="ok",
    )


async def _terminate(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        async with asyncio.timeout(_SIGKILL_GRACE_SEC):
            await proc.wait()
    except (TimeoutError, ProcessLookupError):
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass


def _count_frames(chunk_dir: Path) -> int:
    return sum(1 for _ in chunk_dir.glob("frame_*.jpg"))
