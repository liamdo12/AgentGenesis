"""Graph node: delegate frame extraction to the services facade.

`FrameExtractor.extract` writes manifest.json and returns the manifest dict.
Real provider runs ffmpeg; stub provider falls back to a canned manifest when
ffmpeg or the fixture mp4 is missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.logging import get_logger

log = get_logger("agentgenesis_api.graph.nodes.extract_frames")


def build(deps: NodeDeps):
    async def extract_frames(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("frames_manifest") is not None:
            return {"phase_label": "Extracting frames…", "progress": 0.75}

        src = Path(state["recording_path"])
        run_id = state["run_id"]
        run_dir = deps.settings.data_dir / "runs" / run_id

        manifest = await deps.services.frames.extract(src, run_dir, deps.settings)

        useful = manifest.get("useful_frame_count", 0)
        # Provider-attached warnings (e.g. stub canned-manifest reason) — pop so
        # they don't leak into manifest.json consumers.
        warnings: list[str] = list(manifest.pop("_warnings", []))
        frame_evidence_used = useful >= deps.settings.min_useful_frames
        if not frame_evidence_used:
            warnings.append(f"low_visual_signal: only {useful} frames extracted")
        log.info(
            "extract_frames.done",
            run_id=run_id,
            chunks=len(manifest.get("chunks", [])),
            useful_frame_count=useful,
            frame_evidence_used=frame_evidence_used,
        )
        return {
            "frames_manifest": manifest,
            "warnings": warnings,
            "phase_label": "Extracting frames…",
            "progress": 0.75,
        }

    extract_frames.__name__ = "extract_frames"
    return extract_frames
