"""LangGraph checkpointer factory.

Ships SQLite (`AsyncSqliteSaver`) for dev. Postgres path is documented in
api/README.md; the swap is a one-line change here when prod target is known.
"""

from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agentgenesis_api.config import Settings


def build_checkpointer(settings: Settings) -> AbstractAsyncContextManager[AsyncSqliteSaver]:
    """Returns an async context manager that yields the configured checkpointer.

    Callers must use `async with`. SQLite for dev; for prod, swap to
    PostgresSaver.from_conn_string(settings.postgres_dsn).
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db_path = settings.data_dir / "checkpoints.sqlite"
    return AsyncSqliteSaver.from_conn_string(str(db_path))
