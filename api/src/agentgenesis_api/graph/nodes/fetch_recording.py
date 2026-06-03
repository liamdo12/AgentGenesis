"""Graph node: stream the recording to local disk via services facade.

The Bearer-header + atomic-rename logic lives in `RealServices.recording`;
stub mode swaps in fixture copy via `StubServices.recording`. Node body is
thin.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentgenesis_api.auth.models import STUB_USER
from agentgenesis_api.graph.auth_context import current_user
from agentgenesis_api.graph.deps import NodeDeps


def build(deps: NodeDeps):
    async def fetch_recording(state: dict[str, Any]) -> dict[str, Any]:
        existing = state.get("recording_path")
        if existing and Path(existing).is_file():
            return {"phase_label": "Downloading recording…", "progress": 0.35}

        meeting_id = state["meeting_id"]
        user = current_user.get() or STUB_USER
        run_id = state["run_id"]
        dest = deps.settings.data_dir / "runs" / run_id / "source" / "recording.mp4"

        await deps.services.recording.fetch_to(user, meeting_id, dest)

        # Stub provider may silently skip when the fixture mp4 is absent.
        # Surface a warning so the run trail records it; extract_frames handles
        # the missing-file case downstream.
        warnings: list[str] = []
        if not dest.is_file():
            warnings.append(f"recording missing at {dest}")
        return {
            "recording_path": str(dest),
            "warnings": warnings,
            "phase_label": "Downloading recording…",
            "progress": 0.35,
        }

    fetch_recording.__name__ = "fetch_recording"
    return fetch_recording
