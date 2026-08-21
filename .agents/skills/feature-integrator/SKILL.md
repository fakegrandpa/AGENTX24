---
name: feature-integrator
description: >-
  Integrate a newly announced requirement into the existing AGENTX24 project without breaking what
  already works: parse the requirement, inspect the current code, map affected files and regression
  risks, pick the smallest reliable integration strategy that reuses existing architecture, implement
  incrementally, verify new plus affected old behaviour, update BUILD.md only on real architectural
  change, and checkpoint. Use at every 3-hour requirement drop (Stage 1+).
---

# Feature Integrator

The most-used skill of the hackathon. Read `AGENTS.md` and `BUILD.md` before touching code.

**Framing that governs everything below:** this is an *addition to a living system*, not a new build. The existing stack, structure, and conventions are fixed inputs. Your job is the smallest correct extension of them.

Follow the P6 cycle budget: ~15 min plan, ~90 min implement, ~25 min verify, freeze the last 20 min.

---

## Step 1 — Parse the requirement literally (5 min)

Write out:
- **Demanded:** what the requirement explicitly says must exist. Quote key phrases.
- **Acceptance test:** the observable check that proves it, phrased like `BUILD.md` §8 — "Given X, do Y, see Z."
- **Boundaries:** what it does *not* ask for. Everything adjacent that you are tempted to add goes here.
- **Interpretation:** if wording is ambiguous, choose the reading that is cheapest to implement and easiest to extend, state it, and proceed (P7 only if the ambiguity changes the design).

If the requirement seems to demand replacing the current architecture, re-read it. Usually it demands new *behaviour*, not a new *foundation*. Escalate (P7) only if replacement is truly unavoidable, with a cost estimate and a fallback.

## Step 2 — Inspect before editing (5 min, P1)

- Re-read `BUILD.md` §5 architecture map, §6 data shapes, §7 extension seams.
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

## Step 5 — Implement incrementally

- Work in small verifiable steps; keep the project runnable between steps (never leave it mid-refactor at a stage boundary).
- Follow existing naming, file layout, error handling, and styling conventions. Consistency beats your preferred style.
- Reuse existing helpers, components, and utilities rather than adding parallel ones.
- New dependency? Only if it clearly saves significant time, is a well-known maintained package, and is pinned to an exact version. Otherwise implement the small thing directly. Never add a framework to solve a function-sized problem.
- Touch only the files in your map. If you discover an unrelated defect, note it in `BUILD.md` §12 and keep going — do not fix it in this diff unless it blocks the requirement.
- If you are 60% through the implementation budget and not close, cut to the minimum satisfying version, note what was cut in `BUILD.md` §2, and finish (P6).

## Step 6 — Verify new and old (P3)

1. Build/compile/typecheck.
2. Start the app or run the entry point clean.
3. Execute the Step 1 acceptance test; observe the expected result.
4. Execute the `BUILD.md` §8 core flow — it must still pass.
5. Execute each item from the Step 3 at-risk list.
6. Check for new errors in logs/console, and for stale stored data that no longer loads.

If the at-risk surface is broad, or something failed and the cause is unclear, hand to `regression-guardian` rather than improvising a wider sweep here.

## Step 7 — Document and checkpoint

- `BUILD.md` §11 stage log: always append one line.
- `BUILD.md` §5/§6/§7: update **only** if the architecture map, a data shape, or a seam actually changed.
- `BUILD.md` §3: append a decision line only for a real, consequential choice.
- `BUILD.md` §12: record anything partial, degraded, or cut.
- Green checkpoint (P4): `stage-<N>: <feature> — <what now works>`.

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

## Definition of done

- [ ] Requirement restated with an explicit acceptance test.
- [ ] Existing code inspected; touch/add/reuse/at-risk map written before editing.
- [ ] Smallest viable strategy chosen; existing architecture reused.
- [ ] Only mapped files changed.
- [ ] Acceptance test observed passing.
- [ ] Core flow and every at-risk item re-verified.
- [ ] `BUILD.md` stage log updated; blueprint updated only on real change.
- [ ] Green checkpoint committed.
- [ ] Report: what was added, what was verified, what was cut or is unverified (P8).

## Handoff

→ `regression-guardian` for the verification sweep, then `submission-manager` before the deadline. If the project goes RED at any point → `emergency-recovery` immediately.
