"""Shared FastAPI dependency helpers for the API routers.

`get_session_factory` mirrors `runs_router.get_runner`: pulls the lifespan-
wired session factory off `app.state` and raises a clear 503 if it's
missing (rather than letting an `AttributeError` bubble up to the client).
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import async_sessionmaker


def get_session_factory(request: Request) -> async_sessionmaker:
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "DB session factory not initialized — FastAPI lifespan did not run. "
                "Boot via: uvicorn agentgenesis_api.main:create_app --factory"
            ),
        )
    return factory
