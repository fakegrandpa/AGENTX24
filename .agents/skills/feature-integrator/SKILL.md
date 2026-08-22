---
name: feature-integrator
description: >-
  Integrate a newly announced requirement into the existing AGENTX24 project without breaking what
  already works: read the build-document history, inspect the current code, create the next sequential
  BUILD[n].md stage record, map affected files and regression risks, pick the smallest reliable
  integration strategy that reuses existing architecture, implement incrementally, verify new plus
  affected old behaviour, and checkpoint. Use at every 3-hour requirement drop (Stage 1+).
---

# Feature Integrator

The most-used skill of the hackathon. Read `AGENTS.md` (including P9 on numbered immutable build documents) before touching code.

**Framing that governs everything below:** this is an *addition to a living system*, not a new build. The existing stack, structure, and conventions are fixed inputs. Your job is the smallest correct extension of them.

**The codebase is the source of truth, not the documents.** Build documents record what was *intended* at each stage; only the code says what exists. Where they disagree, trust the code and report the discrepancy.

Follow the P6 cycle budget: ~15 min plan, ~90 min implement, ~25 min verify, freeze the last 20 min.

---

## Step 0 — Locate yourself in the build history (2 min)

- List `BUILD*.md` in the workspace root. Note the highest existing number N; this stage will create `BUILD<N+1>.md`. Never write to an existing number (P9).
- Read `BUILD1.md` for the original architecture, scope, and `Core Flow Test`.
- Read the most recent one or two stage documents for current intent and any `Stage Outcome` blocks.
- Skim earlier stage documents only for decisions that bear on this requirement. Do not read all of them in full — that is not a good use of the clock.

## Step 1 — Parse the requirement literally (5 min)

Write out:
- **Demanded:** what the requirement explicitly says must exist. Quote key phrases.
- **Acceptance test:** the observable check that proves it, phrased like the `Core Flow Test` in `BUILD1.md` — "Given X, do Y, see Z."
- **Boundaries:** what it does *not* ask for. Everything adjacent that you are tempted to add goes here.
- **Interpretation:** if wording is ambiguous, choose the reading that is cheapest to implement and easiest to extend, state it, and proceed (P7 only if the ambiguity changes the design).

If the requirement seems to demand replacing the current architecture, re-read it. Usually it demands new *behaviour*, not a new *foundation*. Escalate (P7) only if replacement is truly unavoidable, with a cost estimate and a fallback.

## Step 2 — Inspect the actual code before editing (5 min, P1)

- Verify against the code what the build documents claim: the real file layout, the real data shapes, the seams that actually exist.
- List the tree and read the files you expect to touch.
- Search for the domain nouns/verbs in the requirement to find where related logic already lives — the feature is often 70% present under a different name.
- Identify the existing pattern for this class of change (how the last route/view/handler/command/model was added) and plan to follow it.

Produce a short written map — this is your P2 diff surface, and you are accountable to it:

```
Requirement: <one line>
Touch:    <file> — <what changes>
Add:      <new file> — <why an existing file was not the right home>
Reuse:    <existing helper/pattern/component being reused>
At risk:  <existing behaviour that shares this code path>
```

## Step 3 — Regression risk assessment (2 min)

Flag anything that is shared, and therefore risky:
- Shared data shapes, schemas, or stored data — does existing data still load?
- Shared entry points, routes, or state — does the old path still work?
- Signature changes to functions with multiple callers — did you update all of them?
- Config, dependency, or version changes — does a clean setup still work?
- Global styling/layout edits — did other views shift?

This list becomes the regression scope for `regression-guardian`.

## Step 4 — Choose the integration strategy (3 min)

Pick the cheapest option that fully satisfies the acceptance test:

| Signal | Strategy |
|---|---|
| Behaviour is additive and nothing shared changes | **Add alongside** — new file/function/view, wire it into an existing seam |
| Existing code does almost this | **Extend in place** — add a parameter, branch, field, or case |
| Two features now need the same logic | **Extract once, then reuse** — pull out the shared piece with no extra abstraction |
| Existing structure genuinely blocks the requirement | **Localized reshape** — change the smallest unit that unblocks it, keep the public behaviour of neighbours |
| Requirement is large | **Slice it** — ship the smallest end-to-end version first, verify, commit, then deepen |

Additive extension is the default; a reshape needs a stated reason. Extract only on the *second* real use, never in anticipation of one.

## Step 5 — Write BUILD<N+1>.md before implementing (3 min)

Create the stage record now, while the analysis is fresh and before any code changes. Use the number established in Step 0. Keep it tight — bullets, no essays:

