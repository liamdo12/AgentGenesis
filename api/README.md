# Agent Genesis API

Extraction-stage backend: takes a Microsoft Teams meeting ID, pulls the transcript and recording via MCP, samples representative frames with ffmpeg, then calls Claude (multimodal) to produce a meeting summary and draft user stories.

Implements phases 1–6 of [`plans/260528-0833-extraction-feature-langgraph-claude-teams-mcp/`](../plans/260528-0833-extraction-feature-langgraph-claude-teams-mcp/). HITL review, Epic/Feature/Task hierarchy, and Azure DevOps writes are out of scope here.

## Prerequisites

- Python **3.13** (`brew install python@3.13` on macOS).
- [`uv`](https://docs.astral.sh/uv/) (`brew install uv`).
- `ffmpeg` ≥ 6 on PATH (`brew install ffmpeg`).
- A running **Teams MCP server**. See [`docs/teams-mcp-setup.md`](../docs/teams-mcp-setup.md).
- An Anthropic API key.

## Setup

```bash
cd api
uv sync
cp .env.example .env
# Fill in AG_TEAMS_MCP_URL and AG_ANTHROPIC_API_KEY in .env.
```

## Run

```bash
uv run uvicorn agentgenesis_api.main:create_app --factory --port 8000 --reload
```

`--factory` is mandatory — the app instance is constructed by `create_app()` so Settings validation runs at app-startup time, not at module-import time.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness check. |
| `GET` | `/mcp/healthz` | Smoke-test MCP connectivity; returns the live tool list. |
| `GET` | `/meetings?limit=N` | List Teams meeting recordings (cached 60s). |
| `POST` | `/runs` | Body `{ "meeting_id": "..." }` → `202 { "run_id": "..." }`. |
| `GET` | `/runs/{id}` | Poll status, progress, error, output paths. |
| `GET` | `/runs?limit=N` | List recent runs. |
| `POST` | `/runs/{id}/resume` | Resume a run paused at `pending_transcript`. |
| `GET` | `/runs/{id}/files/{path}` | Serve a file from the run's output dir (path-traversal blocked). |

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

`stories.json` is the artifact the future HITL review plan will consume.

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
| `/mcp/healthz` → 503 | MCP server unreachable | Check `AG_TEAMS_MCP_URL`; verify the MCP server is running. |
| Run ends `pending_transcript` | Teams still processing | Wait, then `POST /runs/{id}/resume`. |
| Anthropic `401` | Bad key | Check `AG_ANTHROPIC_API_KEY`. |
| Run ends `failed` with "All ffmpeg chunks failed" | Recording is audio-only or codec issue | Check the recording's video stream. |
| Long meeting → slow synthesis | Map-reduce path engaged | Expected. Watch logs for `claude_summary.map_reduce`. |

## Tests

```bash
uv run pytest
uv run ruff check .
```

55 tests, no network access required (MCP and Claude both stubbed at the wrapper boundary; real ffmpeg runs on the bundled 14 KB fixture mp4).

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
├── config.py                # AG_* Settings via pydantic-settings
├── logging.py               # structlog wiring
├── schemas/                 # Pydantic Story/Summary/Run/Segment
├── mcp/                     # TeamsMCPClient + exceptions + models
├── synthesis/               # ClaudeClient + prompts + token counter + map_reduce
├── graph/
│   ├── builder.py           # StateGraph topology
│   ├── checkpointer.py      # AsyncSqliteSaver factory
│   ├── runner.py            # GraphRunner — submit / resume / track
│   ├── state.py             # GraphState TypedDict + reducers
│   ├── deps.py              # NodeDeps DI container
│   └── nodes/               # Real node modules + _stubs.py
└── api/                     # FastAPI routers (mcp, meetings, runs)
```
