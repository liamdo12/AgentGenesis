"""GraphRunner — schedules + tracks extraction runs as asyncio.Tasks.

Two stores of truth interact:

- LangGraph checkpoint (durable, via SqliteSaver) — owns the full graph state.
- `Run` model (in-memory) — projection of graph state useful for the /runs API.

The runner is the only place that writes both. On every graph.astream update
it copies `phase_label`, `progress`, and (when terminal) `status`/`error` from
the graph state into the in-memory `Run`. The two never diverge because the
runner is the single writer.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from langgraph.graph.state import CompiledStateGraph

from agentgenesis_api.auth.models import User
from agentgenesis_api.config import Settings
from agentgenesis_api.graph.auth_context import current_user
from agentgenesis_api.graph.builder import build_graph
from agentgenesis_api.graph.checkpointer import build_checkpointer
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.logging import get_logger
from agentgenesis_api.schemas import Run, RunStatus

log = get_logger("agentgenesis_api.graph.runner")


class RunStoreFull(Exception):
    """Raised when max_concurrent_runs is hit."""


class GraphRunner:
    def __init__(self, settings: Settings, *, deps: NodeDeps | None = None):
        self._settings = settings
        self._deps = deps
        self._sem = asyncio.Semaphore(settings.max_concurrent_runs)
        self._runs: OrderedDict[str, Run] = OrderedDict()
        self._tasks: dict[str, asyncio.Task] = {}
        self._stack: AsyncExitStack | None = None
        self._graph: CompiledStateGraph | None = None
        self._lock = asyncio.Lock()

    async def startup(self) -> None:
        self._stack = AsyncExitStack()
        checkpointer = await self._stack.enter_async_context(build_checkpointer(self._settings))
        self._graph = build_graph(checkpointer, deps=self._deps)
        log.info(
            "graph.startup",
            data_dir=str(self._settings.data_dir),
            wired=self._deps is not None,
        )

    async def shutdown(self) -> None:
        # Cancel anything in-flight before tearing down the checkpointer.
        for task in list(self._tasks.values()):
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._graph = None

    async def submit(self, meeting_id: str, user: User) -> Run:
        if len(self._tasks) >= self._settings.max_concurrent_runs:
            raise RunStoreFull(f"max_concurrent_runs={self._settings.max_concurrent_runs} reached")
        run_id = uuid4().hex
        output_dir = self._settings.data_dir / "runs" / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        run = Run(
            id=run_id,
            meeting_id=meeting_id,
            user_oid=user.oid,
            status=RunStatus.PENDING,
            progress=0.0,
            error=None,
            created_at=datetime.now(UTC),
            finished_at=None,
            output_dir=str(output_dir),
        )
        async with self._lock:
            self._runs[run_id] = run
        task = asyncio.create_task(self._execute(run_id, resume=False, user=user))
        self._tasks[run_id] = task
        return run

    async def resume(self, run_id: str, user: User) -> Run:
        """Resume a paused run; user must own the run."""
        run = self._runs.get(run_id)
        if run is None or run.user_oid != user.oid:
            raise KeyError(run_id)  # 404 — never disclose existence of others' runs
        if run_id in self._tasks and not self._tasks[run_id].done():
            return run  # already running
        async with self._lock:
            run.status = RunStatus.PENDING
            run.error = None
        task = asyncio.create_task(self._execute(run_id, resume=True, user=user))
        self._tasks[run_id] = task
        return run

    async def get(self, run_id: str, user_oid: str) -> Run | None:
        """User-scoped lookup. Returns None if the run doesn't belong to user."""
        run = self._runs.get(run_id)
        if run is None or run.user_oid != user_oid:
            return None
        return run

    async def list(self, user_oid: str, limit: int = 100) -> list[Run]:
        """List only the calling user's runs, newest first."""
        own = [r for r in reversed(self._runs.values()) if r.user_oid == user_oid]
        return own[:limit]

    async def _execute(self, run_id: str, *, resume: bool, user: User) -> None:
        assert self._graph is not None
        config = {"configurable": {"thread_id": run_id}}
        initial = None if resume else {
            "run_id": run_id,
            "meeting_id": self._runs[run_id].meeting_id,
            "progress": 0.0,
            "phase_label": "Queued",
            "warnings": [],
            "errors": [],
        }
        # Set per-task user context — nodes read via `current_user.get()`.
        # The ContextVar dies with this task; no cleanup beyond reset().
        token = current_user.set(user)
        try:
            async with self._sem:
                try:
                    async for event in self._graph.astream(
                        initial, config=config, stream_mode="values"
                    ):
                        await self._project(run_id, event)
                    await self._mark_done(run_id)
                except asyncio.CancelledError:
                    log.info("run.cancelled", run_id=run_id)
                    raise
                except Exception as e:
                    log.exception("run.failed", run_id=run_id, error=str(e))
                    await self._mark_failed(run_id, str(e))
        finally:
            current_user.reset(token)
            self._tasks.pop(run_id, None)

    async def _project(self, run_id: str, state: dict) -> None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            if "progress" in state:
                run.progress = float(state["progress"])
            label = state.get("phase_label", "")
            run.status = _label_to_status(label, current=run.status)
            if state.get("pending_reason") == "transcript_not_ready":
                run.status = RunStatus.PENDING_TRANSCRIPT

    async def _mark_done(self, run_id: str) -> None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            if run.status != RunStatus.PENDING_TRANSCRIPT:
                run.status = RunStatus.DONE
                run.progress = 1.0
            run.finished_at = datetime.now(UTC)

    async def _mark_failed(self, run_id: str, error: str) -> None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = RunStatus.FAILED
            run.error = error
            run.finished_at = datetime.now(UTC)

    def safe_resolve(self, run_id: str, rel_path: str, user_oid: str) -> Path | None:
        """Resolve a request path under the run's output_dir, blocking traversal
        AND enforcing per-user ownership. Returns None on miss or cross-user
        access (caller surfaces as 404 — no existence disclosure)."""
        run = self._runs.get(run_id)
        if run is None or run.user_oid != user_oid:
            return None
        base = Path(run.output_dir).resolve()
        candidate = (base / rel_path).resolve()
        if not candidate.is_relative_to(base):
            return None
        return candidate


# phase_label → RunStatus mapping. Anything we don't recognize keeps the
# existing status (so progress-only updates don't flip the status field).
_LABEL_TO_STATUS = {
    "Resolving meeting…": RunStatus.PENDING,
    "Fetching transcript…": RunStatus.FETCHING_TRANSCRIPT,
    "Downloading recording…": RunStatus.FETCHING_RECORDING,
    "Extracting frames…": RunStatus.EXTRACTING_FRAMES,
    "Building multimodal context…": RunStatus.SYNTHESIZING,
    "Summarizing with Claude…": RunStatus.SYNTHESIZING,
    "Drafting user stories…": RunStatus.SYNTHESIZING,
}


def _label_to_status(label: str, current: RunStatus) -> RunStatus:
    return _LABEL_TO_STATUS.get(label, current)
