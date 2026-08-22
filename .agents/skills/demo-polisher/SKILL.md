---
name: demo-polisher
description: >-
  Make an already-working project immediately understandable and convincing: visual consistency,
  obvious primary action, loading/error/empty states, realistic seed data, a rehearsed demo path, and a
  demo script recorded in the current stage's build document. Highest visible impact for lowest
  technical risk. Use only when the project is GREEN and time remains before a demo. Never use to fix
  broken functionality.
---

# Demo Polisher

Read `AGENTS.md` (including P9 on numbered immutable build documents). Precondition: the project is **GREEN**. If it is YELLOW or RED, stop and use `regression-guardian` or `emergency-recovery` instead — polish on a broken project is wasted work.

For context, read `BUILD1.md` → `Problem & Primary Journey` and `Core Flow Test`, plus the newest `BUILD<n>.md` to know which features exist and what must remain unchanged. Then judge the app by **what it actually does when you run it**, not by what any document says. Do not assume an older document still matches the UI.

Judges score what they can see and understand in a few minutes. This skill improves comprehension and perceived quality **without touching business logic**.

Time box: work in 10-minute slices, verifying after each. Stop whenever the remaining time is needed for submission.

---

## Step 1 — Watch the demo as a stranger (5 min)

Run the app and walk the primary journey while asking:
- Within 5 seconds, is it obvious what this does and what to click or run first?
- Is the main value visible on the first screen/output, or buried behind navigation?
- Does anything look unfinished: placeholder text, lorem ipsum, dead links, debug output, misaligned elements, default framework branding, console errors?
- Does a slow operation look frozen?
- Does an error or an empty result look like a crash?
- Is there data present, or must a judge type input before seeing anything work?

Write the issues down and rank them by **(visible impact) ÷ (risk of breaking something)**. Fix in that order. Do not attempt the whole list.

## Step 2 — The high-value fixes, in order

1. **Frame the value.** A clear title, one-line description of what the project does, and a visible primary action. This is usually the single highest-return change.
2. **Seed data.** A prefilled example, sample dataset, or one-click demo input so the flow can be shown instantly and reliably. Label it as sample data; never present canned output as computed output.
3. **Empty states.** Replace blank areas with a short line saying what will appear and how to make it appear.
4. **Loading states.** Any operation over ~300ms gets a spinner, progress text, or disabled-button feedback. Prevents the "is it broken?" moment.
5. **Error states.** Replace raw stack traces and silent failures with a plain-language message and a recovery hint. Keep the technical detail in logs.
6. **Consistency pass.** Unify spacing, alignment, typography scale, colours, button styles, and terminology. Consistency reads as quality more than novelty does.
7. **Remove noise.** Delete debug prints, unused controls, unreachable views, and half-built features that will invite questions. Removal is often the cheapest polish.
8. **Accessibility basics that are also quality signals.** Readable contrast, labelled controls, focus visibility, sensible headings, keyboard-usable primary flow.
9. **Naming.** Labels and messages in domain language, not internal identifiers.

For non-visual deliverables (CLI, API, pipeline, service), the equivalents are: helpful `--help` output, clear progress logging, human-readable success/error output, a sample request/dataset, and a one-command demo path.

## Step 3 — AI/agent claims (only if genuinely present)

If the project genuinely uses AI or agentic behaviour, make it legible: show the input, the intermediate reasoning or steps if meaningful, and the output; surface which model/tool ran; make it observable rather than magic.

If it does not, **add nothing**. No fake "AI-powered" labels, no simulated thinking animations, no invented confidence scores, no mock agent logs. Fabricated capability is the fastest way to lose credibility under questioning, and judges probe exactly there.

## Step 4 — Rehearse and write the demo script

Run the demo path end to end at least once, exactly as it will be presented, and time it.

Append a `Demo Script` block to the **current** stage's `BUILD<n>.md` (the highest-numbered one), inside or directly after its `Stage Outcome` section. Do not edit earlier documents.

```
## Demo Script
Setup:      <commands to have it running, plus any prerequisites>
Reset:      <how to get back to a clean demo state>
Path:       1. <action> → <what the judge sees>
            2. ...
Talk track: <the one-sentence value proposition>
Avoid:      <known-fragile areas not to click during the demo>
Fallback:   <what to do if a live step fails: prepared data, screenshot, second path>
```

If the polish changed how the app is started or presented, update `README.md` too.

## Step 5 — Verify and checkpoint

Re-run P3 verification: build, start, the `BUILD1.md` core flow, plus every screen or output you touched. Cosmetic changes break layouts and bindings more often than expected — verify, do not assume. Then green checkpoint (P4): `polish: <what improved>`.

---

## Anti-patterns

- Polishing a project that is not green.
- Touching business logic, data shapes, or core algorithms "while in there".
- A full redesign, design-system migration, or component-library swap late in the event.
- Adding animations, 3D, or heavy assets that risk performance or break the flow.
- Introducing a UI framework or theme system at this stage.
- Fake functionality: mock data presented as real, buttons that do nothing, claimed features that do not exist.
- Trading reliability for visual flair.
- Polishing screens that are not part of the demo path.
- Continuing to polish through the submission window.
- Working from an outdated build document instead of the running application.
- Editing earlier `BUILD<n>.md` files, or reviving a single mutable `BUILD.md`.

## Definition of done

- [ ] Project was GREEN before starting and is GREEN after.
- [ ] Value proposition and primary action are obvious on first contact.
- [ ] Loading, error, and empty states exist wherever the demo can hit them.
- [ ] Seed/sample data makes the flow demoable in seconds, labelled honestly.
- [ ] Visual/terminology consistency pass done on demo-path screens.
- [ ] No fake or misleading capability added.
- [ ] Demo path rehearsed and timed; `Demo Script` appended to the current stage's document with a fallback.
- [ ] All touched surfaces re-verified; green checkpoint committed.

## Handoff

→ `submission-manager` for the final package.
