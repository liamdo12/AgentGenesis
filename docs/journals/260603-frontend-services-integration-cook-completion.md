# Frontend Services Integration & Chat Edit API — Implementation Complete

**Date**: 2026-06-03 13:30
**Severity**: Medium
**Component**: Backend (API, DB, services), Frontend (hooks, SSE client), Tests
**Status**: Resolved

## What Happened

Shipped 7-phase frontend services integration: DB infrastructure (async SQLAlchemy 2.x + aiosqlite), approvals API, revisions store with atomic disk commits, SSE chat streaming, frontend hooks for run lifecycle/approvals/chat, and wired chat UI. All phases completed, 83 → 110 backend tests passing, TypeScript + ruff clean.

## The Brutal Truth

This was technically dense and deceptively complex. Multiple subsystems (async DB, FFmpeg stub synthesis, SSE streaming lifecycle, frontend state reconciliation) had to ship coherently. Code review caught a race condition in the StreamingResponse finalization that would have silently leaked stream counters on client disconnect — exactly the kind of bug that only surfaces under load.

The late schema change (widening `_LlmStory` to include optional `id`) came from the stub masking reality: the stub was dumping full objects, the real system wasn't. That's a testing friction point worth fixing.

## Technical Details

**Backend DB layer** (`api/db/engine.py`, `models/`): Async SQLAlchemy 2.x with aiosqlite, 4 new tables (Run, Approval, StoryRevision, ChatTurn). Initial greenlet import failure on async context manager — added `greenlet` to dependencies.

**Revision commits** (`services/revisions.py`): DB-first design. Disk (`stories.json`) is a cache; atomic `os.replace` after DB commit. If disk write fails, DB remains consistent. Restore path reads from DB, not stale disk snapshots.

**StreamingResponse lifecycle** (`api/routers/chat_router.py`): Original code caught `Exception`, missing `asyncio.CancelledError`. Counter leaked on client disconnect. Fixed with `_StreamResult` dataclass holder + Starlette `BackgroundTask` (always runs after body, even on cancel). Per-run counter decremented in `_finalize_and_release`'s `finally` block.

**Chat schema evolution** (`services/chat.py`): Plan locked `_LlmStory` without `id`. Real Claude respects the prompt instruction to preserve ids. Stub tests passed because stub emitted full `StoriesOutput.model_dump()`. Real responses 500'd on validation. Added `merge_revise_into_envelope` to round-trip responses through `StoriesOutput.model_validate`.

**Single-worker enforcement** (`main.py`): Per-run `asyncio.Lock` is in-process. Multi-worker would race revision commits silently. `_check_single_worker` raises at boot with actionable error.

**Frontend** (`app/src/lib`, `app/src/hooks`): `lib/story-types.ts` removed dead `Story.status` field. Approval state lives in `useApprovals(approved: Set<string>)` scoped per run. `use-run-lifecycle.ts` + `use-run-status.ts` + `use-chat.ts` with AbortController + SSE history hydration. `parse-sse.ts` handles fragmented deltas.

## What We Tried

1. Caught `Exception` in chat stream → code review flagged race. Switched to `BackgroundTask` + `finally` block.
2. Stub tests hid schema gap (missing `id`). Widened `_LlmReviseStory` late.
3. Missing `greenlet` transitive dep discovered at runtime → added to uv.

## Root Cause Analysis

1. **BackgroundTask race**: FastAPI `BackgroundTasks` parameter runs inside generator body, not guaranteed after response completes. Starlette `BackgroundTask` is explicit — safer for cleanup with side effects (counter decrement).
2. **Schema gap**: Stub implementation never validated against real Claude responses. Tests passed but deploy would fail.
3. **Single-worker silent racing**: In-process locks don't scale to multiple workers. Enforcement at boot prevents subtle corruption.

## Lessons Learned

- **Async cleanup is fragile.** Always use finally blocks for counter/resource decrements. Test under cancellation.
- **Stubs must validate same schema as real.** Stub tests passing ≠ system works. Add integration smoke test.
- **DB-first with disk cache requires atomic ordering.** Database is source of truth; disk is an optimization with fallback restore.
- **Multi-worker assumptions should fail loud at boot, not silently corrupt at runtime.**

## Next Steps

- Monitor SSE stream stability in production (15s heartbeat interval, BackgroundTask finalization).
- Add integration smoke test validating real Claude schema round-trip (not just stub).
- Follow-up: DB advisory locks for true multi-worker safety (out of scope).
- Verify bulkdelete gate (>1 threshold) in production rollout.
