"""Graph node: stream the recording MP4 from Graph to local disk.

Critical per red-team Finding 4: Graph's `recordingContentUrl` is an
endpoint URL (NOT a signed URL). Every recording download MUST attach
`Authorization: Bearer {graph-token}`. The TokenBroker provides the bearer.

Writes to `source/recording.mp4.part` then atomic-renames on success so a
killed download never leaves a partial-looking file at the final path.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import httpx

from agentgenesis_api.auth.models import STUB_USER
from agentgenesis_api.graph.auth_context import current_user
from agentgenesis_api.graph.deps import NodeDeps


def build(deps: NodeDeps):
    async def fetch_recording(state: dict[str, Any]) -> dict[str, Any]:
        # Idempotent: skip if we already have the file on disk.
        existing = state.get("recording_path")
        if existing and Path(existing).is_file():
            return {"phase_label": "Downloading recording…", "progress": 0.35}

        meeting_id = state["meeting_id"]
        user = current_user.get() or STUB_USER
        if deps.graph is None:
            raise RuntimeError("graph client not configured")

        artifact = await deps.graph.get_recording(user, meeting_id)
        if artifact.download_url is None:
            raise RuntimeError("Graph returned no recordingContentUrl")

        # Bearer header for the content download — Graph's recordingContentUrl
        # is NOT a signed URL. Per red-team Finding 4.
        if deps.broker is None:
            raise RuntimeError("TokenBroker required to download recording content")
        bearer = await deps.broker.acquire_graph_token(user, deps.settings.graph_delegated_scopes)

        run_id = state["run_id"]
        source_dir = deps.settings.data_dir / "runs" / run_id / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        dest = source_dir / "recording.mp4"
        tmp = source_dir / "recording.mp4.part"

        timeout = httpx.Timeout(deps.settings.recording_download_timeout_sec)
        headers = {"Authorization": f"Bearer {bearer}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", str(artifact.download_url), headers=headers) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", "0"))
                _ensure_free_space(source_dir, total)
                with tmp.open("wb") as f:
                    async for chunk in r.aiter_bytes(deps.settings.recording_chunk_bytes):
                        f.write(chunk)
        tmp.rename(dest)
        return {
            "recording_path": str(dest),
            "phase_label": "Downloading recording…",
            "progress": 0.35,
        }

    fetch_recording.__name__ = "fetch_recording"
    return fetch_recording


def _ensure_free_space(path: Path, needed_bytes: int) -> None:
    """Refuse to start the download if the destination disk has < 2x the size free."""
    if needed_bytes <= 0:
        return
    usage = shutil.disk_usage(path)
    if usage.free < 2 * needed_bytes:
        raise RuntimeError(
            f"Insufficient disk: {usage.free} free, need {2 * needed_bytes} (2x recording size)"
        )
