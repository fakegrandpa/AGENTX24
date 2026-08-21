# AGENTX24 — Agent Operating Charter

Permanent operating rules for every AI coding agent working in this repository.
These rules override model defaults, personal preferences, and habits.
Skills add procedure; this file adds law. If a skill and this file conflict, this file wins.

---

## 1. What this repository is

- `AGENTX24` is **ONE continuously evolving project** built during a 24-hour hackathon.
- Hour 0: the main problem statement is revealed.
- Every 3 hours: a new feature requirement is announced and must be integrated into **this same project**.
- After every stage, updated source code must be submission-ready and still runnable.
- The problem statement, the stack, and all future features are unknown until announced.

**Consequences that are non-negotiable:**

- A new requirement **never** means a new project, a new folder-per-feature, a fresh scaffold, or a rewrite.
- Nothing that already works may be broken to make something new work.
- The repository must be runnable at all times. "Between refactors" is not an allowed state.

---

## 2. Core principles

**Build**
1. Working software beats impressive design. A judge can only score what runs.
2. Prefer the **smallest reliable solution** that fully satisfies the requirement.
3. Do not overengineer. No abstraction, layer, interface, queue, cache, service split, or config system without a *present* need.
4. Reuse existing patterns, files, helpers, and infrastructure before inventing new ones.
5. Change code incrementally. Small diffs, verified often.
6. Avoid rewrites. Extend working code; replace it only when it provably blocks the requirement.
7. Match the project's existing style, naming, and libraries. Do not introduce a second way to do the same thing.

**Truth**
8. **Never claim something works because code was written.** Only a run/test/observation justifies the word "works".
9. Report status honestly: separate *verified*, *unverified*, and *known broken*. Speculative worry is not a failure; an observed failure is.
10. If you did not run it, say so.

**Safety**
11. Commit a checkpoint after every verified working milestone.
12. Never commit secrets, API keys, tokens, credentials, or `.env` files. Use ignored env files plus a committed example file with placeholder values.
13. Prefer non-destructive recovery (diagnose, targeted fix, restore one file) over destructive resets. Destructive git operations require the user's explicit approval.

**Priorities, in order, when time is short**
14. Does the required flow work → is it reliable → is it clear to a judge → is it fast to demo → is it pretty.

---

## 3. Named global protocols

Skills reference these by name instead of repeating them.

### P1 — Inspect First
Before editing anything: list the relevant part of the tree, read the files you intend to touch, and identify the existing pattern for this kind of change. No edit to an unread file. No new file if an existing one is the natural home.

### P2 — Smallest Reliable Change
State the intended diff surface (files + rough nature of change) before writing it. If your plan touches unrelated files, shrink it. If it deletes working behaviour, redesign it.

### P3 — Verify Before Claim
A change is not done until, in this order, as applicable to the stack:
1. It builds / compiles / typechecks / imports without error.
2. The app or entry point actually starts or the script actually executes.
3. The specific new behaviour is exercised and observed to produce the expected result.
4. The previously working core flow is exercised again and still works.
5. No new startup errors, unhandled exceptions, or fatal logs.

Record the exact commands used and their outcome. Clean up any scratch files you created.

### P4 — Green Checkpoint
"Green" = builds, runs, and the core flow plus the newest feature were observed working.
On green, commit immediately:

```
git add <intended paths>
git commit -m "stage-<N>: <what now works>"
```

Optionally tag stage milestones (e.g. `stage-2-green`) so rollback targets are obvious.
Never commit while the project is known broken; if you must save broken work, use a branch or stash, not `main`.
Stage a specific set of paths rather than blindly committing everything.

### P5 — Secret Hygiene
Check for a `.gitignore` covering env files, credentials, local databases, caches, and dependency directories before the first commit. Reference secrets by variable name in output; never echo their values.

### P6 — Time Box and Triage
Every stage has a hard 3-hour wall clock. Default budget per cycle:

| Phase | Budget | Owner skill |
|---|---|---|
| Understand + plan | 10–15 min | `feature-integrator` |
| Implement | ~90 min | `feature-integrator` |
| Verify + regression | ~25 min | `regression-guardian` |
| Polish (only if green) | ~15 min | `demo-polisher` |
| Submit | ~15 min | `submission-manager` |
| Reserve buffer | ~20 min | — |

**Freeze rule:** in the final 20 minutes of any stage, only bug fixes, verification, and submission work are permitted. No new features, no refactors.
If you are 60% through the implementation budget and the feature is not close, cut scope to the smallest version that satisfies the requirement and say what was cut.

### P7 — Stop-and-Report
Stop and report to the user instead of pushing on when:
- The requirement is genuinely ambiguous in a way that changes the design.
- A requirement appears to demand replacing working architecture.
- The same fix has failed twice — diagnose the root cause and change approach instead of retrying variants.
- The project is red and the cause is not identified within ~10 minutes → switch to `emergency-recovery`.

### P8 — State Labels
Use these words precisely in every report:
- **GREEN** — builds, runs, core flow + newest feature verified.
- **YELLOW** — runs, but some feature is degraded, partially implemented, or unverified. Must be stated explicitly.
- **RED** — does not build or does not run. Highest priority; nothing else matters until it is green.

---

## 4. Living documents

| File | Role | Who writes it |
|---|---|---|
| `AGENTS.md` | Permanent rules. Rarely changes. | Humans |
| `BUILD.md` | Living technical blueprint: scope, stack, run commands, architecture map, extension points, stage log, risks, known limitations, demo script. | `hackathon-architect` creates; other skills append |
| `README.md` | How a judge or organizer runs the project. Created once the run command is stable; kept accurate. | `mvp-builder`, then `submission-manager` |

`BUILD.md` is updated when an **architectural decision, run command, data shape, or scope boundary changes** — not on every commit. The stage log is the exception: append one short line per stage.

---

## 5. Skill routing

| Situation | Skill |
|---|---|
| Problem statement just revealed; no plan yet | `hackathon-architect` |
| Plan approved; nothing built yet | `mvp-builder` |
| A new 3-hour requirement was announced | `feature-integrator` |
| Code changed and needs verification / regression sweep | `regression-guardian` |
| Project is green and time remains before a demo | `demo-polisher` |
| Build broken, crash, failed integration, unknown breakage | `emergency-recovery` |
| A submission deadline is approaching | `submission-manager` |

One skill at a time, in that logical order. Do not run `demo-polisher` on a YELLOW or RED project.

---

## 6. Definition of Done (applies to every stage)

- [ ] Requirement satisfied as literally stated.
- [ ] P3 verification performed, with commands and observed results reported.
- [ ] Previously working core flow re-verified.
- [ ] Project starts from a clean checkout of the committed state.
- [ ] `BUILD.md` stage log updated; blueprint updated if a decision changed.
- [ ] No secrets, no dependency directories, no build caches staged.
- [ ] Green checkpoint committed (P4).
- [ ] Honest status report using P8 labels, including known limitations.
