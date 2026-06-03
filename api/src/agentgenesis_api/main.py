"""FastAPI app factory.

Routers from later phases plug into `create_app` via the local
`_register_routers` hook so this file doesn't grow per phase.
"""

import os
import shutil
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from agentgenesis_api.api.approvals_router import router as approvals_router
from agentgenesis_api.api.chat_router import router as chat_router
from agentgenesis_api.api.meetings_router import router as meetings_router
from agentgenesis_api.api.runs_router import router as runs_router
from agentgenesis_api.auth import TokenBroker
from agentgenesis_api.auth.dependency import build_jwks_client
from agentgenesis_api.config import Settings
from agentgenesis_api.db import repository
from agentgenesis_api.db.engine import build_engine, create_all_if_dev
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.runner import GraphRunner
from agentgenesis_api.logging import configure_logging, get_logger
from agentgenesis_api.msgraph import GraphClient
from agentgenesis_api.services import RealServices, StubServices


def _check_single_worker() -> None:
    """Refuse to boot under uvicorn `--workers > 1`.

    Phase 1 + Phase 3 use in-process locks (per-run asyncio.Lock + file-lock
    around create_all). Multi-worker would race the locks silently and
    corrupt revision state. Re-enable when DB-backed advisory locks land.
    """
    raw = os.environ.get("WEB_CONCURRENCY")
    if raw is None:
        return
    try:
        workers = int(raw)
    except ValueError:
        return
    if workers > 1:
        raise RuntimeError(
            "This service requires single-worker uvicorn (--workers 1). "
            "Multi-worker requires DB-backed advisory locks (out of scope for v1)."
        )


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(settings.log_format)
    log = get_logger("agentgenesis_api.main")
    _check_single_worker()
    log.info("startup", data_dir=str(settings.data_dir), claude_model=settings.claude_model)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        if settings.use_stub_nodes:
            # Stub contributors may not have ffmpeg installed; StubServices.frames
            # falls back to a canned manifest in that case.
            log.warning(
                "ffmpeg.missing",
                detail="ffmpeg not on PATH; frames will fall back to a canned manifest.",
            )
        else:
            raise RuntimeError("ffmpeg not found on PATH; required for frame extraction.")
    # PyJWKClient — only built when we're validating real tokens.
    app.state.jwks_client = None if settings.use_stub_nodes else build_jwks_client(settings)
    app.state.token_broker = TokenBroker(settings)

    # DB engine + session factory. Created BEFORE services so they can
    # consume the factory and drive `commit_revision` etc.
    app.state.db_engine = build_engine(settings.database_url)
    await create_all_if_dev(app.state.db_engine, settings)
    app.state.db_session_factory = async_sessionmaker(
        app.state.db_engine, expire_on_commit=False
    )

    if settings.use_stub_nodes:
        services = StubServices.create(
            settings,
            stub_video_path=settings.data_dir / "stub" / "sample.mp4",
            stub_vtt_path=settings.data_dir / "stub" / "sample.vtt",
            db_session_factory=app.state.db_session_factory,
        )
        app.state.graph_client = None
        app.state.claude = None
    else:
        graph = GraphClient(settings, app.state.token_broker)
        from agentgenesis_api.synthesis import ClaudeClient
        claude = ClaudeClient(settings)
        services = RealServices.create(
            settings,
            graph=graph,
            broker=app.state.token_broker,
            claude=claude,
            db_session_factory=app.state.db_session_factory,
        )
        # Held only so we can aclose() on shutdown; routers consume app.state.services.
        app.state.graph_client = graph
        app.state.claude = claude

    app.state.services = services
    deps = NodeDeps(settings=settings, services=services)
    app.state.runner = GraphRunner(settings, deps=deps)
    app.state.runner.attach_db(app.state.db_session_factory)
    await app.state.runner.startup()
    await app.state.runner.hydrate_from_db()
    # Boot-time sweep: chat turns left in "streaming" >5min are from a
    # crashed prior process — mark them as errored.
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    async with app.state.db_session_factory() as session:
        n = await repository.sweep_stale_streaming_turns(session, older_than=cutoff)
        await session.commit()
        if n:
            log.info("startup.sweep_stale_streaming", marked_error=n)
    try:
        yield
    finally:
        # Drain in-flight chat streams before disposing the engine so
        # background-task persistence doesn't race shutdown.
        await app.state.runner.drain_chat_streams(timeout_sec=30.0)
        await app.state.runner.shutdown()
        claude_obj = getattr(app.state, "claude", None)
        if claude_obj is not None:
            await claude_obj.aclose()
        await app.state.token_broker.aclose()
        graph_obj = getattr(app.state, "graph_client", None)
        if graph_obj is not None:
            await graph_obj.aclose()
        await app.state.db_engine.dispose()
        log.info("shutdown")


def _register_routers(app: FastAPI) -> None:
    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(meetings_router)
    app.include_router(runs_router)
    app.include_router(approvals_router)
    app.include_router(chat_router)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    app = FastAPI(title="Agent Genesis API", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings
    _register_routers(app)
    return app


# uvicorn is invoked with `--factory` so this module never instantiates
# Settings at import time. Boot via:
# `uv run uvicorn agentgenesis_api.main:create_app --factory`.
