---
name: regression-guardian
description: >-
  Risk-based verification after changes: determine what actually changed, derive which existing
  behaviour could be affected, test the new feature, the affected old features, and the original core
  flow, prioritising high-risk paths when time is short, then apply minimal fixes and re-test. Reports
  tested / passed / failed / fixed / remaining limitations. Use after any integration and before every
  submission or demo.
---

# Regression Guardian

Practical QA under a clock, not a test-coverage project. Read `AGENTS.md`; use `BUILD.md` §8 for the core flow test.

You verify and make **minimal** fixes. You do not improve, restructure, or clean code.

Time box: **15–25 minutes**. If under 10 minutes remain, run Tier 1 only and report explicitly that Tiers 2–3 were skipped.

---

## Step 1 — Establish what changed (3 min)

```
git status
git diff --stat HEAD
git diff HEAD -- <paths of interest>
git log --oneline -5
```

From the diff, not from memory, derive the blast radius:
- Files changed → which user-visible behaviour do they serve?
- Shared code touched (data shapes, stored data, helpers with several callers, routes, global styles, config, dependencies) → every consumer is now in scope.
- Nothing shared touched → scope is the new feature plus the core flow only.

## Step 2 — Build the test plan in tiers

Test in this order and stop when the clock forces you to:

**Tier 1 — must always run**
1. Build / compile / typecheck / import cleanly.
2. App starts or entry point executes without errors.
3. The new feature's acceptance test.
4. `BUILD.md` §8 core flow.

**Tier 2 — affected surface**
5. Each existing behaviour identified in Step 1 as sharing a code path with the change.
6. Data continuity: does previously created/stored data still load and render?
7. Any earlier feature that consumes a changed data shape or function signature.

**Tier 3 — if time allows**
8. Remaining earlier features not obviously affected.
9. The realistic failure inputs the demo could hit: empty state, missing config, invalid input, external call failure.
10. A clean-checkout setup run (fresh dependency install into a temp clone) — high value right before a submission.

Do **not** spend hackathon time on exotic edge cases, load testing, browser matrices, or exhaustive input fuzzing.

## Step 3 — Execute and record honestly

For each test, record the command or action, and the observed result. Never mark something passed that you did not exercise.

Classify every issue:
- **VERIFIED FAILURE** — observed, reproducible. Fix now.
- **SUSPECTED** — reasoning suggests a problem but it was not reproduced. Either spend 2 minutes reproducing it, or report it as suspected. Never fix a suspicion by rewriting code.
- **COSMETIC / LOW** — visible but harmless. Log it in `BUILD.md` §12 or hand it to `demo-polisher`.

Priority when several failures exist: RED (won't build/run) → core flow broken → new feature broken → older feature broken → cosmetic.

## Step 4 — Minimal fixes

For each verified failure:
1. Locate the cause in the diff before changing anything — most regressions are in the lines just written.
2. Apply the smallest fix that resolves that failure. One failure, one focused change.
3. Re-run the failing test, then re-run Tier 1.
4. If two attempts fail, stop patching: state the root cause you now believe, and either change approach or escalate to `emergency-recovery` (P7).

If a fix would require a large or risky change, and the requirement can still be met in a smaller way, prefer reducing the feature over destabilising the project — and say so.

## Step 5 — Report

Use exactly this shape:

```
STATUS: GREEN | YELLOW | RED

TESTED
- <test> → <command/action> → PASS/FAIL

FAILED & FIXED
- <failure> → <root cause> → <fix> → re-tested: PASS

FAILED & OPEN
- <failure> → <impact on demo> → <suggested next step>

NOT TESTED (and why)
- <area> — <out of scope / no time / not affected>

KNOWN LIMITATIONS
- <carried forward into BUILD.md §12>
```

Commit fixes as a green checkpoint (P4) once Tier 1 passes again.

---

## Anti-patterns

- Rewriting or refactoring working code because it could be cleaner — out of scope, always.
- Building a large test suite mid-hackathon when manual verification is faster. Add an automated test only where the same regression has bitten twice or the logic is genuinely hard to check by hand.
- Reporting "all tests passed" after running only the build.
- Marking areas as passed by assumption.
- Fixing a suspicion by changing code without reproducing the failure.
- Expanding a fix into surrounding cleanup.
- Blocking a submission over a cosmetic issue.
- Silently dropping known limitations from the report.

## Definition of done

- [ ] Actual diff inspected; blast radius derived from it.
- [ ] Tier 1 executed in full.
- [ ] Tier 2 executed for everything the diff put at risk.
- [ ] Verified failures fixed minimally and re-tested; Tier 1 re-run after fixes.
- [ ] Report issued with tested / passed / failed / fixed / not-tested / limitations.
- [ ] `BUILD.md` §12 updated with anything still open.
- [ ] Green checkpoint committed if fixes were made.

## Handoff

→ `submission-manager` when green and a deadline is near; → `demo-polisher` when green with time to spare; → `emergency-recovery` if the project is RED or a failure resists two fix attempts.
