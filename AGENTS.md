# AGENTS.md — AgentGenesis

> Read this first. Single source of truth for project layout, conventions, and
> invariants for any AI agent (Cursor, Claude Code, etc.) working in this repo.

---

## 1. What this project does

AgentGenesis turns Microsoft Teams meeting recordings into structured user
stories. A user signs in via Entra ID, picks a meeting from their Teams
recordings list, and the backend pulls the transcript + recording from
Microsoft Graph, samples frames with ffmpeg, calls Claude (multimodal) to
produce a `MeetingSummary` + a `StoriesOutput` (list of user stories), and
serves the result back. Users can then **chat-edit** the stories
conversationally (SSE streaming Claude) — every edit becomes a versioned
revision in the DB.

Status: pre-production. Single-worker only.

---

## 2. Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.13, FastAPI, LangGraph 1.x, SQLAlchemy 2.x async + aiosqlite, Anthropic SDK, ffmpeg, structlog, uv |
| Frontend | React 18, Vite 5, TypeScript 5, MSAL.js v5 + react-router-dom v6 |
| Design system | React components + tokens (separate package, aliased `@ds/*`) |
| Auth | Microsoft Entra ID — SPA flow (MSAL) → JWT to backend → OBO exchange → Microsoft Graph delegated calls |
| AI | Claude Sonnet 4.6 (configurable via `AG_CLAUDE_MODEL`) |
| Persistence | SQLite (dev) / SQL Server (prod, manual DDL) via SQLAlchemy. LangGraph checkpoint = separate `data/checkpoints.sqlite`. |

---

## 3. Repo layout (monorepo)

```
AgentGenesis/
├── api/                 # FastAPI + LangGraph backend (Python, uv)
│   ├── src/agentgenesis_api/
│   │   ├── main.py              # create_app() + lifespan
│   │   ├── config.py            # AG_* pydantic-settings
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── runs_router.py
│   │   │   ├── meetings_router.py
│   │   │   ├── approvals_router.py
│   │   │   ├── chat_router.py   # SSE chat-edit endpoint
│   │   │   └── dependencies.py  # get_session_factory helper
│   │   ├── auth/                # Entra JWT validation + OBO TokenBroker
│   │   ├── db/                  # SQLAlchemy models, engine, repository
│   │   ├── graph/               # LangGraph DAG
│   │   │   ├── builder.py       # topology (serialized — see §6)
│   │   │   ├── runner.py        # GraphRunner: submit / resume / hydrate
│   │   │   ├── state.py         # GraphState TypedDict + reducers
│   │   │   └── nodes/           # individual graph nodes
│   │   ├── services/            # provider seam (Real | Stub | Noop)
│   │   │   ├── protocols.py     # PipelineServices facade
│   │   │   ├── real.py          # → Graph + Claude
│   │   │   ├── stub.py          # → fixtures + canned synth
│   │   │   ├── noop.py          # topology tests only
│   │   │   ├── chat.py          # CHAT_SYSTEM prompt + revise schema
│   │   │   └── revisions.py     # commit_revision (DB-first + atomic os.replace)
│   │   ├── msgraph/             # GraphClient + MS Graph types
│   │   ├── schemas/             # Pydantic: Run, Story, StoriesOutput, Summary, Segment
│   │   └── synthesis/           # ClaudeClient, prompts, frame selection
│   ├── tests/                   # pytest (132 tests as of writing)
│   ├── data/                    # dev artifacts (gitignored)
│   │   ├── agentgenesis.db          # SQLAlchemy DB
│   │   ├── checkpoints.sqlite       # LangGraph state
│   │   ├── stub/                    # fixture .mp4 + .vtt
│   │   └── runs/{run_id}/           # per-run artifacts (stories.json etc.)
│   ├── .env.example
│   └── pyproject.toml
├── app/                 # React frontend (Vite)
│   ├── src/
│   │   ├── main.tsx             # hardened MSAL boot + RouterProvider
│   │   ├── app-root.tsx
│   │   ├── router.tsx           # react-router-dom v6
│   │   ├── auth/                # MSAL config + apiFetch + AuthCallback
│   │   ├── hooks/               # useRunLifecycle, useApprovals, useChat, useMeetings
│   │   ├── lib/                 # story-types.ts, parse-sse.ts
│   │   ├── panels/              # stories-panel, ai-side-panel, meetings-list
│   │   ├── modals/              # edit-story, devops-push, bulk-delete-preview
│   │   ├── state/               # reducer + context
│   │   └── styles/
│   ├── .env.example
│   └── package.json
├── design-system/       # @ds/* — shared components + tokens
├── docs/                # markdown docs
│   ├── entra-id-setup.md        # Azure portal walk-through
│   ├── diagrams/
│   │   ├── architecture-overview.png        # READ THIS for full picture
│   │   ├── architecture-overview-hires.png
│   │   └── architecture-overview.excalidraw # editable source
│   └── journals/                # one-off retrospectives
├── plans/               # /ck:plan output (work-in-flight planning)
│   ├── 260603-1540-verify-entra-id-app-credentials/
│   ├── 260604-1027-wire-entra-callback-and-meetings-fetch/
│   └── …
├── .cursor/             # Cursor-specific agent config (committed)
│   ├── rules/
│   │   └── plan-workflow.mdc           # auto-attached for plans/**/*.md
│   └── commands/
│       ├── ck-plan.md                  # /ck-plan slash command
│       ├── ck-plan-red-team.md         # /ck-plan-red-team
│       ├── ck-plan-validate.md         # /ck-plan-validate
│       └── ck-cook.md                  # /ck-cook
└── .claude/             # Claude Code / ck CLI config (gitignored except rules)
```

