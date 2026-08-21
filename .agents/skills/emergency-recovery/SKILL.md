---
name: emergency-recovery
description: >-
  Disciplined triage when the project will not build, will not run, crashes, or an integration broke
  something: stop changing code, read the actual error, inspect git status/diff/log, form a single root
  cause hypothesis, apply the smallest safe fix, and if needed restore the last known green checkpoint.
  Use the moment the project is RED or a failure resists two fix attempts.
---

# Emergency Recovery

Read `AGENTS.md`. The project is RED. Nothing else matters until it is green again.

The failure mode that loses hackathons is not the bug — it is the panicked sequence of speculative edits after it. **Diagnosis before change. Always.**

Time box: **10 minutes to a hypothesis.** No hypothesis by then → roll back to the last green checkpoint (Step 6) rather than continuing to explore.

---

## Step 0 — STOP

- Make no further edits until Steps 1–3 are complete.
- Do not restart the process hoping it resolves itself, more than once.
- Do not install, upgrade, or remove dependencies as a guess.
- Do not "clean up" anything.
- Do not run any destructive git command yet.
- Every currently-broken change is still on disk and recoverable — keep it that way.

## Step 1 — Read the actual error

- Capture the **complete** message: type, message text, file, line, and the top frames of the stack. Where relevant, capture the client/console error too, not only the server side.
- Distinguish the layers: setup/install error, compile/type error, startup error, runtime error, integration error (external service, network, credentials), data error (stored data no longer matches the code), or environment error (port in use, missing tool, wrong version, path issue).
- Read the file and line the error names. Frequently the answer is literally there.
- Reproduce it once deliberately, and note the exact command that reproduces it. If it is intermittent, say so — that changes the diagnosis.

## Step 2 — Inspect the change history

```
git status
git diff --stat HEAD
git diff HEAD -- <files named in the error>
git log --oneline -10
```

Ask: what is different between the last known green state and now? Uncommitted changes are the prime suspect. Also check for changes you did not intend — a generator, formatter, or install may have rewritten config or lock files.

## Step 3 — One root cause hypothesis

State it in one sentence, in the form: *"X fails because Y, introduced by Z."*

Then check it against the evidence before acting. If you cannot name Y, you are not ready to edit — gather one more piece of evidence (targeted log line, minimal reproduction, isolate the failing call) rather than guessing. Prefer the boring explanations: typo, wrong import path, missing await/async, null or undefined value, changed signature with a stale caller, stale build cache, missing env var, wrong working directory, port conflict, dependency version drift, uninstalled new dependency.

## Step 4 — Choose the recovery route

| Situation | Route |
|---|---|
| Cause is local and understood | **Targeted fix** — smallest edit to the identified line(s), nothing else |
| One file is mangled beyond repair | **Restore that file** from the last green commit, re-apply the intent carefully |
| Recent uncommitted work is broadly broken and time is short | **Shelve it** (`git stash push -m "wip-<stage>-broken"`), confirm green, then re-implement smaller |
| The last commit itself is broken | **Return to the last green tag/commit** on a new branch and re-apply the feature minimally |
| Environment or dependency state is corrupt | **Reinstall dependencies from the lock file** (delete the dependency directory, reinstall) — data and source untouched |
| External dependency is failing | **Switch to the pre-decided fallback** from `BUILD.md` §10 (fixture, cached response, offline mode) |

Rules for all routes:
- Change one thing, then test. Never bundle several speculative fixes — you will not know which worked, or what else you broke.
- Nothing that destroys uncommitted work without the user's explicit approval: no `reset --hard`, no `clean -f`, no force push, no branch deletion. Stash or branch instead.
- If the same fix fails twice, the hypothesis is wrong. Return to Step 3; do not iterate on variants.
- Restoring a green checkpoint and losing 40 minutes of work is a good trade against staying RED at a submission deadline. Make that call early, not late.

## Step 5 — Verify recovery (P3)

1. Build/compile/typecheck clean.
2. App starts or entry point runs clean.
3. `BUILD.md` §8 core flow passes.
4. The most recently added feature: works, or is explicitly reported as reverted/degraded.
5. No new errors introduced by the fix itself.

## Step 6 — Checkpoint and report

Green checkpoint immediately (P4): `fix: recover from <failure> — <cause>`.

Report:

```
FAILURE:   <the actual error>
CAUSE:     <root cause, evidence-backed>
ACTION:    <fix or rollback route taken>
LOST:      <work discarded or reverted, if any>
STATUS:    GREEN | YELLOW  (+ what is degraded)
NEXT:      <how to re-apply the reverted work more safely>
```

If work was shelved or reverted, note it in `BUILD.md` §12 so it is not forgotten in the next stage.

---

## Anti-patterns

- Editing before reading the full error.
- Multiple simultaneous speculative changes.
- Rewriting a file, module, or the whole feature "to be safe" instead of fixing the identified cause.
- Rebuilding the project from scratch because it feels faster. It never is.
- Blind dependency churn: upgrading, downgrading, or adding packages without evidence.
- Deleting or reverting work destructively without approval.
- Treating a symptom (silencing an error, wrapping everything in try/catch, deleting the failing call) while the cause stands.
- Chasing a suspected second bug before the first is confirmed fixed.
- Reporting recovery without re-running the core flow.
- Staying RED past a submission deadline out of attachment to unfinished work.

## Definition of done

- [ ] Full error captured and reproduced deliberately.
- [ ] `git status` / `diff` / `log` inspected before any edit.
- [ ] Single root cause stated and evidence-checked.
- [ ] Smallest safe route taken; no destructive git operation without approval.
- [ ] Build, startup, and core flow re-verified.
- [ ] Green checkpoint committed.
- [ ] Report issued, including any lost work and the plan to re-apply it.

## Handoff

→ `regression-guardian` to confirm nothing else regressed; → `feature-integrator` to re-apply reverted work in smaller slices; → `submission-manager` if a deadline is imminent (submit the green state, not the ambition).
