"""/runs/{id}/chat — conversational story editor.

POST streams SSE: text deltas, then either a `revision` event (≤1 deletion
auto-applied) or a `revision_preview` event (>1 deletion gated behind an
explicit user accept). GET, restore, accept, delete-history round out the
surface.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.background import BackgroundTask

from agentgenesis_api.api.dependencies import get_session_factory
from agentgenesis_api.api.runs_router import get_runner
from agentgenesis_api.auth import User, require_user
from agentgenesis_api.db import repository
from agentgenesis_api.graph.runner import GraphRunner
from agentgenesis_api.logging import get_logger
from agentgenesis_api.schemas import StoriesOutput
from agentgenesis_api.services import PipelineServices
from agentgenesis_api.services.revisions import commit_revision, get_run_lock

router = APIRouter()
log = get_logger("agentgenesis_api.api.chat_router")

# Bulk-delete previews live in-process for ~5 minutes; restart loses
# pending previews (user reissues the chat turn). Keyed by preview_id.
_BULK_PREVIEW_TTL_SEC = 300.0
_bulk_previews: dict[str, tuple[float, str, str, dict, list[str]]] = {}
# (created_at, run_id, user_oid, stories_json_dict, removed_ids)

_BULK_DELETE_THRESHOLD = 1  # Auto-apply ≤1 removed; preview ≥2.


def _check_owns(request: Request, run_id: str, user_oid: str) -> Path:
    runner = get_runner(request)
    resolved = runner.safe_resolve(run_id, ".", user_oid)
    if resolved is None:
        raise HTTPException(status_code=404, detail="run not found")
    return resolved


class _ChatBody(BaseModel):
    message: str


def _sse(event: str, data: str) -> bytes:
    return f"event: {event}\ndata: {data}\n\n".encode()


def _services(request: Request) -> PipelineServices:
    svc = getattr(request.app.state, "services", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="services not initialized")
    return svc


@dataclass
class _StreamResult:
    """Holder the generator writes; the background task reads after the
    response body finishes (whether the client got it all, errored, or
    disconnected). Single-source-of-truth for the chat_turn finalize.
    """

    content_parts: list[str] = field(default_factory=list)
    revision_version: int | None = None
    status: str = "error"  # default to error so cancel paths persist as such
    error_detail: str | None = "stream ended without explicit completion"


@router.post("/runs/{run_id}/chat")
async def post_chat(
    run_id: str,
    body: _ChatBody,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
):
    run_dir = _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)
    services = _services(request)
    runner = get_runner(request)

    # Eagerly load current stories + history, eagerly create both turns so
    # they survive a Claude failure. Hold the per-run lock to serialize
    # against concurrent chats.
    lock = get_run_lock(run_id)
    async with lock:
        async with session_factory() as session:
            current_rev = await repository.get_latest_revision(
                session, run_id=run_id, user_oid=user.oid
            )
            if current_rev is None:
                raise HTTPException(
                    status_code=409,
                    detail="run has no stories revision yet; complete extraction first",
                )
            current_stories = StoriesOutput.model_validate_json(current_rev.content_json)
            history_rows = await repository.list_chat_turns(
                session, run_id=run_id, user_oid=user.oid, limit=50
            )
            history = [{"role": t.role, "content": t.content} for t in history_rows]
            await repository.append_chat_turn(
                session, run_id=run_id, user_oid=user.oid,
                role="user", content=body.message, status="done",
            )
            assistant_turn = await repository.append_chat_turn(
                session, run_id=run_id, user_oid=user.oid,
                role="assistant", content="", status="streaming",
            )
            await session.commit()
            assistant_id = assistant_turn.id

    runner.chat_stream_started()
    result = _StreamResult()

    async def _gen() -> AsyncIterator[bytes]:
        preview_id: str | None = None
        last_yield = asyncio.get_event_loop().time()
        try:
            async for chunk in services.synth.stream_chat(
                body.message, history, current_stories
            ):
                now = asyncio.get_event_loop().time()
                if now - last_yield > 15.0:
                    yield b": keep-alive\n\n"
                last_yield = now

                if chunk.get("type") == "text":
                    text = chunk.get("text", "")
                    result.content_parts.append(text)
                    yield _sse("text", json.dumps(text))
                elif chunk.get("type") == "stories":
                    removed = chunk.get("removed_ids", []) or []
                    stories_dict = chunk.get("stories") or {}
                    if len(removed) <= _BULK_DELETE_THRESHOLD:
                        async with get_run_lock(run_id):
                            async with session_factory() as session:
                                new_obj = StoriesOutput.model_validate(stories_dict)
                                v = await commit_revision(
                                    session,
                                    run_id=run_id,
                                    user_oid=user.oid,
                                    run_dir=run_dir,
                                    new=new_obj,
                                    source="chat",
                                )
                        result.revision_version = v
                        yield _sse(
                            "revision",
                            json.dumps({
                                "version": v,
                                "stories": stories_dict,
                                "removed_ids": removed,
                            }),
                        )
                    else:
                        preview_id = uuid4().hex
                        _bulk_previews[preview_id] = (
                            time.monotonic(), run_id, user.oid, stories_dict, removed
                        )
                        yield _sse(
                            "revision_preview",
                            json.dumps({
                                "preview_id": preview_id,
                                "stories": stories_dict,
                                "removed_ids": removed,
                            }),
                        )
            yield _sse(
                "done",
                json.dumps({
                    "revision_version": result.revision_version,
                    "preview_id": preview_id,
                }),
            )
            result.status = "done"
            result.error_detail = None
        except asyncio.CancelledError:
            # Client disconnected mid-stream. We've accumulated some text in
            # `result.content_parts`; mark the turn done with what we have so
            # the next visit shows the partial response rather than "error".
            log.info("chat.stream.cancelled", run_id=run_id, parts=len(result.content_parts))
            result.status = "done"
            result.error_detail = None
            raise
        except Exception as e:  # noqa: BLE001 — funnel to error event
            log.exception("chat.stream.failed", run_id=run_id)
            result.status = "error"
            result.error_detail = str(e)
            yield _sse("error", json.dumps({"detail": str(e), "code": "stream_failed"}))

    background = BackgroundTask(
        _finalize_and_release,
        session_factory=session_factory,
        runner=runner,
        turn_id=assistant_id,
        result=result,
    )

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
        background=background,
    )


async def _finalize_and_release(
    *,
    session_factory: async_sessionmaker,
    runner: GraphRunner,
    turn_id: int,
    result: _StreamResult,
) -> None:
    """Always runs after the response body completes (success / error /
    client-disconnect). Persists the assistant turn and decrements the
    in-flight chat counter so `drain_chat_streams` can finish on shutdown.
    """
    try:
        async with session_factory() as session:
            await repository.update_chat_turn(
                session,
                turn_id=turn_id,
                content="".join(result.content_parts),
                revision_version=result.revision_version,
                status=result.status,
                error_detail=result.error_detail,
            )
            await session.commit()
    except Exception:
        log.exception("chat.finalize_turn.failed", turn_id=turn_id)
    finally:
        runner.chat_stream_finished()


@router.get("/runs/{run_id}/chat/history")
async def get_chat_history(
    run_id: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> dict:
    _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)
    async with session_factory() as session:
        turns = await repository.list_chat_turns(
            session, run_id=run_id, user_oid=user.oid, limit=200
        )
    return {
        "turns": [
            {
                "id": t.id,
                "role": t.role,
                "content": t.content,
                "revision_version": t.revision_version,
                "status": t.status,
                "error_detail": t.error_detail,
                "created_at": t.created_at.isoformat(),
            }
            for t in turns
        ]
    }


@router.delete("/runs/{run_id}/chat/history")
async def delete_chat_history(
    run_id: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> dict:
    _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)
    async with session_factory() as session:
        n = await repository.delete_chat_history(
            session, run_id=run_id, user_oid=user.oid
        )
        await session.commit()
    return {"deleted": n}


@router.post("/runs/{run_id}/chat/revisions/{version}/restore")
async def restore_revision(
    run_id: str,
    version: int,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> dict:
    run_dir = _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)
    async with session_factory() as session:
        rev = await repository.get_revision(
            session, run_id=run_id, user_oid=user.oid, version=version
        )
        if rev is None:
            raise HTTPException(status_code=404, detail="revision not found")
        restored = StoriesOutput.model_validate_json(rev.content_json)

    lock = get_run_lock(run_id)
    async with lock:
        async with session_factory() as session:
            new_version = await commit_revision(
                session,
                run_id=run_id,
                user_oid=user.oid,
                run_dir=run_dir,
                new=restored,
                source="chat",
            )
    return {"version": new_version, "restored_from": version}


@router.post("/runs/{run_id}/chat/revisions/preview/{preview_id}/accept")
async def accept_preview(
    run_id: str,
    preview_id: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> dict:
    run_dir = _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)

    rec = _bulk_previews.get(preview_id)
    if rec is None or rec[1] != run_id or rec[2] != user.oid:
        raise HTTPException(status_code=404, detail="preview not found")
    created_at, _r, _u, stories_dict, removed = rec
    if time.monotonic() - created_at > _BULK_PREVIEW_TTL_SEC:
        _bulk_previews.pop(preview_id, None)
        raise HTTPException(status_code=410, detail="preview expired")

    lock = get_run_lock(run_id)
    async with lock:
        async with session_factory() as session:
            new = StoriesOutput.model_validate(stories_dict)
            new_version = await commit_revision(
                session,
                run_id=run_id,
                user_oid=user.oid,
                run_dir=run_dir,
                new=new,
                source="chat",
            )
    _bulk_previews.pop(preview_id, None)
    return {"version": new_version, "removed_ids": removed}
