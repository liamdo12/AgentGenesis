"""Async data-access helpers — thin wrappers over the four tables.

Functions accept an `AsyncSession` and never commit on the caller's behalf
unless that's the only sensible behavior (e.g. fire-and-forget upserts in
write-through paths). Where transactional semantics matter (multi-step
mutations), callers commit explicitly.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentgenesis_api.db.models import Approval, ChatTurn, RunRow, StoryRevision

# --- Run ---------------------------------------------------------------------


async def list_runs_all(session: AsyncSession) -> list[RunRow]:
    """All runs across users. Used by lifespan hydrate; never exposed via API."""
    res = await session.execute(select(RunRow))
    return list(res.scalars().all())


async def upsert_run(session: AsyncSession, *, run: RunRow) -> None:
    """Insert or update a RunRow. Caller commits."""
    existing = await session.get(RunRow, run.id)
    if existing is None:
        session.add(run)
        return
    existing.meeting_id = run.meeting_id
    existing.user_oid = run.user_oid
    existing.status = run.status
    existing.progress = run.progress
    existing.error = run.error
    existing.output_dir = run.output_dir
    existing.created_at = run.created_at
    existing.finished_at = run.finished_at


async def get_run(session: AsyncSession, *, run_id: str, user_oid: str) -> RunRow | None:
    row = await session.get(RunRow, run_id)
    if row is None or row.user_oid != user_oid:
        return None
    return row


# --- Approval ---------------------------------------------------------------


async def set_approvals(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    changes: dict[str, bool],
) -> None:
    """Upsert true rows; delete false rows. Caller commits."""
    for story_id, approved in changes.items():
        if approved:
            existing = await session.get(Approval, (run_id, story_id))
            if existing is None:
                session.add(Approval(
                    run_id=run_id,
                    story_id=story_id,
                    user_oid=user_oid,
                    approved=True,
                    updated_at=datetime.now(UTC),
                ))
            else:
                existing.approved = True
                existing.updated_at = datetime.now(UTC)
                existing.user_oid = user_oid
        else:
            await session.execute(
                delete(Approval).where(
                    Approval.run_id == run_id,
                    Approval.story_id == story_id,
                    Approval.user_oid == user_oid,
                )
            )


async def get_approvals(
    session: AsyncSession, *, run_id: str, user_oid: str
) -> set[str]:
    res = await session.execute(
        select(Approval.story_id).where(
            Approval.run_id == run_id,
            Approval.user_oid == user_oid,
            Approval.approved.is_(True),
        )
    )
    return set(res.scalars().all())


async def delete_approvals_not_in(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    keep_story_ids: list[str],
) -> int:
    """Drop approvals whose story_id is no longer in the current revision."""
    if not keep_story_ids:
        res = await session.execute(
            delete(Approval).where(
                Approval.run_id == run_id,
                Approval.user_oid == user_oid,
            )
        )
        return res.rowcount or 0
    res = await session.execute(
        delete(Approval).where(
            Approval.run_id == run_id,
            Approval.user_oid == user_oid,
            Approval.story_id.notin_(keep_story_ids),
        )
    )
    return res.rowcount or 0


# --- StoryRevision ----------------------------------------------------------


async def add_story_revision(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    content_json: str,
    source: str,
) -> int:
    """Insert a new revision and return its version. Retries once on the
    `(run_id, version)` UNIQUE collision; caller should hold the per-run
    asyncio.Lock to make collisions rare. Caller commits.
    """
    for _ in range(3):
        max_row = await session.execute(
            select(StoryRevision.version)
            .where(StoryRevision.run_id == run_id)
            .order_by(StoryRevision.version.desc())
            .limit(1)
        )
        current_max = max_row.scalar() or 0
        version = current_max + 1
        try:
            await session.execute(
                insert(StoryRevision).values(
                    run_id=run_id,
                    version=version,
                    content_json=content_json,
                    source=source,
                    user_oid=user_oid,
                    created_at=datetime.now(UTC),
                )
            )
            await session.flush()
            return version
        except IntegrityError:
            await session.rollback()
            continue
    raise RuntimeError("add_story_revision: exhausted retries on UNIQUE collision")


async def add_story_revision_if_absent(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    content_json: str,
    source: str,
    version: int = 1,
) -> int:
    """INSERT OR IGNORE — used by extraction so LangGraph replay doesn't dup
    revision 1. Returns the requested version regardless of insert result.
    Caller commits.
    """
    existing = await session.get(StoryRevision, (run_id, version))
    if existing is not None:
        return version
    try:
        session.add(StoryRevision(
            run_id=run_id,
            version=version,
            content_json=content_json,
            source=source,
            user_oid=user_oid,
            created_at=datetime.now(UTC),
        ))
        await session.flush()
    except IntegrityError:
        await session.rollback()
    return version


async def get_latest_revision(
    session: AsyncSession, *, run_id: str, user_oid: str
) -> StoryRevision | None:
    res = await session.execute(
        select(StoryRevision)
        .where(StoryRevision.run_id == run_id, StoryRevision.user_oid == user_oid)
        .order_by(StoryRevision.version.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_revision(
    session: AsyncSession, *, run_id: str, user_oid: str, version: int
) -> StoryRevision | None:
    row = await session.get(StoryRevision, (run_id, version))
    if row is None or row.user_oid != user_oid:
        return None
    return row


async def list_revisions(
    session: AsyncSession, *, run_id: str, user_oid: str
) -> list[StoryRevision]:
    res = await session.execute(
        select(StoryRevision)
        .where(StoryRevision.run_id == run_id, StoryRevision.user_oid == user_oid)
        .order_by(StoryRevision.version.asc())
    )
    return list(res.scalars().all())


# --- ChatTurn ---------------------------------------------------------------


async def append_chat_turn(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    role: str,
    content: str,
    revision_version: int | None = None,
    status: str = "done",
) -> ChatTurn:
    turn = ChatTurn(
        run_id=run_id,
        user_oid=user_oid,
        role=role,
        content=content,
        revision_version=revision_version,
        status=status,
        created_at=datetime.now(UTC),
    )
    session.add(turn)
    await session.flush()
    return turn


async def update_chat_turn(
    session: AsyncSession,
    *,
    turn_id: int,
    content: str | None = None,
    revision_version: int | None = None,
    status: str = "done",
    error_detail: str | None = None,
) -> None:
    row = await session.get(ChatTurn, turn_id)
    if row is None:
        return
    if content is not None:
        row.content = content
    if revision_version is not None:
        row.revision_version = revision_version
    row.status = status
    if error_detail is not None:
        row.error_detail = error_detail


async def list_chat_turns(
    session: AsyncSession,
    *,
    run_id: str,
    user_oid: str,
    limit: int = 200,
) -> list[ChatTurn]:
    res = await session.execute(
        select(ChatTurn)
        .where(ChatTurn.run_id == run_id, ChatTurn.user_oid == user_oid)
        .order_by(ChatTurn.id.asc())
        .limit(limit)
    )
    return list(res.scalars().all())


async def delete_chat_history(
    session: AsyncSession, *, run_id: str, user_oid: str
) -> int:
    res = await session.execute(
        delete(ChatTurn).where(
            ChatTurn.run_id == run_id,
            ChatTurn.user_oid == user_oid,
        )
    )
    return res.rowcount or 0


async def sweep_stale_streaming_turns(
    session: AsyncSession, *, older_than: datetime
) -> int:
    """Boot-time cleanup: any chat_turn with status='streaming' older than
    `older_than` is left over from a crashed process. Mark as error.
    """
    res = await session.execute(
        update(ChatTurn)
        .where(ChatTurn.status == "streaming", ChatTurn.created_at < older_than)
        .values(status="error", error_detail="crashed mid-stream")
    )
    return res.rowcount or 0
