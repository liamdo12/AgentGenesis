"""FastAPI app factory.

Routers from later phases plug into `create_app` via the local
`_register_routers` hook so this file doesn't grow per phase.
"""

import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentgenesis_api.api.meetings_router import router as meetings_router
from agentgenesis_api.api.runs_router import router as runs_router
from agentgenesis_api.auth import TokenBroker
from agentgenesis_api.auth.dependency import build_jwks_client
from agentgenesis_api.config import Settings
from agentgenesis_api.graph.deps import NodeDeps
from agentgenesis_api.graph.runner import GraphRunner
from agentgenesis_api.logging import configure_logging, get_logger
from agentgenesis_api.msgraph import GraphClient


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(settings.log_format)
    log = get_logger("agentgenesis_api.main")
    log.info("startup", data_dir=str(settings.data_dir), claude_model=settings.claude_model)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        if settings.use_stub_nodes:
            # Stub-mode contributors may not have ffmpeg installed; the
            # extract_frames stub-fallback handles the missing-binary path.
            log.warning(
                "ffmpeg.missing",
                detail="ffmpeg not on PATH; extract_frames will fall back to a canned manifest.",
            )
        else:
            raise RuntimeError("ffmpeg not found on PATH; required for frame extraction.")
    # PyJWKClient — only built when we're actually validating real tokens.
    # Stub mode skips this entirely; require_user returns STUB_USER without
    # ever touching the JWKS endpoint.
    app.state.jwks_client = None if settings.use_stub_nodes else build_jwks_client(settings)
    app.state.token_broker = TokenBroker(settings)
    if settings.use_stub_nodes:
        # Stub mode: skip the real Graph / Claude clients entirely.
        app.state.graph = None
        app.state.claude = None
        app.state.runner = GraphRunner(settings, graph=None, broker=None, claude=None)
        app.state.runner._stub_deps = NodeDeps(
            settings=settings,
            graph=None,
            broker=None,
            claude=None,
            stub_mode=True,
            stub_video_path=settings.data_dir / "stub" / "sample.mp4",
            stub_vtt_path=settings.data_dir / "stub" / "sample.vtt",
        )
    else:
        # GraphClient replaces the deleted TeamsMCPClient. Per Phase 4 / Finding 15.
        app.state.graph = GraphClient(settings, app.state.token_broker)
        from agentgenesis_api.synthesis import ClaudeClient
        app.state.claude = ClaudeClient(settings)
        app.state.runner = GraphRunner(
            settings,
            graph=app.state.graph,
            broker=app.state.token_broker,
            claude=app.state.claude,
        )
    await app.state.runner.startup()
    try:
        yield
    finally:
        await app.state.runner.shutdown()
        if app.state.claude is not None:
            await app.state.claude.aclose()
        await app.state.token_broker.aclose()
        if app.state.graph is not None:
            await app.state.graph.aclose()
        log.info("shutdown")


def _register_routers(app: FastAPI) -> None:
    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(meetings_router)
    app.include_router(runs_router)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    app = FastAPI(title="Agent Genesis API", version="0.1.0", lifespan=_lifespan)
    app.state.settings = settings
    _register_routers(app)
    return app


# uvicorn is invoked with `--factory` so this module never instantiates
# Settings at import time. Boot via:
# `uv run uvicorn agentgenesis_api.main:create_app --factory`.
