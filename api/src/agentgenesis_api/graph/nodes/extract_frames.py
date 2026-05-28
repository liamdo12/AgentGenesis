"""Graph node: chunked parallel ffmpeg frame extraction.

Probes the recording duration, plans N chunks, runs M ≤ cpu_count parallel
ffmpegs, then writes manifest.json. Failed chunks are logged in the manifest
but don't abort siblings.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.nodes._shared import ffprobe, frames_manifest
from agentgenesis_api.graph.nodes._shared.chunker import plan_chunks
from agentgenesis_api.graph.nodes._shared.extractor import ChunkResult, extract_chunk
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.graph.nodes.extract_frames")


def build(deps: NodeDeps):
    async def extract_frames(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("frames_manifest") is not None:
            return {"phase_label": "Extracting frames…", "progress": 0.75}

        src = Path(state["recording_path"])
        if not src.is_file():
            raise RuntimeError(f"recording not found at {src}")

        duration = await ffprobe.get_duration(src)
        chunks = plan_chunks(duration, deps.settings.chunk_window_sec)
        if not chunks:
            raise RuntimeError(f"video has non-positive duration: {duration}")

        run_id = state["run_id"]
        out_dir = deps.settings.data_dir / "runs" / run_id
        frames_root = out_dir / "frames"
        frames_root.mkdir(parents=True, exist_ok=True)

        sem = asyncio.Semaphore(min(os.cpu_count() or 1, deps.settings.max_parallel_ffmpeg))

        async def run_one(c) -> ChunkResult:
            async with sem:
                return await extract_chunk(
                    c, src, frames_root, deps.settings.frame_interval_sec
                )

        raw_results = await asyncio.gather(*(run_one(c) for c in chunks), return_exceptions=True)
        results: list[ChunkResult] = []
        for c, r in zip(chunks, raw_results, strict=True):
            if isinstance(r, ChunkResult):
                results.append(r)
            else:
                results.append(
                    ChunkResult(
                        idx=c.idx,
                        start=c.start,
                        end=c.end,
                        frame_count=0,
                        status="error",
                        error=f"{type(r).__name__}: {r}",
                    )
                )

        manifest = frames_manifest.build(
            out_dir=out_dir,
            chunks_results=results,
            frame_interval_sec=deps.settings.frame_interval_sec,
            chunk_window_sec=deps.settings.chunk_window_sec,
            duration_sec=duration,
        )
        useful = manifest["useful_frame_count"]
        all_failed = all(r.status == "error" for r in results)
        if useful == 0 and all_failed:
            raise RuntimeError(
                "All ffmpeg chunks failed; no frames extracted. "
                f"First error: {results[0].error if results else 'no chunks'}"
            )

        warnings: list[str] = []
        frame_evidence_used = useful >= deps.settings.min_useful_frames
        if not frame_evidence_used:
            warnings.append(f"low_visual_signal: only {useful} frames extracted")

        log.info(
            "extract_frames.done",
            run_id=run_id,
            chunks=len(chunks),
            useful_frame_count=useful,
            frame_evidence_used=frame_evidence_used,
        )
        return {
            "frames_manifest": manifest,
            "phase_label": "Extracting frames…",
            "progress": 0.75,
            "warnings": warnings,
        }

    extract_frames.__name__ = "extract_frames"
    return extract_frames
