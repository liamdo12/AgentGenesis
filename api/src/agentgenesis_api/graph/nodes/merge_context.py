"""Graph node: build the MultimodalContext that the Claude nodes consume.

The build logic is exposed as `build_multimodal_context_from_state` so
downstream nodes (claude_summary) can re-derive the context idempotently
if a partial LangGraph checkpoint reaches them with the slice missing —
which can happen after server-restart during a paused parallel branch.
"""

from __future__ import annotations

from typing import Any

from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.logging import get_logger
from agentgenesis_api.synthesis.frame_selection import pick_evenly
from agentgenesis_api.synthesis.schemas import MultimodalContext, TimeWindow

log = get_logger("agentgenesis_api.graph.nodes.merge_context")


def build_multimodal_context_from_state(
    state: dict[str, Any], settings: Settings
) -> MultimodalContext:
    """Pure helper: derive a MultimodalContext from whatever state holds.

    Tolerant of missing `frames_manifest` (treats as empty manifest) and
    empty `transcript_segments`. Requires `meeting_ref` — raises KeyError
    if absent (callers should pre-check and surface a clearer error).
    """
    meeting_ref = state["meeting_ref"]
    manifest = state.get("frames_manifest") or {}
    manifest_frames = manifest.get("frames") or []
    segments = state.get("transcript_segments") or []
    duration = manifest.get("video", {}).get("duration_sec") or _segments_duration(segments)
    detected = _detected_language_from_warnings(state.get("warnings") or [])

    selected = pick_evenly(manifest_frames, settings.synth_max_frames_in_context)
    window_size = settings.chunk_window_sec
    windows = _build_windows(segments, manifest_frames, window_size, duration)

    return MultimodalContext(
        meeting=meeting_ref,
        duration_sec=duration,
        detected_language=detected,
        windows=windows,
        selected_frames=selected,
        frame_evidence_used=(len(selected) >= settings.min_useful_frames),
    )


def resolve_or_rebuild_multimodal_context(
    state: dict[str, Any], settings: Settings, *, node_name: str
) -> tuple[MultimodalContext, bool]:
    """Read multimodal_context from state; rebuild if missing.

    Returns (ctx, was_rebuilt). Callers should propagate the rebuilt
    slice back into state so downstream nodes don't repeat the work.
    Raises RuntimeError with state shape if rebuild is impossible
    (meeting_ref also missing).
    """
    raw = state.get("multimodal_context")
    if raw is not None:
        return MultimodalContext.model_validate(raw), False

    if "meeting_ref" not in state:
        log.error(
            f"{node_name}.unrecoverable_missing_meeting_ref_and_multimodal",
            run_id=state.get("run_id"),
            state_keys=sorted(state.keys()),
            pending_reason=state.get("pending_reason"),
        )
        raise RuntimeError(
            f"{node_name}: state is missing 'multimodal_context' AND "
            "'meeting_ref'. Cannot recover. "
            f"present state keys: {sorted(state.keys())}"
        )

    log.warning(
        f"{node_name}.rebuilding_multimodal_context",
        run_id=state.get("run_id"),
        state_keys=sorted(state.keys()),
        has_transcript_segments="transcript_segments" in state,
        has_frames_manifest="frames_manifest" in state,
        pending_reason=state.get("pending_reason"),
    )
    return build_multimodal_context_from_state(state, settings), True


def build(deps: NodeDeps):
    async def merge_context(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("multimodal_context") is not None:
            log.info(
                "merge_context.idempotent_skip",
                run_id=state.get("run_id"),
            )
            return {"phase_label": "Building multimodal context…", "progress": 0.80}

        if "meeting_ref" not in state:
            # Surface root cause: a parent branch (fetch_meeting_ref) failed
            # silently. Without meeting_ref we can't build the context, but
            # raising plain KeyError obscures the upstream failure.
            log.error(
                "merge_context.missing_meeting_ref",
                run_id=state.get("run_id"),
                state_keys=sorted(state.keys()),
            )
            raise RuntimeError(
                "merge_context: state missing 'meeting_ref' — fetch_meeting_ref did not run "
                f"(present keys: {sorted(state.keys())})"
            )

        ctx = build_multimodal_context_from_state(state, deps.settings)
        log.info(
            "merge_context.built",
            run_id=state.get("run_id"),
            windows=len(ctx.windows),
            selected_frames=len(ctx.selected_frames),
            duration_sec=ctx.duration_sec,
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
