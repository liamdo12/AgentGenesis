"""Graph node: build the MultimodalContext that the Claude nodes consume."""

from __future__ import annotations

from typing import Any

from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.synthesis.frame_selection import pick_evenly
from agentgenesis_api.synthesis.schemas import MultimodalContext, TimeWindow


def build(deps: NodeDeps):
    async def merge_context(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("multimodal_context") is not None:
            return {"phase_label": "Building multimodal context…", "progress": 0.80}

        meeting_ref = state["meeting_ref"]
        manifest = state.get("frames_manifest") or {}
        manifest_frames = manifest.get("frames") or []
        segments = state.get("transcript_segments") or []
        duration = manifest.get("video", {}).get("duration_sec") or _segments_duration(segments)

        # detected_language was pushed into state.warnings by fetch_transcript.
        detected = _detected_language_from_warnings(state.get("warnings") or [])

        selected = pick_evenly(manifest_frames, deps.settings.synth_max_frames_in_context)
        window_size = deps.settings.chunk_window_sec
        windows = _build_windows(segments, manifest_frames, window_size, duration)

        ctx = MultimodalContext(
            meeting=meeting_ref,
            duration_sec=duration,
            detected_language=detected,
            windows=windows,
            selected_frames=selected,
            frame_evidence_used=(len(selected) >= deps.settings.min_useful_frames),
        )

        return {
            "multimodal_context": ctx.model_dump(),
            "phase_label": "Building multimodal context…",
            "progress": 0.80,
        }

    merge_context.__name__ = "merge_context"
    return merge_context


def _segments_duration(segments: list[dict]) -> float:
    if not segments:
        return 0.0
    return max(s["end"] for s in segments)


def _detected_language_from_warnings(warnings: list[str]) -> str:
    for w in warnings:
        if w.startswith("language="):
            return w[len("language=") :]
    return "en"


def _build_windows(
    segments: list[dict],
    manifest_frames: list[dict],
    window_sec: int,
    duration_sec: float,
) -> list[TimeWindow]:
    if duration_sec <= 0:
        return []
    out: list[TimeWindow] = []
    start = 0.0
    while start < duration_sec:
        end = min(start + window_sec, duration_sec)
        in_window = [s for s in segments if start <= s["start"] < end]
        speakers = sorted({s["speaker"] for s in in_window})
        text = " ".join(f"[{s['speaker']}] {s['text']}" for s in in_window)
        frame_paths = [f["path"] for f in manifest_frames if start <= f["timestamp_sec"] < end]
        out.append(
            TimeWindow(
                start=start,
                end=end,
                transcript_text=text,
                speakers=speakers,
                frame_paths=frame_paths,
            )
        )
        start = end
    return out
