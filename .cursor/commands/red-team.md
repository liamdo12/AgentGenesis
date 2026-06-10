# /red-team — adversarial review of an existing plan

Invoke when the user wants an adversarial pass on a plan file. Default
target: the most recently modified `plan.md` under `plans/`. User can
pass an explicit path as the argument.

## When to use

- Plan touches auth, security, payments, data integrity, public APIs,
  migrations, infra.
- High blast radius (multi-system change).
- User explicitly typed `/red-team`.

## Steps

1. **Resolve target plan.** If user passed a path, use it. Else `ls -t
   plans/*/plan.md | head -1`.

2. **Read all plan files in that directory.**
   - `plan.md` (overview + decisions).
   - Every `phase-*.md`.

3. **Read the referenced code paths.** The plan should cite `file:line`
   for every concrete claim. Read those files. If the plan claims an
   invariant that isn't in the code, that's a finding.

4. **Adversarial roles** — adopt all of these for the review:

   | Role | Focus |
   |---|---|
   | Security Adversary | AuthN/Z, CSRF, SSRF, IDOR, secrets handling, XSS, injection, supply chain |
   | Failure Mode Analyst | Race conditions, network failures, partial writes, crash-recovery, cancellation |
   | Assumption Destroyer | Every "we can assume" in the plan must hold up. Cite counter-examples from code. |
   | Scope & Complexity Critic | YAGNI / KISS / DRY violations. Hidden complexity. Unjustified abstractions. |
   | Verification Skeptic | "How do we know this works?" Every success criterion must be testable. |

5. **Produce findings.** Each finding has this shape:

   ```
   [severity: CRITICAL | HIGH | MEDIUM | LOW | NIT]
   File: <plan file or code path>
   Issue: 1-line summary
   Why it matters: 2-3 sentences (cite evidence — file:line)
   Fix: concrete change to the plan
   ```

   Severity:
   - **CRITICAL**: will fail in production.
   - **HIGH**: will fail intermittently or break security.
   - **MEDIUM**: will require rework after first iteration.
   - **LOW**: polish.
   - **NIT**: optional.

6. **Cross-cutting observations.** A short section noting patterns across
   findings (e.g. "plan assumes serial execution but code uses asyncio
   throughout").

7. **Whole-plan consistency sweep.** After applying findings, re-read
   every plan file and grep for:
   - Stale terms / renamed APIs.
   - Rejected assumptions still cited.
   - Numbers that drifted.
   - Duplicate embedded drafts.

8. **Surface escalations.** Any finding that REVERSES a user-confirmed
   decision must be presented as an `AskUserQuestion`-style choice, NOT
   silently applied. Cite "user confirmed in the original ask: …" and
   ask: keep / change / hybrid?

9. **Update the plan** with applied findings inline. Add a "Red Team
   Review" section to `plan.md` with a findings table (`# | Finding |
   Severity | Disposition | Applied To`).

10. **Output** under 700 words, ending with:

    ```
    **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED
    **Findings:** <count by severity>
    **Recommendation:** apply findings inline | discard plan | refine via /validate
    ```

## Rules

- Adversarial means find issues, NOT validate. Reviewers who "find
  nothing" are doing it wrong — at minimum surface trade-offs or
  unverifiable claims.
- Cite evidence — file/line or doc reference for every finding.
- Don't suggest fixes the user didn't sanction. Decisions the user
  explicitly locked stay locked; flag the trade-off for them to decide.
- "Apply inline" is the default for unambiguous defects (CRITICAL,
  HIGH); MEDIUM and LOW only if they don't touch user decisions.
