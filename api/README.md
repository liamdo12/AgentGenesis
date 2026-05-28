# Agent Genesis API

Extraction-stage backend: takes a Microsoft Teams meeting, pulls the transcript and recording via Microsoft Graph, samples representative frames with ffmpeg, then calls Claude (multimodal) to produce a meeting summary and draft user stories.

Implements:
- [`260528-0833-extraction-feature-langgraph-claude-teams-mcp`](../plans/260528-0833-extraction-feature-langgraph-claude-teams-mcp/) — phases 1–7 (the LangGraph pipeline).
- [`260528-1050-graph-fallback-and-entra-id-sso`](../plans/260528-1050-graph-fallback-and-entra-id-sso/) — Entra ID SSO + OBO + direct Graph client + IDOR scoping.

HITL review, Epic/Feature/Task hierarchy, and Azure DevOps writes are still out of scope here.

## Prerequisites

- Python **3.13** (`brew install python@3.13` on macOS).
- [`uv`](https://docs.astral.sh/uv/) (`brew install uv`).
- `ffmpeg` ≥ 6 on PATH (`brew install ffmpeg`).
- An **Anthropic API key** for Claude.
- A **Microsoft Entra ID app registration** — see [`docs/entra-id-setup.md`](../docs/entra-id-setup.md). 15-minute walkthrough.

## Setup

```bash
cd api
uv sync
cp .env.example .env
# Fill in AG_ENTRA_*, AG_ANTHROPIC_API_KEY (see docs/entra-id-setup.md).
```

## Run

```bash
uv run uvicorn agentgenesis_api.main:create_app --factory --port 8000 --reload
```

`--factory` is mandatory — the app instance is constructed by `create_app()` so Settings validation runs at app-startup time, not at module-import time.

## Authentication

Every endpoint except `/healthz` requires a **Bearer JWT** from Microsoft Entra ID (v2 access token, `aud` = client_id GUID, scope `api://agentgenesis-api/access_as_user`). The backend then mints a per-user Graph token via the **On-Behalf-Of (OBO)** flow for every Graph call. Run authorship is tracked via `Run.user_oid`; cross-user reads return 404 (never 403, to avoid run-id disclosure).

For local dev without a real tenant, set `AG_USE_STUB_NODES=1` (refused in `AG_ENVIRONMENT=prod`). The frontend pairs this with `?fakeAuth=1` which sends `Authorization: Bearer stub-token`.

```bash
# Sample request with a real token from MSAL.js
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/meetings
```

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness check (no auth). |
| `GET` | `/meetings?limit=N` | List the caller's Teams meeting recordings (cached 60s per `(oid, limit)`). |
| `POST` | `/runs` | Body `{ "meeting_id": "..." }` → `202 { "run_id": "..." }`. |
| `GET` | `/runs/{id}` | Poll caller's run; cross-user → 404. |
| `GET` | `/runs?limit=N` | List caller's recent runs only. |
| `POST` | `/runs/{id}/resume` | Resume a paused run (caller must own it). |
| `GET` | `/runs/{id}/files/{path}` | Serve a file from the run's output dir (path-traversal blocked, user-scoped). |

## Outputs

Each run writes to `data/runs/{run_id}/`:

```
source/recording.mp4
transcript.json          # parsed VTT segments + warnings
frames/{cidx:04d}/frame_*.jpg
manifest.json            # frame index with timestamps
summary.json             # MeetingSummary
stories.json             # StoriesOutput — IDs AG-1001+
```

## Status flow

```
pending → fetching_transcript → fetching_recording
        → extracting_frames → synthesizing → done
                ↘
                  pending_transcript   (Teams hasn't produced VTT; POST /runs/{id}/resume to retry)
                ↘
                  failed               (terminal; error field populated)
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Boot raises `ffmpeg not found on PATH` | ffmpeg missing | `brew install ffmpeg` (or set `AG_USE_STUB_NODES=1` for stub-only dev). |
| Boot raises `Entra ID config required when use_stub_nodes is false` | Missing `AG_ENTRA_*` env | Fill them per `docs/entra-id-setup.md`. |
| Boot raises `use_stub_nodes=True is refused when environment='prod'` | Stub auth enabled in prod | Remove `AG_USE_STUB_NODES=1` or set `AG_ENVIRONMENT=dev`. |
| `401 unauthorized` on every request | JWT audience/issuer mismatch | Check `accessTokenAcceptedVersion: 2` in the Entra app manifest. |
| `401 consent_required` with `claims` field | First-use Graph-scope consent gap | Frontend handles via `acquireTokenPopup({ claims })`. Admin can pre-grant by visiting the consent URL in the setup doc. |
| Run ends `pending_transcript` | Teams still processing | Wait, then `POST /runs/{id}/resume`. |
| Anthropic `401` | Bad key | Check `AG_ANTHROPIC_API_KEY`. |
| Recording 403 | User attended but didn't organize | Known v1 limitation — delegated `OnlineMeetingRecording.Read.All` is organizer-only. |
| Run ends `failed` with "All ffmpeg chunks failed" | Audio-only / codec issue | Check the recording's video stream. |
| Long meeting → slow synthesis | Map-reduce path engaged | Expected. Watch logs for `claude_summary.map_reduce`. |

## Tests

```bash
uv run pytest
uv run ruff check .
```

83+ tests, no network access required (Entra discovery + JWKS + OBO + Graph + Claude all stubbed; real ffmpeg runs on a bundled 14 KB fixture mp4).

## Production note — Postgres checkpointer

LangGraph state is persisted via `AsyncSqliteSaver` for dev. For production:

```python
# api/src/agentgenesis_api/graph/checkpointer.py
# Dev (current):
return AsyncSqliteSaver.from_conn_string(str(settings.data_dir / "checkpoints.sqlite"))
# Prod (uncomment + add settings.postgres_dsn + install langgraph-checkpoint-postgres):
# from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# return AsyncPostgresSaver.from_conn_string(settings.postgres_dsn)
```

Runs in flight at swap time will not resume — they need a fresh `POST /runs` against the new store.

## Cleanup

```bash
rm -rf api/data/runs/*               # remove all run artifacts
rm api/data/checkpoints.sqlite       # also reset graph state
```

## Layout

```
src/agentgenesis_api/
├── main.py                  # FastAPI app factory + lifespan
├── config.py                # AG_* Settings via pydantic-settings (incl. Entra)
├── logging.py               # structlog wiring
├── auth/                    # Entra JWT validation + OBO TokenBroker + User
├── schemas/                 # Pydantic Story/Summary/Run/Segment
├── mcp/                     # GraphClient (replaced TeamsMCPClient) + shared exceptions/models
├── synthesis/               # ClaudeClient + prompts + token counter + map_reduce
├── graph/
│   ├── auth_context.py      # current_user ContextVar (per-task)
│   ├── builder.py           # StateGraph topology
│   ├── checkpointer.py      # AsyncSqliteSaver factory
│   ├── runner.py            # GraphRunner — submit(meeting_id, user) / resume(run_id, user)
│   ├── state.py             # GraphState TypedDict + reducers
│   ├── deps.py              # NodeDeps DI container
│   └── nodes/               # Real node modules + _stubs.py
└── api/                     # FastAPI routers (meetings, runs)
```