**`.env` files are gitignored** — never commit secrets. `.env.example`
mirrors required keys.

---

## 4. How to build & run

### Backend

```bash
cd api
uv sync                                      # install deps (Python 3.13)
cp .env.example .env                         # fill in real creds OR use stub
uv run uvicorn agentgenesis_api.main:create_app --factory --port 8000
```

- `--factory` is **mandatory** — Settings validation must run at app-startup,
  not module-import time.
- Stub mode (no Entra/Claude credentials needed):
  ```bash
  AG_USE_STUB_NODES=1 AG_ANTHROPIC_API_KEY=stub uv run uvicorn ...
  ```
- Hot-reload: append `--reload`.

### Frontend

```bash
cd app
npm install
npm run dev                                  # Vite on http://localhost:5174
```

- Stub auth for design-QA: `http://localhost:5174?fakeAuth=1` (sends
  `Authorization: Bearer stub-token`).
- Production build: `npm run build` → `dist/`.

### Design system playground

```bash
cd design-system
npm install
npm run dev
```

---

## 5. Testing

### Backend

```bash
cd api
uv run pytest                                # 132 tests (current)
uv run pytest -k test_chat                   # filter
uv run ruff check src tests                  # MUST be clean before commit
```

### Frontend

```bash
cd app
npm run typecheck                            # MUST be clean before commit
npm run build                                # sanity check
```

No frontend unit tests yet (Vitest not configured).

### Smoke against running backend

```bash
curl -s http://localhost:8000/healthz                          # {"status":"ok"}
curl -s -H "Authorization: Bearer stub-token" http://localhost:8000/runs | jq
```

---

## 6. Architecture overview

**Read first**: `docs/diagrams/architecture-overview.png` — 7-zone diagram
covering frontend, FastAPI, LangGraph DAG, services facade, persistence,
external services, SSE chat loop. Editable source at
`docs/diagrams/architecture-overview.excalidraw`.

### Extraction pipeline (LangGraph DAG — serialized)

```
START
  → fetch_meeting_ref       (MS Graph: resolve meeting metadata)
  → fetch_transcript        (MS Graph: VTT → segments; may pause as pending_transcript)
  → fetch_recording         (MS Graph: download .mp4 to data/runs/{id}/source/)
  → extract_frames          (ffmpeg: chunk + sample frames)
  → merge_context           (build MultimodalContext from above)
  → claude_summary          (Claude: → summary.json)
  → claude_draft_stories    (Claude: → stories.json + DB revision 1)
  → END
```

