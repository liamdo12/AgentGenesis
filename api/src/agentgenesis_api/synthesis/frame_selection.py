"""Pick K representative frames from a manifest's frame list.

Evenly-spaced strategy: index step = floor(N / K). Returns ≤ K frames.
"""

from __future__ import annotations

from agentgenesis_api.synthesis.schemas import FrameRef


def pick_evenly(manifest_frames: list[dict], k: int) -> list[FrameRef]:
    if k <= 0 or not manifest_frames:
        return []
    n = len(manifest_frames)
    if n <= k:
        step = 1
        count = n
    else:
        step = n // k
        count = k
    picked = [manifest_frames[i * step] for i in range(count)]
    return [FrameRef.model_validate(f) for f in picked]
