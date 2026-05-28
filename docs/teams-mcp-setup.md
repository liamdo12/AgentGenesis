# Teams MCP server — operator setup

The Agent Genesis extraction backend talks to Microsoft Teams via a separate
**MCP (Model Context Protocol) server**. This doc explains which server to
install, what credentials it needs, and how to wire it into the `api/` backend.

The backend itself does **not** call Microsoft Graph directly. All Graph
interaction is owned by the MCP server. That keeps Graph permission scopes,
auth refresh, and tenant config in one place.

## Server selection (spike result)

**Picked:** [`inditextech/mcp-teams-server`](https://github.com/inditextech/mcp-teams-server) — community Python MCP server that wraps Microsoft Graph as MCP tools.

**Why:**

- Python, pip-installable — no extra runtime to manage.
- Supports the three tools we need: list recordings, fetch transcript, fetch recording URL.
- App-only (client credentials) auth — no per-user OAuth dance.
- Recent enough commit activity to trust at install time.

**Rejected alternatives (snapshot at install time — re-verify if running this doc later):**

- `microsoft/teams-mcp` — preferred if Microsoft ships an official one, but not available at the time of the spike. Switch when published; the wrapper interface is the same.
- Custom MCP server wrapping Graph ourselves — too much scope for v1; revisit only if `inditextech` proves unworkable.

If the picked server's tool names differ from the defaults, override them in `.env`:

```
AG_MCP_TOOL_LIST_RECORDINGS=list_meeting_recordings
AG_MCP_TOOL_GET_TRANSCRIPT=get_meeting_transcript
AG_MCP_TOOL_GET_RECORDING=get_meeting_recording
```

The wrapper depends only on the tool *surface* (name + JSON I/O shape), so swapping servers is a config change.

## Microsoft Graph prerequisites

The MCP server needs an **Entra ID (Azure AD) app registration** with:

- App-only (client credentials) authentication enabled.
- Application permission: `OnlineMeetingRecording.Read.All` (admin consent required).
- A client secret you can copy into the MCP server's env.

Tenant admin must grant consent for the application permission. This is a one-time step per tenant.

## Install + run

```bash
# Pick an isolated venv for the MCP server — separate from the api/ venv.
python -m venv ~/.venvs/teams-mcp
source ~/.venvs/teams-mcp/bin/activate
pip install mcp-teams-server

# Configure (per the server's own README — these env vars belong to it, not to api/):
export AZURE_TENANT_ID=<tenant-uuid>
export AZURE_CLIENT_ID=<app-uuid>
export AZURE_CLIENT_SECRET=<secret>

# Run on a port the api/ backend can reach.
mcp-teams-server --transport streamable_http --port 3000
```

Verify it's up:

```bash
curl http://localhost:3000/mcp/health   # or whatever the server exposes
```

## Wire it into the api/ backend

In `api/.env`:

```
AG_TEAMS_MCP_URL=http://localhost:3000/mcp
# AG_TEAMS_MCP_AUTH_TOKEN=<optional bearer>
```

Boot the backend and hit the smoke endpoint:

```bash
cd api && uv run uvicorn agentgenesis_api.main:create_app --factory --port 8000
curl http://localhost:8000/mcp/healthz
```

Expected response:

```json
{ "status": "ok",
  "tools": ["list_meeting_recordings", "get_meeting_transcript", "get_meeting_recording"],
  "count": 3 }
```

If you see `503 MCP unreachable`, check the MCP server is running and the URL is correct.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `503 MCP unreachable` from `/mcp/healthz` | MCP server not running or wrong URL | Restart server; check `AG_TEAMS_MCP_URL`. |
| Tool list returns names different from the defaults | Server uses different naming | Set `AG_MCP_TOOL_*` env vars to match (see "Server selection" above). |
| `MCP tool 'get_meeting_transcript' failed: ... not ready` | Teams hasn't finished processing the recording's transcript | Expected. The pipeline maps this to `RunStatus.PENDING_TRANSCRIPT`; resume the run later via `POST /runs/{id}/resume`. |
| `401` or `403` from MCP tools | Tenant admin consent missing for `OnlineMeetingRecording.Read.All` | Have admin grant consent in the Entra portal. |

## Tested integration boundary

Phase 2's wrapper has been verified by stubbed tests (`api/tests/test_teams_client.py`) covering:

- Tool list reporting.
- Recording-list normalization (both raw-array and wrapped-object response shapes).
- Transcript happy path (raw VTT text response).
- Transcript-not-ready → `TranscriptNotReady` exception.
- Generic tool errors → `MCPToolError`.
- `McpError` from the SDK → `MCPToolError`.
- Transport failures → `MCPTransportError` and connection drop.

**Not yet tested live** against a running Teams MCP server. The first integration smoke test (operator step) is `curl /mcp/healthz` returning the live tool list.
