"""GET /meetings — UI helper for the meeting picker.

Caches results in-memory for 60s so a tab refresh doesn't re-hit Graph.
Phase 5 swaps the cache key to `(user.oid, limit)` once `require_user` is
applied; for now the cache uses STUB_USER's identity since auth is not yet
enforced at this endpoint.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from agentgenesis_api.auth import User, require_user
from agentgenesis_api.sources import MeetingRef, SourceCallError, SourceTransportError

router = APIRouter()

_CACHE_TTL_SEC = 60.0
_cache: dict[tuple[str, int], tuple[float, list[MeetingRef]]] = {}


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
    try:
        refs = await request.app.state.graph.list_meeting_recordings(user, limit=limit)
    except SourceTransportError as e:
        raise HTTPException(status_code=503, detail=f"Graph unreachable: {e}") from e
    except SourceCallError as e:
        # Map by HTTP status (Finding 8): 5xx/408/429 → 502; 4xx → surface as-is.
        upstream = e.status or 502
        if 500 <= upstream < 600 or upstream in (408, 429):
            raise HTTPException(status_code=502, detail=str(e)) from e
        raise HTTPException(status_code=upstream, detail=str(e)) from e
    _cache[cache_key] = (time.monotonic(), refs)
    return refs