```
# BUILD<n>.md — Stage <n> — <feature name>

## Requirement              (exact wording as announced, quoted)
## Acceptance Test          ("Given X, do Y, see Z")
## What Already Exists      (verified against the code, not the documents)
## Relevant Prior Context   (decisions from earlier BUILD files that constrain this)
## Affected Files & Components   (the Touch / Add / Reuse map)
## Integration Strategy     (chosen option + why the cheaper ones were rejected)
## Regression Risks         (each with how it will be checked)
## Implementation Plan      (numbered, each step independently verifiable)
## Architectural Decisions This Stage   (only real ones; "none" is a valid answer)
## Must Remain Unchanged    (working behaviour and files this stage must not disturb)
## Scope Cut Line           (minimum version if the clock runs out)
## Stage Outcome            (empty heading; appended after verification)
```

Do not touch `BUILD1.md` or any earlier stage document while doing this (P9).

## Step 6 — Implement incrementally

- Work in small verifiable steps; keep the project runnable between steps (never leave it mid-refactor at a stage boundary).
- Follow existing naming, file layout, error handling, and styling conventions. Consistency beats your preferred style.
- Reuse existing helpers, components, and utilities rather than adding parallel ones.
- New dependency? Only if it clearly saves significant time, is a well-known maintained package, and is pinned to an exact version. Otherwise implement the small thing directly. Never add a framework to solve a function-sized problem.
- Touch only the files in your map, and respect this stage's `Must Remain Unchanged` list. If you discover an unrelated defect, note it for the `Stage Outcome` block and keep going — do not fix it in this diff unless it blocks the requirement.
- If you are 60% through the implementation budget and not close, fall back to the `Scope Cut Line`, and record what was cut (P6).

## Step 7 — Verify new and old (P3)

1. Build/compile/typecheck.
2. Start the app or run the entry point clean.
3. Execute this stage's `Acceptance Test`; observe the expected result.
4. Execute the `Core Flow Test` from `BUILD1.md` — it must still pass.
5. Execute each item from the `Regression Risks` list.
6. Check for new errors in logs/console, and for stale stored data that no longer loads.

If the at-risk surface is broad, or something failed and the cause is unclear, hand to `regression-guardian` rather than improvising a wider sweep here.

## Step 8 — Document and checkpoint

- **Append** to this stage's `BUILD<n>.md` → `Stage Outcome`: what was actually built, what was verified and how, what was cut or deferred, any deviation from the plan and why, and new known limitations. Leave the planning sections above it as written.
- Update `README.md` if the run commands or the user-visible feature set changed — it is the only always-current document.
- Do **not** edit `BUILD1.md` or earlier stage documents. If an earlier document is now factually wrong about the code, append a one-line `[correction]` note there and say so in your report; never rewrite it.
- Green checkpoint (P4): `stage-<n>: <feature> — <what now works>`.

---

## Anti-patterns

Hard prohibitions — each of these has lost hackathons:

- **Rebuilding the app** or re-scaffolding because the new requirement "feels like a different project".
- **Swapping the stack, framework, or library** because you would have chosen differently at Hour 0.
- **Rewriting working code** that the requirement did not touch, for style, structure, or cleanliness.
- **Drive-by edits** to unrelated files in the same diff.
- **Scope inflation:** adding auth, roles, settings pages, dashboards, exports, or "while I'm here" features nobody asked for.
- **Heavy dependencies** for narrow needs; unpinned versions; unfamiliar packages with typo-like names.
- **Speculative abstraction** for the next unknown requirement — you will guess wrong, and the abstraction will cost more than the eventual edit.
- **Breaking old behaviour** to make new behaviour simpler, without saying so.
- **Committing unverified work** or reporting success from code alone.
- **Starting to code before inspecting** the files you are about to change.
- **Trusting a build document over the code** — plan from what exists, not from what an old file claims.
- **Overwriting, renaming, deleting, or rewriting an existing `BUILD<n>.md`**, reviving a single mutable `BUILD.md`, or creating `BUILD-LAST.md` during a normal feature cycle.

## Definition of done

- [ ] Highest existing `BUILD<n>.md` identified; the next sequential number created, nothing overwritten.
- [ ] Requirement restated with an explicit acceptance test.
- [ ] Actual code inspected; touch/add/reuse/at-risk map written before editing.
- [ ] Smallest viable strategy chosen; existing architecture reused.
- [ ] `BUILD<n>.md` stage record written before implementation began.
- [ ] Only mapped files changed; the `Must Remain Unchanged` list respected.
- [ ] Acceptance test observed passing.
- [ ] `BUILD1.md` core flow and every regression-risk item re-verified.
- [ ] `Stage Outcome` appended to this stage's document; earlier documents untouched; `README.md` still accurate.
- [ ] Green checkpoint committed.
- [ ] Report: what was added, what was verified, what was cut or is unverified (P8).

## Handoff

→ `regression-guardian` for the verification sweep, then `submission-manager` before the deadline. If the project goes RED at any point → `emergency-recovery` immediately.
