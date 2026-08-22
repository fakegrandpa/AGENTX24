---
name: hackathon-architect
description: >-
  Turn a freshly revealed hackathon problem statement into an actionable plan: mandatory vs optional
  requirements, hidden assumptions, likely judging priorities, the fastest appropriate stack, the
  smallest complete end-to-end MVP, real risks, minimal extension points, a build order, and an
  explicit not-yet list. Creates BUILD1.md, the frozen Hour 0 architecture record. Use at Hour 0, or
  when a later requirement genuinely forces an architectural decision. Do not use for routine feature
  work.
---

# Hackathon Architect

Read `AGENTS.md` first, including protocol P9 on numbered immutable build documents. This skill produces a **plan and `BUILD1.md`**, not code.

**Hard rule: write zero application code in this skill.** The only file you may create or edit is `BUILD1.md` (and `.gitignore` if absent).

Time box: **20 minutes** for the analysis, **25 max**. If you exceed it, ship the plan as-is and start building.

---

## Step 1 — Requirement extraction (5 min)

Re-read the problem statement literally and split it into four buckets. Quote the source wording where it decides something.

| Bucket | Meaning |
|---|---|
| **MUST** | Explicitly demanded, or the deliverable is incomplete without it |
| **SHOULD** | Stated as desirable, or clearly implied by the domain |
| **NICE** | Would impress, costs little, is not required |
| **OUT** | Tempting, unstated, expensive → explicitly excluded for now |

Then list:
- **Actors** — who uses this, and in what role.
- **Primary journey** — the single path from trigger → processing → visible result. One sentence.
- **Deliverable form** — what is actually submitted and demoed (running app, CLI, API + client, dashboard, pipeline, notebook, device, something else).
- **Hard constraints** — offline/online, data provided or synthetic, required platform, judged environment, mandated tools.

## Step 2 — Hidden assumptions and ambiguity (3 min)

Write down every assumption the statement leaves open that would change the design: data source and volume, auth needs, multi-user vs single-user, persistence vs in-memory, real-time vs batch, accuracy bar, external service availability.

For each: state the assumption you will proceed with and pick the option that is **cheapest to reverse later**. Surface only genuinely blocking ambiguity to the user (P7); do not stall on the rest.

## Step 3 — Judging priorities (2 min)

Infer, marked as inference, not fact: what the problem statement rewards (working core flow, correctness, breadth of features, UX, novelty, technical depth, presentation). Note that requirements arrive every 3 hours, so **integration-friendliness and never being broken are themselves scored in practice.**

## Step 4 — Stack decision (5 min)

Choose the stack that gets a **complete vertical slice running fastest with acceptable risk**. Criteria in order:
1. Team/agent fluency and availability of a known-good scaffold.
2. Time to first running end-to-end flow.
3. Fit for the deliverable form and constraints.
4. Ability to absorb unknown features without re-platforming.
5. Setup risk: installs, native builds, credentials, quotas, GPU, licenses.

Record for each significant choice: **decision — one-line reason — cheaper alternative rejected and why.**

Also decide and record now:
- Exact run command(s) and the dev entry point.
- Persistence: none / file / embedded store / server store — start at the weakest option that satisfies MUST.
- Where configuration and secrets live (env file, ignored; example file, committed).
- One dependency budget rule: any dependency larger than a single-purpose library needs a written reason.

**Reject on sight, unless a MUST requirement literally demands it:**
- Microservices, message queues, containers, orchestration, or a reverse proxy for a 24-hour single-app build.
- Multi-agent frameworks, vector databases, or an orchestration layer when one direct call would do.
- A stack chosen for résumé value or novelty rather than delivery speed.
- Auth, roles, migrations, i18n, or multi-tenancy that nobody asked for.
- A monorepo, plugin system, or configurable "engine" for one concrete use case.
- Custom implementations of solved problems (routing, parsing, auth, charts, HTTP) instead of a proven library.

## Step 5 — Smallest complete MVP (3 min)

