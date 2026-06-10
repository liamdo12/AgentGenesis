# /validate — critical-questions interview on an existing plan

Invoke when the user wants a final ambiguity-scrub on a plan before
`/cook`. Default target: most recently modified `plan.md` under
`plans/`. User can pass an explicit path.

## When to use

- Plan is written and looks "done" but you have nagging doubts.
- Moderate scope with ambiguity ("we should probably…" phrasing).
- Plan has been red-teamed and you want one more pass on
  user-decision-shaped questions.

`/validate` is CHEAPER than `/red-team` — it surfaces missing info from
the user, not findings from the codebase.

## Steps

1. **Resolve target plan.** If user passed a path, use it. Else `ls -t
   plans/*/plan.md | head -1`.

2. **Read all plan files** (`plan.md` + every `phase-*.md`).

3. **Identify ambiguity zones.** Search the plan for:
   - Hand-wavy language: "should probably", "ideally", "maybe", "we'll
     see", "TBD", "future iteration".
   - Missing acceptance criteria on phases.
   - Phases with effort `""` (empty).
   - "If" without "else": "if X then Y" with no Y' path.
   - Numbers that look pulled from a hat (thresholds, timeouts, batch
     sizes).
   - User-shaped decisions presented as locked but with no rationale.

4. **Generate 3-8 critical questions.** Each question must:
   - Have 2-4 concrete options (NOT abstract — grounded in the plan).
   - Recommend one option first (mark with "(Recommended)").
   - Cite plan-file:line for context.
   - Be answerable in <30 seconds by the user.

   Use `AskUserQuestion` (Claude Code) or interactive prompt (Cursor) to
   present all questions in one batch.

5. **Apply confirmed answers to the plan.**
   - Update frontmatter (effort, priority, dependencies) if questions
     touched those.
   - Update Decisions Locked table in plan.md.
   - Update phase bodies inline.

6. **Whole-plan consistency sweep.** Re-read every plan file. Verify:
   - All hand-wavy language is now concrete or annotated as known-TBD.
   - Acceptance criteria exist on every phase.
   - User answers don't contradict each other.

7. **Add a Validation Log section** to `plan.md`:

   ```markdown
   ## Validation Log

   ### Session — YYYY-MM-DD
   **Questions asked:** N
   **Confirmed decisions:**
   1. [Topic] <decision> — applied to <phase>.
   2. ...

   ### Whole-Plan Consistency Sweep
   - Files reread: plan.md + N phase files.
   - Reconciled stale references: ...
   - Unresolved contradictions: 0
   ```

8. **Output** under 400 words, ending with:

   ```
   **Status:** plan is ready for /cook
   **Open questions:** <count> (must be 0 before /cook)
   ```

## Rules

- Never ASK what you can SCOUT. Read code first; ask only what code
  can't answer.
- Don't ask leading questions. Each option must be a real choice.
- Recommend the option that aligns with the project's
  declared invariants (single-worker, DB-first, YAGNI, etc.).
- If the user picks an answer that conflicts with an existing locked
  decision, surface the conflict and ask for explicit confirmation —
  don't silently reverse.
