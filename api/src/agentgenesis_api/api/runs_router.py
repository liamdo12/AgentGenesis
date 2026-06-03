"""/runs HTTP endpoints — start, poll, list, resume, file-serve.

All endpoints require an authenticated user (`Depends(require_user)`).
Cross-user reads return 404, never 403, to avoid run-id existence disclosure
(per red-team Finding 9).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agentgenesis_api.auth import User, require_user
from agentgenesis_api.graph.runner import GraphRunner, RunStoreFull
from agentgenesis_api.schemas import Run

router = APIRouter()


def get_runner(request: Request) -> GraphRunner:
    """Pull the runner off app.state with a clear 503 if it's missing.

    `app.state.runner` is populated by the lifespan hook. A missing attribute
    means the lifespan didn't fire (mis-launched without --factory, lifespan
    errored silently, etc.) — surface that explicitly rather than the cryptic
    AttributeError that bites once per Postman session on Windows.
    """
    runner = getattr(request.app.state, "runner", None)
    if runner is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "runner not initialized — FastAPI lifespan did not run. "
                "Boot via: uvicorn agentgenesis_api.main:create_app --factory"
            ),
        )
    return runner


class StartRunBody(BaseModel):
    meeting_id: str


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    body: StartRunBody,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008 — FastAPI canonical
) -> dict[str, str]:
    runner = get_runner(request)
    try:
        run = await runner.submit(body.meeting_id, user)
    except RunStoreFull as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    return {"run_id": run.id}


@router.get("/runs/{run_id}", response_model=Run)
async def get_run(
    run_id: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> Run:
    runner = get_runner(request)
    run = await runner.get(run_id, user.oid)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs", response_model=list[Run])
async def list_runs(
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
    limit: int = 100,
) -> list[Run]:
    runner = get_runner(request)
    return await runner.list(user.oid, limit=limit)


@router.post("/runs/{run_id}/resume", response_model=Run)
async def resume_run(
    run_id: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
) -> Run:
    runner = get_runner(request)
    try:
        return await runner.resume(run_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="run not found") from e


@router.get("/runs/{run_id}/files/{rel_path:path}")
async def get_run_file(
    run_id: str,
    rel_path: str,
    request: Request,
    user: User = Depends(require_user),  # noqa: B008
):
    runner = get_runner(request)
    resolved = runner.safe_resolve(run_id, rel_path, user.oid)
    if resolved is None:
        # 404 (not 403) — never disclose whether a run id exists for another user.
        raise HTTPException(status_code=404, detail="not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(resolved)
