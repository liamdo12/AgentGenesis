"""Plan chunks for parallel frame extraction.

Pure function. Boundary cases:
- duration ≤ 0 → empty list (caller treats this as "no video").
- duration ≤ window → single chunk covering the full duration.
- duration > window with remainder → final chunk is shorter.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    idx: int
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def plan_chunks(duration_sec: float, window_sec: int) -> list[Chunk]:
    if duration_sec <= 0 or window_sec <= 0:
        return []
    chunks: list[Chunk] = []
    start = 0.0
    idx = 0
    while start < duration_sec:
        end = min(start + window_sec, duration_sec)
        chunks.append(Chunk(idx=idx, start=start, end=end))
        start = end
        idx += 1
    return chunks
