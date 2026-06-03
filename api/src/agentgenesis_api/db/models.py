"""Declarative tables for runs, approvals, story revisions, and chat turns.

All four tables key on `user_oid` so the existing IDOR rules extend to the DB
layer cleanly: a row "exists" only for the owning user.

`RunRow` is the persisted projection of `schemas.Run`; the in-memory `Run`
pydantic model remains the request/response shape but is hydrated from this
table on startup so approvals and chat survive restarts.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "run"

    id: Mapped[str] = mapped_column(primary_key=True)
    meeting_id: Mapped[str] = mapped_column(index=True)
    user_oid: Mapped[str] = mapped_column(index=True)
    status: Mapped[str]
    progress: Mapped[float] = mapped_column(default=0.0)
    error: Mapped[str | None] = mapped_column(default=None)
    output_dir: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class Approval(Base):
    __tablename__ = "approval"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    story_id: Mapped[str] = mapped_column(primary_key=True)
    user_oid: Mapped[str] = mapped_column(index=True)
    approved: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow)


class StoryRevision(Base):
    __tablename__ = "story_revision"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    content_json: Mapped[str]
    source: Mapped[str]  # "extraction" | "chat"
    user_oid: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    __table_args__ = (
        UniqueConstraint("run_id", "version", name="uq_story_revision_run_version"),
    )


class ChatTurn(Base):
    __tablename__ = "chat_turn"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(index=True)
    user_oid: Mapped[str] = mapped_column(index=True)
    role: Mapped[str]                                     # "user" | "assistant"
    content: Mapped[str]
    revision_version: Mapped[int | None] = mapped_column(default=None)
    # Lifecycle: "streaming" → "done" | "error". Boot-time sweep marks stale
    # streaming rows as "error" after SIGKILL recovery.
    status: Mapped[str] = mapped_column(default="done")
    error_detail: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
