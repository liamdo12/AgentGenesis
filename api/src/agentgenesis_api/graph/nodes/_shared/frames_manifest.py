"""Build manifest.json from ChunkResult list + the actual files on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentgenesis_api.graph.nodes._shared.extractor import ChunkResult


def build(
    out_dir: Path,
    chunks_results: list[ChunkResult],
    frame_interval_sec: int,
    chunk_window_sec: int,
    duration_sec: float,
) -> dict[str, Any]:
    """Walk frames/*/ on disk; produce the manifest dict and write it to manifest.json.

    `out_dir` is the run's output_dir (parent of the `frames/` subdir).
    """
    frames_root = out_dir / "frames"
    chunks_payload: list[dict[str, Any]] = []
    frames_payload: list[dict[str, Any]] = []
    useful_frame_count = 0

    for cr in sorted(chunks_results, key=lambda c: c.idx):
        chunk_dir = frames_root / f"{cr.idx:04d}"
        files = sorted(chunk_dir.glob("frame_*.jpg")) if chunk_dir.exists() else []
        actual_count = len(files)
        useful_frame_count += actual_count
        chunks_payload.append(
            {
                "idx": cr.idx,
                "start": cr.start,
                "end": cr.end,
                "frame_count": actual_count,
                "status": cr.status,
                **({"error": cr.error} if cr.error else {}),
            }
        )
        for k, file in enumerate(files, start=1):
            ts = cr.start + (k - 1) * frame_interval_sec
            frames_payload.append(
                {
                    "chunk": cr.idx,
                    "frame": k,
                    "timestamp_sec": ts,
                    "path": str(file.relative_to(out_dir)),
                }
            )

    manifest = {
        "video": {
            "duration_sec": duration_sec,
            "frame_interval_sec": frame_interval_sec,
            "chunk_window_sec": chunk_window_sec,
        },
        "chunks": chunks_payload,
        "frames": frames_payload,
        "useful_frame_count": useful_frame_count,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