**Why serialized, not parallel**: LangGraph 1.x BSP scheduler fires
`merge_context` after only one inbound edge of a parallel join, producing
empty context. See `api/src/agentgenesis_api/graph/builder.py` header
comment for the full story.

### SSE chat-edit loop

```
POST /runs/{id}/chat        (Bearer JWT, body: {message})
  → acquire per-run asyncio.Lock
  → load latest StoryRevision + chat history (≤50 turns)
  → Synthesizer.stream_chat:
       yields text deltas → SSE 'event: text'
       fence parser detects ```ag-stories``` JSON
         ≤1 removed_ids → commit_revision (auto-apply) → SSE 'event: revision'
         >1 removed_ids → stash preview → SSE 'event: revision_preview'
                          requires POST .../preview/{id}/accept
  → SSE 'event: done'  + 15s ': keep-alive' heartbeats
  → BackgroundTask finalizes ChatTurn (always — survives client disconnect)
```

### Auth flow (real mode)

```
Browser (MSAL.js v5)
  → loginRedirect → login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize
  → callback to http://localhost:5174/auth/login/callback#code=…
  → <AuthCallback> renders <Navigate to="/" />
  → useActiveAccount() = authenticated
  → apiFetch sets Authorization: Bearer <user JWT>
  → backend validates JWT (aud = client_id, v2 token)
  → backend OBO exchange: client_secret + user_assertion → Graph token
  → MS Graph calls (delegated, organizer-only for recordings)
```

---

## 7. Provider seam (PipelineServices facade)

The LangGraph nodes never touch `GraphClient` or `ClaudeClient` directly.
They go through `deps.services.{meetings,recording,frames,synth,db_session_factory}`.
The lifespan swaps the concrete impl at boot:

| Provider | Trigger | Used for |
|---|---|---|
| `RealServices` | default (when `AG_USE_STUB_NODES != 1`) | Production: real Graph + Claude |
| `StubServices` | `AG_USE_STUB_NODES=1` | Local dev + tests: fixtures + canned synth |
| `NoopServices` | `build_graph(deps=None)` | Topology tests only |

Add a new service method = update `services/protocols.py` + Real + Stub +
Noop in one PR. Adding only one breaks topology tests.

---

## 8. Persistence model

**DB is the source of truth.** Filesystem `data/runs/{id}/stories.json` is a
cache rebuildable from the latest `StoryRevision` row.

Four SQLAlchemy tables (`api/src/agentgenesis_api/db/models.py`):

| Table | PK | Purpose |
|---|---|---|
| `run` | `id` | Projected `Run` state. Hydrated into in-memory store on boot. |
| `approval` | `(run_id, story_id)` | Per-user approval flag. |
| `story_revision` | `(run_id, version)` | Versioned stories. `content_json` IS the story list. |
| `chat_turn` | `id` autoincr | User + assistant turns. `status` = `streaming` → `done`/`error`. |

`commit_revision` (`services/revisions.py`):
1. Insert `StoryRevision` row → `session.commit()`.
2. Atomic `os.replace(tmp, stories.json)`.
3. Best-effort `stories.v{N}.json` snapshot.
4. Cleanup approvals for story ids no longer present.

Caller MUST hold the per-run `asyncio.Lock` from `get_run_lock(run_id)`.

---

## 9. Critical invariants — never violate

1. **Single-worker uvicorn only.** `main.py:_check_single_worker` refuses
   `WEB_CONCURRENCY > 1` at boot. Multi-worker requires DB-backed advisory
   locks (out of scope). All locks are in-process `asyncio.Lock`.
2. **DB-first writes.** Never write `stories.json` to disk before the
   `StoryRevision` row is committed. A disk-only write that loses the DB
   commit is unrecoverable.
