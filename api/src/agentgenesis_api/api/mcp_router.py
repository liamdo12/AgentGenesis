"""MCP smoke-test endpoint.

`GET /mcp/healthz` connects to the configured Teams MCP server and reports the
list of tools it exposes. Useful as a deploy-time sanity check and as live
documentation of the MCP surface.
"""

from fastapi import APIRouter, HTTPException, Request

from agentgenesis_api.mcp.exceptions import MCPToolError, MCPTransportError

router = APIRouter()


@router.get("/mcp/healthz")
async def mcp_healthz(request: Request) -> dict[str, object]:
    client = request.app.state.mcp
    try:
        tools = await client.list_tools()
    except MCPTransportError as e:
        raise HTTPException(status_code=503, detail=f"MCP unreachable: {e}") from e
    except MCPToolError as e:
        raise HTTPException(status_code=502, detail=f"MCP tool error: {e}") from e
    return {"status": "ok", "tools": tools, "count": len(tools)}
