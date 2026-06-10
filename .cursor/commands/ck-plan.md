# /ck-plan — create a multi-phase implementation plan (or route to a sub-action)

Mirrors Claude Code's `/ck:plan` family.

## Argument routing

Inspect the first word of the user's argument after `/ck-plan`:

| First word | Action | Equivalent direct command |
|---|---|---|
| `validate` | Run validation interview. Read + follow `.cursor/commands/ck-plan-validate.md`. | `/ck-plan-validate <path>` |
| `red-team` (or `redteam`) | Run adversarial review. Read + follow `.cursor/commands/ck-plan-red-team.md`. | `/ck-plan-red-team <path>` |
| `archive` | Mark plan completed + `git mv` it into `plans/archive/`. | (no separate command yet) |
| anything else (default) | Treat the whole argument as a task description and create a new plan per the steps below. | `/ck-plan <task>` |

Examples:

- `/ck-plan add Stripe checkout` → create plan.
- `/ck-plan validate plans/260610-1000-stripe/plan.md` → validate that plan.
- `/ck-plan red-team` → red-team the most recently modified plan.

When routing to a sub-action, READ the corresponding command file FIRST and follow its steps end-to-end. Don't paraphrase from memory.

---

## Default action: create a new plan

Triggered when the argument is a task description (not `validate` / `red-team` / `archive`). Output is a directory under `plans/` with `plan.md` + one `phase-NN-<slug>.md` per phase.

## Steps

1. **Auto-detect mode.** Default `--auto`. Force `--hard` if the task
   touches: auth, security, payments, data integrity, public APIs,
   migrations, infra. Force `--fast` if scope is trivial (single file,
   <20 word description, user said "quick").

2. **Pre-creation scan.** `ls plans/` and read frontmatter of any
   pending plan. If the new ask overlaps with an existing one, declare
   `blockedBy` / `blocks` in both plan.md frontmatters.

3. **Scope challenge.** Skip for `--fast`. Otherwise ask the user 1-3
   sharp questions:
   - "What's the smallest thing that proves this works?"
   - "What's explicitly out of scope this round?"
   - "Any locked decisions you don't want me to revisit?"

4. **Codebase scout.** Read affected files. Cite `file:line` in the plan
   for every concrete claim.

5. **Scaffold.** If `ck` CLI is installed:
   ```bash
   ck plan create \
     --title "<plan title>" \
     --phases "Phase 1 name,Phase 2 name,..." \
     --dir plans/$(date +%y%m%d-%H%M)-<slug>
   ```
   Otherwise create the directory + files by hand using the §5 templates
   in `.cursor/rules/plan-workflow.mdc`.

6. **Read every generated stub** before populating (Cursor will reject
   Write on a file it hasn't observed).

7. **Populate plan.md** with:
   - Overview (1-2 paragraphs, plain English).
   - Decisions locked (table: decision, pick, why).
   - Phases table (status: pending).
   - Dependencies (`blockedBy` / `blocks` if any).
   - Out of scope.

8. **Populate each phase-NN file** with:
   - Frontmatter: phase, title, status, priority (P1/P2/P3), effort,
     dependencies.
   - Overview (1-2 sentences).
   - Requirements (functional + non-functional bullets).
   - Architecture (diagram or prose).
   - Related Code Files (Create / Modify / Delete with paths).
   - Implementation Steps (numbered, concrete).
   - Success Criteria (`- [ ]` checkboxes).
   - Risk Assessment (R1, R2, ... with mitigations).

9. **Activate the plan** (if `ck` is installed):
   ```bash
   ck plan status plans/<dir>/plan.md
   ```

10. **Post-plan handoff.** Present 3-4 options, recommended first:
    - `/red-team` (if `--hard` mode or auth/security/data touch).
    - `/validate` (if moderate scope with ambiguity).
    - `/cook <plan-path>` (start implementation).
    - End session (user reviews offline).

## Output

Final reply: plan directory absolute path + one-paragraph summary +
handoff options.

## Rules

- Plans go in `plans/<dir>/` only. Never write plans anywhere else.
- Cite `file:line` for every concrete codebase claim.
- Don't ask vague questions in the scope challenge — every question must
  have grounded options the user can pick.
- Don't recommend `/cook` until the plan passes consistency sweep.
