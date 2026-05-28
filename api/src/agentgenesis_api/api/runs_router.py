"""/runs HTTP endpoints — start, poll, list, resume, and file-serve outputs."""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agentgenesis_api.graph.runner import RunStoreFull
from agentgenesis_api.schemas import Run

router = APIRouter()


class StartRunBody(BaseModel):
    meeting_id: str


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(body: StartRunBody, request: Request) -> dict[str, str]:
    runner = request.app.state.runner
    try:
        run = await runner.submit(body.meeting_id)
    except RunStoreFull as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    return {"run_id": run.id}


@router.get("/runs/{run_id}", response_model=Run)
async def get_run(run_id: str, request: Request) -> Run:
    runner = request.app.state.runner
    run = await runner.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs", response_model=list[Run])
async def list_runs(request: Request, limit: int = 100) -> list[Run]:
    runner = request.app.state.runner
    return await runner.list(limit=limit)


@router.post("/runs/{run_id}/resume", response_model=Run)
async def resume_run(run_id: str, request: Request) -> Run:
    runner = request.app.state.runner
    try:
        return await runner.resume(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="run not found") from e


@router.get("/runs/{run_id}/files/{rel_path:path}")
async def get_run_file(run_id: str, rel_path: str, request: Request):
    runner = request.app.state.runner
    resolved = runner.safe_resolve(run_id, rel_path)
    if resolved is None:
        # 403 covers both "not under output_dir" and "run not found" — don't
        # leak whether a given run exists.
        raise HTTPException(status_code=403, detail="forbidden")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(resolved)
