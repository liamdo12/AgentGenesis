"""GET /meetings — UI helper for the meeting picker.

Caches results in-memory for 60s so a tab refresh doesn't re-hit MCP.
"""

import time

from fastapi import APIRouter, HTTPException, Request

from agentgenesis_api.mcp import MCPToolError, MCPTransportError, MeetingRef

router = APIRouter()

_CACHE_TTL_SEC = 60.0
_cache: dict[str, tuple[float, list[MeetingRef]]] = {}


@router.get("/meetings", response_model=list[MeetingRef])
async def list_meetings(request: Request, limit: int = 50) -> list[MeetingRef]:
    cache_key = f"limit={limit}"
    hit = _cache.get(cache_key)
    if hit is not None and (time.monotonic() - hit[0]) < _CACHE_TTL_SEC:
        return hit[1]
    try:
        refs = await request.app.state.mcp.list_meeting_recordings(limit=limit)
    except MCPTransportError as e:
        raise HTTPException(status_code=503, detail=f"MCP unreachable: {e}") from e
    except MCPToolError as e:
        raise HTTPException(status_code=502, detail=f"MCP tool error: {e}") from e
    _cache[cache_key] = (time.monotonic(), refs)
    return refs