Define the vertical slice: the thinnest path that a judge can watch work end to end, covering the primary journey and nothing else. If any listed item can be removed while the journey still demonstrates the solution, remove it.

State the MVP's **observable success test** in one sentence: "Given X, the user does Y, and Z is visibly produced." This becomes the `Core Flow Test` section of `BUILD1.md`, and `mvp-builder`, `feature-integrator`, and `regression-guardian` reuse that exact sentence as the baseline regression check for the rest of the event.

## Step 6 — Extension points, only where earned (2 min)

Unknown features are coming. Buy flexibility **only** where it is nearly free:
- Keep the core operation callable from more than one entry point (e.g. logic separated from its trigger/UI).
- Keep the data shape in one place so a field can be added in one edit.
- Keep the display layer thin so a new view is additive.
- Name things after the domain, not the current feature.

That is the whole list. Do not add plugin registries, event buses, strategy interfaces, or abstract base classes on speculation. Note in `BUILD1.md`: *"Flexibility is bought by small files and clear seams, not by abstractions."*

## Step 7 — Risks (2 min)

For each real risk: likelihood, impact, and a **pre-decided fallback** (e.g. "if the external API needs a paid key → ship with a local fixture behind the same function"). Highest-value output of this step is the fallback, not the warning.

## Step 8 — Write BUILD1.md

Confirm no `BUILD1.md` already exists (P9 numbering). If one does, you are not at Hour 0 — stop and report; a later stage belongs to `feature-integrator`, which creates the next sequential number.

Create `BUILD1.md` with exactly these sections (concise; bullets over prose):

```
# BUILD1.md — <project name> — Hour 0 architecture record

## Problem & Primary Journey
## Scope: MUST / SHOULD / NICE / NOT YET
## Stack & Key Decisions        (decision — reason — rejected alternative)
## How to Run                   (setup, run, verify commands as planned)
## Architecture                 (what each planned file/module owns)
## Data Shapes                  (the few structures that matter)
## Extension Seams              (where future features are expected to attach)
## Core Flow Test               (the observable success sentence — the baseline
                                 regression check for the whole hackathon)
## Build Order                  (numbered, each step independently verifiable)
## Risks & Fallbacks
## Not To Be Built Yet          (explicit)
## Stage Outcome                (empty heading; mvp-builder appends here)
```

This document is the frozen Hour 0 record. Once written, do not rewrite its planning sections — later stages get their own numbered documents, and the executing skills append only under `Stage Outcome`.

Keep it short enough that any agent can read it fully at the start of any stage.

### If asked for the final summary (BUILD-LAST.md)

Only near the final stage, and only when asked, produce `BUILD-LAST.md`: a compact final system map built from all `BUILD<n>.md` files, the **current actual codebase** (the authority), and current Git state. Cover final purpose, final architecture, the complete implemented feature set, major decisions, known limitations, and the demo flow. Verify every claim against the code — do not copy stale intentions forward. It must not replace, delete, or edit any numbered build document. Do not create it during normal feature cycles.

---

## Anti-patterns

- Writing application code, scaffolding, or installing dependencies in this skill.
- Producing a plan longer than the MVP it describes.
- Designing for features that have not been announced.
- Diagramming, layering, or naming patterns instead of deciding what to build first.
- Restating the problem statement back without decisions.
- Leaving the stack "to be decided" — the next skill cannot start without it.
- Creating a mutable `BUILD.md`, overwriting an existing numbered document, or creating `BUILD-LAST.md` early.

## Definition of done

- [ ] MUST/SHOULD/NICE/NOT-YET buckets written, with an explicit **not yet** list.
- [ ] Stack decided, with run command and persistence choice named.
- [ ] Vertical-slice MVP defined with a single observable success sentence.
- [ ] Risks each have a fallback.
- [ ] Numbered build order where every step is independently verifiable.
- [ ] `BUILD1.md` written, no pre-existing build document touched, and no application code created.
- [ ] User shown the plan and the not-yet list before implementation starts.

## Handoff

→ `mvp-builder`, using the `Build Order` section of `BUILD1.md`.
