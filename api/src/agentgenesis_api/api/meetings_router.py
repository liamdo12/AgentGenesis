"""GET /meetings — UI helper for the meeting picker.

Caches results in-memory for 60s per (user.oid, limit) so a tab refresh
doesn't re-hit the upstream source. The underlying source is selected by
the lifespan (Graph in real mode, canned fixture list in stub mode) and
reached via the `PipelineServices.meetings` protocol.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from agentgenesis_api.auth import User, require_user
from agentgenesis_api.msgraph import (
    MeetingRef,
    MsGraphCallError,
    MsGraphTransportError,
)
from agentgenesis_api.services import PipelineServices

router = APIRouter()

_CACHE_TTL_SEC = 60.0
_cache: dict[tuple[str, int], tuple[float, list[MeetingRef]]] = {}


def _get_services(request: Request) -> PipelineServices:
    """Pull PipelineServices off app.state with a clean 503 if lifespan didn't fire."""
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Services not initialized — FastAPI lifespan did not run. "
                "Boot via: uvicorn agentgenesis_api.main:create_app --factory"
            ),
        )
    return services


@router.get("/meetings", response_model=list[MeetingRef])
async def list_meetings(
    request: Request,
    user: User = Depends(require_user),  # noqa: B008 — FastAPI canonical
    limit: int = 50,
) -> list[MeetingRef]:
    cache_key = (user.oid, limit)
    hit = _cache.get(cache_key)
    if hit is not None and (time.monotonic() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]
    services = _get_services(request)
    try:
        refs = await services.meetings.list_meetings(user, limit=limit)
    except MsGraphTransportError as e:
        raise HTTPException(status_code=503, detail=f"Graph unreachable: {e}") from e
    except MsGraphCallError as e:
        # Map by HTTP status: 5xx/408/429 → 502; 4xx → surface as-is.
        upstream = e.status or 502
        if 500 <= upstream < 600 or upstream in (408, 429):
            raise HTTPException(status_code=502, detail=str(e)) from e
        raise HTTPException(status_code=upstream, detail=str(e)) from e
    _cache[cache_key] = (time.monotonic(), refs)
    return refs
