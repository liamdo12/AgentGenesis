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
from agentgenesis_api.services import RealServices, StubServices


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(settings.log_format)
    log = get_logger("agentgenesis_api.main")
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

    if settings.use_stub_nodes:
        services = StubServices.create(
            settings,
            stub_video_path=settings.data_dir / "stub" / "sample.mp4",
            stub_vtt_path=settings.data_dir / "stub" / "sample.vtt",
        )
        app.state.graph_client = None
        app.state.claude = None
    else:
        graph = GraphClient(settings, app.state.token_broker)
        from agentgenesis_api.synthesis import ClaudeClient
        claude = ClaudeClient(settings)
        services = RealServices.create(
            settings, graph=graph, broker=app.state.token_broker, claude=claude,
        )
        # Held only so we can aclose() on shutdown; routers consume app.state.services.
        app.state.graph_client = graph
        app.state.claude = claude

    app.state.services = services
    deps = NodeDeps(settings=settings, services=services)
    app.state.runner = GraphRunner(settings, deps=deps)
    await app.state.runner.startup()
    try:
        yield
    finally:
        await app.state.runner.shutdown()
        claude_obj = getattr(app.state, "claude", None)
        if claude_obj is not None:
            await claude_obj.aclose()
        await app.state.token_broker.aclose()
        graph_obj = getattr(app.state, "graph_client", None)
        if graph_obj is not None:
            await graph_obj.aclose()
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
