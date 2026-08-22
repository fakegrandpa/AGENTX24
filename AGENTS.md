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

### P9 — Build Documents (immutable and numbered)
There is **no single mutable `BUILD.md`**. Each stage gets exactly one numbered document.

**Numbering — do this before creating any build document:**
1. List the workspace root for existing `BUILD*.md` files.
2. Find the highest existing number N.
3. Create `BUILD<N+1>.md`. Never write to a number that already exists.

`BUILD1.md` is the Hour 0 architecture and planning record. `BUILD2.md`, `BUILD3.md`, … are stage records, one per announced requirement.

**Immutability:**
- The planning content of any build document is **frozen once written**.
- The **current** stage's document may receive an **append-only** `Stage Outcome` block at the bottom, written by the skills that execute that stage (what was actually built, verified, cut, and any new limitations). Never rewrite the planning sections above it.
- **Earlier** stages' documents are historical records: do not edit, rename, delete, renumber, or reflow them. A genuine factual correction is appended as a clearly labelled `[correction]` line, never an in-place rewrite.
- `BUILD-LAST.md` is created **only** near the final stage, as a compact final system map. It never replaces or deletes the numbered documents.

**Source of truth, in order:**
1. **The current actual codebase** — the only authority on what exists.
2. The **latest** relevant `BUILD<n>.md` — latest planning context and intent.
3. **Earlier** `BUILD<n>.md` files — historical architecture and decision context.
4. **Git history** — checkpoint and change history.

Never assume an older build document still describes the implementation. Inspect the code before planning or changing anything. Where a document and the code disagree, the code wins and the discrepancy is worth reporting.

**Cross-references** use section *names*, not numbers, because each document has its own layout:
- The original core flow test lives in `BUILD1.md` → `Core Flow Test`. It stays the baseline regression check for the whole event.
- Per-stage acceptance tests live in that stage's document → `Acceptance Test`.

---

## 4. Living documents

| File | Role | Who writes it |
|---|---|---|
| `AGENTS.md` | Permanent rules. Rarely changes. | Humans |
| `BUILD1.md` | Hour 0 architecture record: problem, scope, stack and decisions, MVP, architecture, core flow test, build order, risks, what not to build yet. Frozen after creation. | `hackathon-architect` |
| `BUILD2.md`, `BUILD3.md`, … | One per announced requirement: the requirement, what already exists in code, affected components, integration strategy, regression risks, plan, decisions, what must stay unchanged. Frozen after its stage ends. | `feature-integrator` (planning), append-only outcome from the executing skills |
| `BUILD-LAST.md` | Final compact system map. Created only near the end. | `hackathon-architect` or `submission-manager`, when asked |
| `README.md` | The always-current answer to "how do I run this and what does it do". Updated whenever the run commands or feature set change. | `mvp-builder`, then each stage |

Because build documents are frozen, `README.md` is the only place that must always be true about the *present* state. Keep it accurate.

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
- [ ] This stage's `BUILD<n>.md` exists, and its append-only `Stage Outcome` block records what was actually built, verified, and cut. Earlier build documents untouched.
- [ ] `README.md` still describes the current run commands and feature set accurately.
- [ ] No secrets, no dependency directories, no build caches staged.
- [ ] Green checkpoint committed (P4).
- [ ] Honest status report using P8 labels, including known limitations.
