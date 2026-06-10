# /ck-cook — execute a plan phase-by-phase

Invoke when the plan is written, validated, and the user wants to start
implementing. User passes the plan path: `/ck-cook plans/<dir>/plan.md`.

## When to use

- Plan has passed `/red-team` and/or `/validate` (or is small enough to
  skip).
- User explicitly typed `/cook <path>`.

## Steps

1. **Resolve the plan.** Read `plan.md` + every `phase-*.md` in the
   plan directory. Mandatory.

2. **Detect mode** from the user message:
   - `--fast`: skip review gates, no test pause between phases.
   - `--auto`: auto-approve low-risk artifact-validated steps; stop on
     high-risk before finalize/commit.
   - default (`interactive`): pause for user approval before each phase.

3. **Hydrate tasks** (if Cursor has a TODO list mechanism, or use a
   local tracker). One task per phase, with dependency chain matching
   the phase `dependencies` frontmatter.

4. **Execute phase-by-phase** in order:

   For each phase:

   a. Mark task in-progress.

   b. Read every "Related Code Files" listed in the phase. Confirm they
      match the current code (the plan may have drifted).

   c. Implement the phase per Implementation Steps. Edit code in place;
      never duplicate files or leave `.old` stubs.

   d. Run validation commands appropriate to the surface:
      - Backend: `cd api && uv run pytest && uv run ruff check src tests`
      - Frontend: `cd app && npm run typecheck && npm run build`
   
   e. Verify Success Criteria checkboxes one by one. Check them off as
      they pass.

   f. **Mandatory code-review pass.** Run an adversarial self-review of
      the diff before committing — adopt the same roles as `/red-team`:
      Security Adversary, Failure Mode Analyst, Verification Skeptic.
      Fix issues found, OR surface a question if a finding requires the
      user's input.

   g. Mark task complete; update plan file's phase status (`status:
      completed`).

5. **Hard gates** — never violate, regardless of mode:

   - **Tests pass.** If a test fails, fix the root cause OR ask the user
     before downgrading. Never `--no-verify` or skip tests silently.
   - **No new lint / type / build errors anywhere in the repo.**
   - **No regression to features outside the phase's blast radius.**
     Walk the touchpoints.
   - **Public contracts unchanged** unless the plan explicitly says so.

6. **Finalize after the last phase**:

   a. Run the full test suite one more time.

   b. Update `docs/` if the changes warrant. New flow? Update
      `docs/diagrams/architecture-overview.png` (Excalidraw source in
      `docs/diagrams/`).

   c. Ask the user before committing — confirm scope, message, and
      whether to push.

   d. Conventional commit messages: `feat(scope):`, `fix(scope):`, etc.
      Scope = `api`, `app`, `design-system`, `plan`, `journals`. No
      "co-authored-by: AI" footers.

   e. After commit, ask if they want a journal entry under
      `docs/journals/YYMMDD-<slug>.md` capturing decisions + lessons.

## Rules

- **Plan files are read-only once execution starts.** Update only their
  phase status (pending → in_progress → completed). Don't rewrite
  bodies mid-cook.
- **Never delegate understanding.** Don't tell a sub-agent "implement
  the plan" — read the plan yourself, then act.
- **Don't expand scope** to fix things the plan didn't call out.
  Surface the issue, ask the user.
- **Verify, don't assume.** "Tests pass" only means what the tests cover.
  Walk the workflow if the plan touches user-facing surfaces.
- **If you hit 3 consecutive failures on the same step**, STOP. Question
  the plan's assumption — don't keep retrying. Ask the user.