3. **User scoping is implicit.** `Run.user_oid`, `Approval.user_oid`,
   `StoryRevision.user_oid`, `ChatTurn.user_oid` enforce IDOR. Cross-user
   reads return 404 (NEVER 403 — never disclose run existence).
4. **`safe_resolve` for filesystem.** Every `data/runs/{id}/...` access
   goes through `GraphRunner.safe_resolve(run_id, rel_path, user_oid)` —
   user-scoped + path-traversal-guarded.
5. **Provider seam parity.** `services/protocols.py` is the contract. Real
   + Stub + Noop must all implement every method. Tests use Stub or Noop;
   never Real.
6. **`asyncio.CancelledError` is BaseException in 3.11+.** `except
   Exception:` does NOT catch it. SSE / BackgroundTask code that needs to
   survive client disconnect uses `try / finally` or
   `StreamingResponse.background` (NOT `BackgroundTasks` parameter).
7. **MSAL silent-refresh keeps `acquireTokenPopup`.** Mid-session token
   refresh must NOT navigate away (would lose in-memory state). Only
   login + logout use `loginRedirect` / `logoutRedirect`.

---

## 10. Conventions

### File naming

- Python: `snake_case.py`.
- TS/JS/CSS: `kebab-case.ts`, `kebab-case.tsx`, `kebab-case.css`.
- Tests: `test_<module>.py` (pytest auto-discovery).
- Plan dirs: `YYMMDD-HHMM-kebab-slug/` under `plans/`.
- Reports: `{type}-YYMMDD-HHMM-{slug}-report.md` under `plans/reports/`.

### Code style

- Python: ruff (`line-length = 100`, target `py313`). Run `uv run ruff
  check src tests` before commit.
- TypeScript: `strict` mode. `tsc -b` clean before commit. No frontend
  linter configured beyond TypeScript's own checks.
- Avoid emojis in code/docs unless explicitly asked.
- Default to writing no comments — names should carry meaning. Comment
  only when the WHY is non-obvious (invariant, race, surprising
  trade-off).

### Commit messages

- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`,
  `docs(scope):`, `chore(scope):`, `test(scope):`. Scope = `api`, `app`,
  `design-system`, `plan`, `journals`.
- Use `git commit -m "$(cat <<'EOF' ... EOF)"` heredoc form for
  multi-line messages.
- NO AI references / "co-authored-by: Claude" footers — clean
  conventional commits.
- `chore` and `docs` are NOT used for changes inside `.claude/` (that
  directory is gitignored anyway).

### Imports / module boundaries

- `from __future__ import annotations` at the top of every Python file
  that uses generics in annotations.
- Backend modules use absolute imports
  (`from agentgenesis_api.graph.nodes import ...`).
- Frontend uses `@ds/*` for design-system, `~/lib/...` not used (Vite
  alias only for `@ds`).

---

## 11. Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `RuntimeError: claude_summary: state is missing 'multimodal_context'` | Stale LangGraph checkpoint OR `/resume` after a partial pause | `rm api/data/checkpoints.sqlite api/data/agentgenesis.db` (dev wipe) |
| `KeyError: 'multimodal_context'` in `claude_draft_stories` | Same as above (older code path) | Same wipe. Recovery logic in current code rebuilds. |
| `stories=[]` + `source_meeting_title=''` | Pipeline ran with empty upstream (e.g. NoopSynth path or empty real meeting) | Verify provider seam: log line `wired=True`; confirm `AG_USE_STUB_NODES` if stubbing |
| `ValueError: Entra ID config required` | Missing `AG_ENTRA_*` env vars | Fill `api/.env` OR set `AG_USE_STUB_NODES=1` |
| `RuntimeError: ffmpeg not found on PATH` | ffmpeg missing | `brew install ffmpeg` (or set `AG_USE_STUB_NODES=1` — stub falls back to canned manifest) |
| `AADSTS50011 redirect_uri_mismatch` | Entra app reg doesn't list `http://localhost:5174/auth/login/callback` exactly | Register the URI on the SPA platform |
| `AADSTS65001 consent_required` | Admin consent for Graph delegated scopes not granted | Azure portal → API permissions → Grant admin consent |
| `401 Unauthorized` on every endpoint | `accessTokenAcceptedVersion` not set to `2` in app manifest | Edit Entra app manifest → Save → retest |
| `import fcntl` fails on Windows | POSIX-only stdlib | Already handled in `db/engine.py:_try_acquire_file_lock` (uses msvcrt on Windows) |
| `data/runs/{id}/` empty but `run.status=done` | Old broken run from before recovery fixes; or `cwd` mismatch | Check `pwd` of the running uvicorn; if old, wipe DB + checkpoints |
| Empty `/meetings` response (real mode) | Delegated `OnlineMeetingRecording.Read.All` is organizer-only in personal calendars; channel meetings differ | Use a meeting you organized; or check Teams web UI for the same user |

---

## 12. Where to find more

| Topic | Path |
|---|---|
| Entra ID portal walk-through | `docs/entra-id-setup.md` |
| Architecture diagram (visual) | `docs/diagrams/architecture-overview.png` |
| Active plans (work-in-flight) | `plans/{date}-{slug}/plan.md` |
| API README (deployment, troubleshooting) | `api/README.md` |
| LangGraph state schema | `api/src/agentgenesis_api/graph/state.py` |
| Pipeline services contract | `api/src/agentgenesis_api/services/protocols.py` |
| SQLAlchemy schema | `api/src/agentgenesis_api/db/models.py` |
| MSAL config | `app/src/auth/msal-config.ts` |
| Recent decision rationale | `docs/journals/` |
| Slash commands (Cursor) | `.cursor/commands/*.md` (see §13) |
| Plan-workflow rule | `.cursor/rules/plan-workflow.mdc` |

---

## 13. Slash commands & planning workflow

This repo ships custom slash commands under `.cursor/commands/` for
Cursor + a shared workflow rule under `.cursor/rules/`. Equivalent
behavior is available in Claude Code via the `ck` CLI (`npm install -g
claudekit`) — same plan-file structure, same gates, same conventions.

| Command | Purpose | When to use |
|---|---|---|
| `/ck-plan <task description>` | Create a multi-phase plan under `plans/YYMMDD-HHMM-<slug>/`. Phases get individual `phase-NN-*.md` files with frontmatter (status, priority, effort, dependencies). | User asks to plan / architect / design / scope a feature. |
| `/ck-plan-red-team [plan-path]` (or `/ck-plan red-team`) | Adversarial review of an existing plan. Five hostile roles (Security Adversary, Failure Mode Analyst, Assumption Destroyer, Scope & Complexity Critic, Verification Skeptic). Outputs findings with severity (CRITICAL → NIT) and applies them inline. | Plan touches auth, security, payments, data, public APIs, infra. |
| `/ck-plan-validate [plan-path]` (or `/ck-plan validate`) | Critical-questions interview. Surfaces ambiguity ("should probably…", missing acceptance criteria, hand-wavy thresholds). Asks the user 3-8 grounded multiple-choice questions. | Plan looks done but has nagging gaps. Cheaper than `/red-team`. |
| `/ck-cook <plan-path>` | Execute the plan phase-by-phase. Reads phase file, implements, runs tests + typecheck + ruff, walks success criteria, code-reviews diff, marks phase complete. | Plan is finalized and you want to ship. |

### The workflow loop

```
/ck-plan <ask>                       → creates plans/<dir>/
    ↓
/ck-plan-validate plans/<dir>/plan.md     → 3-8 questions; applies answers
    ↓
/ck-plan-red-team plans/<dir>/plan.md     → findings; applies inline
    ↓
/ck-cook plans/<dir>/plan.md         → implements phase 1 → N
    ↓
ask user to commit + push
```

You can skip `/ck-plan-validate` or `/ck-plan-red-team` for small / low-risk plans.
`/ck-plan` accepts a `--fast` flag (in the message) to skip them
automatically.

### What lives where

- **Rule definition** (the workflow the agent follows):
  `.cursor/rules/plan-workflow.mdc`. Auto-attached when the user is
  editing inside `plans/` or referencing `AGENTS.md`.
- **Command bodies** (what each slash command actually does):
  `.cursor/commands/{plan,red-team,validate,cook}.md`. Cursor's
  slash-command picker shows these.
- **Plan output** (work product): `plans/YYMMDD-HHMM-<slug>/` —
  `plan.md` + `phase-NN-<slug>.md` per phase. Never write plans
  anywhere else.
- **Reports** (research notes, code-review handoffs): `plans/reports/`
  with naming `{type}-YYMMDD-HHMM-{slug}-report.md`. No generic names
  like `notes.md` or `review.md`.

### Plan file contract

`plan.md` MUST have these sections:

- **Overview** — 1-2 paragraphs, plain English.
- **Decisions locked** — table: decision, pick, why. Once user
  confirms a decision here, treat it as STICKY — `/ck-plan-red-team` and
  `/ck-plan-validate` cannot silently reverse it; they must surface
  contradictions and ask.
- **Phases table** — status per phase (pending / in_progress /
  completed).
- **Dependencies** — `blockedBy` / `blocks` if any.
- **Out of scope** — explicit; protects against scope creep.
- **(Optional) Red Team Review** — findings table after `/ck-plan-red-team`.
- **(Optional) Validation Log** — Q&A session record after `/validate`.

Each `phase-NN-<slug>.md` MUST have frontmatter + Overview +
Requirements + Architecture + Related Code Files (Create / Modify /
Delete) + Implementation Steps + Success Criteria (`- [ ]`
checkboxes) + Risk Assessment.

### Plan + AGENTS.md interaction

This file (`AGENTS.md`) is project-wide context. Plan files are
work-in-flight. When the agent operates inside `plans/<dir>/`, the
plan-workflow rule auto-attaches AND `AGENTS.md` stays implicit — both
inform the agent. If you need to pin `AGENTS.md` explicitly, type
`@AGENTS.md` in the chat.

---

## 14. Rules for AI agents working here

1. **Read this file + the relevant `plans/{active}/plan.md` before editing.**
2. **Always run `uv run ruff check src tests` (api) and `npm run typecheck`
   (app) before committing.** Don't commit if either is dirty.
3. **Never write to `data/runs/` from outside the runner / commit_revision
   path.** Disk is a cache; DB is the truth.
4. **Never widen the multi-tenant assumption** without explicit user
   confirmation — backend OBO endpoint is hard-coded to single-tenant.
5. **Don't skip the recovery path** in `claude_summary` / `claude_draft_stories`
   — it handles stale checkpoints. If you remove it, runs that hit a
   partial-state LangGraph checkpoint will die with a `KeyError`.
6. **Don't add code in `.claude/`** — that's tooling config, gitignored.
   Project rules live in `.claude/rules/*.md` (gitignored as a directory,
   tracked via `.claude/rules/` being explicit). When in doubt, ask.
7. **Don't commit `.env`** — gitignored. Use `.env.example` for shape
   docs.
8. **Don't introduce parallel branches in the LangGraph DAG** without
   reading the `builder.py` header comment — the BSP semantics will bite.
9. **Test before claiming success.** "tests pass + ruff clean" ≠ "feature
   works". Real-mode features need real-mode smoke (or explicit
   `AskUserQuestion` to confirm trade-off).
10. **Plan files in `plans/`** are work-in-flight. Don't edit completed
    plans except via `ck plan archive`.
11. **When the user asks you to plan something**, follow the slash-command
    flow in §13 (`/plan` → optionally `/red-team` or `/validate` →
    `/cook`). Even if no slash command is typed, mirror the workflow:
    scout the codebase, scope-challenge, scaffold under
    `plans/YYMMDD-HHMM-<slug>/`, populate phases, present handoff
    options. The CLI tool `ck plan create` is optional — fall back to
    hand-scaffolding the same file structure if it's not installed.

---

_Last updated: 2026-06-10. If you add a major flow, update §6 and the
architecture diagram (Excalidraw source in `docs/diagrams/`)._
