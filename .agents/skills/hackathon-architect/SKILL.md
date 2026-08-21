---
name: hackathon-architect
description: >-
  Turn a freshly revealed hackathon problem statement into an actionable plan: mandatory vs optional
  requirements, hidden assumptions, likely judging priorities, the fastest appropriate stack, the
  smallest complete end-to-end MVP, real risks, minimal extension points, a build order, and an
  explicit not-yet list. Writes or updates BUILD.md. Use at Hour 0, or when a later requirement
  genuinely forces an architectural decision. Do not use for routine feature work.
---

# Hackathon Architect

Read `AGENTS.md` first. This skill produces a **plan and `BUILD.md`**, not code.

**Hard rule: write zero application code in this skill.** The only file you may create or edit is `BUILD.md` (and `.gitignore` if absent).

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

State the MVP's **observable success test** in one sentence: "Given X, the user does Y, and Z is visibly produced." `mvp-builder` and `regression-guardian` will reuse this exact sentence as the core flow test.

## Step 6 — Extension points, only where earned (2 min)

Unknown features are coming. Buy flexibility **only** where it is nearly free:
- Keep the core operation callable from more than one entry point (e.g. logic separated from its trigger/UI).
- Keep the data shape in one place so a field can be added in one edit.
- Keep the display layer thin so a new view is additive.
- Name things after the domain, not the current feature.

That is the whole list. Do not add plugin registries, event buses, strategy interfaces, or abstract base classes on speculation. Note in `BUILD.md`: *"Flexibility is bought by small files and clear seams, not by abstractions."*

## Step 7 — Risks (2 min)

For each real risk: likelihood, impact, and a **pre-decided fallback** (e.g. "if the external API needs a paid key → ship with a local fixture behind the same function"). Highest-value output of this step is the fallback, not the warning.

## Step 8 — Write BUILD.md

Create `BUILD.md` with exactly these sections (concise; bullets over prose):

```
# BUILD.md — <project name>
## 1. Problem & Primary Journey
## 2. Scope: MUST / SHOULD / NICE / NOT YET
## 3. Stack & Key Decisions   (decision — reason — rejected alternative)
## 4. How to Run             (setup, run, verify commands)
## 5. Architecture Map       (what each file/module owns; kept current)
## 6. Data Shapes            (the few structures that matter)
## 7. Extension Seams        (where new features are expected to attach)
## 8. Core Flow Test         (the observable success sentence)
## 9. Build Order            (numbered, each step independently verifiable)
## 10. Risks & Fallbacks
## 11. Stage Log             (one line per stage: what was added, status)
## 12. Known Limitations
## 13. Demo Script           (filled in later by demo-polisher)
```

Keep it short enough that any agent can read it fully at the start of every stage.

---

## Anti-patterns

- Writing application code, scaffolding, or installing dependencies in this skill.
- Producing a plan longer than the MVP it describes.
- Designing for features that have not been announced.
- Diagramming, layering, or naming patterns instead of deciding what to build first.
- Restating the problem statement back without decisions.
- Leaving the stack "to be decided" — the next skill cannot start without it.

## Definition of done

- [ ] MUST/SHOULD/NICE/NOT-YET buckets written, with an explicit **not yet** list.
- [ ] Stack decided, with run command and persistence choice named.
- [ ] Vertical-slice MVP defined with a single observable success sentence.
- [ ] Risks each have a fallback.
- [ ] Numbered build order where every step is independently verifiable.
- [ ] `BUILD.md` written; no application code created.
- [ ] User shown the plan and the not-yet list before implementation starts.

## Handoff

→ `mvp-builder`, using `BUILD.md` §9 build order.
