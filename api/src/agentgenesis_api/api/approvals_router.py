"""/runs/{id}/stories/approvals — per-user, per-story approval state.

Persisted in the `approval` table. Approval state survives server restarts
because runs are hydrated from `RunRow` on lifespan boot, so ownership
checks resolve even after a process recycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from agentgenesis_api.api.dependencies import get_session_factory
from agentgenesis_api.api.runs_router import get_runner
from agentgenesis_api.auth import User, require_user
from agentgenesis_api.db import repository

router = APIRouter()


class _ApprovalChanges(BaseModel):
    changes: dict[str, bool] = Field(default_factory=dict)


def _check_owns(request: Request, run_id: str, user_oid: str) -> None:
    runner = get_runner(request)
    # ownership-only — does NOT require stories.json on disk
    if runner.safe_resolve(run_id, ".", user_oid) is None:
        # 404 not 403 — never disclose existence of others' runs.
        raise HTTPException(status_code=404, detail="run not found")


@router.get("/runs/{run_id}/stories/approvals")
async def get_approvals(
    run_id: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> dict[str, list[str]]:
    _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)
    async with session_factory() as session:
        ids = await repository.get_approvals(
            session, run_id=run_id, user_oid=user.oid
        )
    return {"approved_ids": sorted(ids)}


@router.post("/runs/{run_id}/stories/approvals")
async def post_approvals(
    run_id: str,
    body: _ApprovalChanges,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> dict[str, list[str]]:
    _check_owns(request, run_id, user.oid)
    session_factory = get_session_factory(request)
    async with session_factory() as session:
        await repository.set_approvals(
            session, run_id=run_id, user_oid=user.oid, changes=body.changes
        )
        await session.commit()
        ids = await repository.get_approvals(
            session, run_id=run_id, user_oid=user.oid
        )
    return {"approved_ids": sorted(ids)}
