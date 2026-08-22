# BUILD3.md — Stage 2 — Autonomous Intelligence Office (living workflow visualization)

Stage record created under AGENTS.md P9. Planning sections are frozen once written; only `Stage Outcome` is appended after implementation. `BUILD1.md` and `BUILD2.md` are untouched.

**Baseline for this stage:** commit `a75ede4` — `v2: stable baseline before UI redesign` (local `main`, working tree clean, `origin/main` at `da665b4` and therefore *behind* local — nothing about this stage may be pushed).

---

## Requirement

Transform the frontend into a **living, interactive AI office** that visualizes the *existing* autonomous system. One Manager (the real agent loop) and ~7 worker positions. Quoted constraints that decide the design:

> "The UI MUST NOT pre-script these actions. The backend event stream must control them."
>
> "If the agent calls research_search twice, the Research Worker should visibly perform work twice… If a tool is never called, that Worker remains idle."
>
> "Do not redesign the backend into a multi-agent architecture just because the UI looks like multiple agents… The UI may PERSONIFY real tools and pipeline stages as office workers. But the architecture must remain technically honest."
>
> "DO NOT falsely claim that an internal stage is an independently autonomous agent if it is not."
>
> "If SVG + CSS + JavaScript provides a better balance than Three.js… prefer the simpler approach." · "Do not build a full game engine for a workflow visualization."
>
> "Do not remove the ability to inspect the actual results." · "Respect accessibility and reduced-motion preferences."

**Non-goals (explicit).** No multi-agent backend. No new external tools or data sources. No 3D engine, game loop, physics, sprite sheets, or asset pipeline. No React/Vue/Tailwind/npm/bundler. No new dependency of any kind. No database, persistence, auth, run history, or export. No charts, KPI cards, or dashboard metrics. No changes to the agent loop, prompt, tool registry, provider adapters, report assembly, budgets, or the four API endpoints. No fake progress percentages, no simulated tool latency, no invented worker chatter, no pixel-art or cartoon mascots, no neon/HUD/glassmorphism. No pushing to GitHub.

---

## Acceptance Test

**Given** the server running with a valid `GEMINI_API_KEY`, **when** a judge submits `Quantum error correction patent landscape` from the office screen, **then** the Manager visibly receives the task, and **only** the workers whose tools the backend actually called leave their desks — each carrying the real `data.query` and `data.reason` from its `tool_selected` event — remain in a working state for exactly as long as the real tool call takes, return with a packet count equal to the real `data.new_evidence`, and the back-office stages activate only on the real synthesis events; every worker whose tool was never called stays idle for the entire run; and the final report renders with the same content and clickable evidence-derived sources as the V2 baseline.

---

## What Already Exists (verified against the code at `a75ede4`)

Inspected: `app/agent.py`, `app/llm.py`, `app/models.py`, `app/tools/__init__.py`, `app/tools/{news,research,web,patents}.py`, `app/report.py`, `app/main.py`, `app/store.py`, `web/{index.html,app.css,app.js}`, git history.

### Architecture, as it actually is

```
browser --POST /api/investigate {query}--> main.py::api_investigate
                                            store.create_run() -> Run(id, status="running")
                                            BackgroundTasks -> _execute_investigation_background (threadpool)
                                                                 |
                                          agent.py::run_investigation(objective, emit_callback)
                                            emit() closure -> Run.telemetry.append + store.broadcast_event
                                                                 |
browser --GET /api/stream/{run_id} (SSE)--  main.py::api_stream
                                            replays Run.telemetry, then asyncio.Queue frames,
                                            terminated by {"event":"stream_end"}
browser --GET /api/run/{run_id}----------->  full Run JSON (telemetry, evidence, tool_calls, report)
```

- **One real reasoning entity.** `agent.py::run_investigation` is a single ReAct loop calling `llm.py::propose_next_step` (Gemini `generate_content` + `types.Tool(function_declarations=…)`). Budgets: `MAX_ITERATIONS=8`, `MAX_TOOL_CALLS=12`, `WALL_CLOCK=120s`, `TOOL_TIMEOUT=15s`. **There is no orchestrator, no sub-agent, no planner/executor split.** Anything the office shows as a "worker" is either a tool or a code stage.
- **Four real tools**, in `TOOL_REGISTRY` (`app/tools/__init__.py`), advertised via `get_advertised_tools()` (patents gated by `is_patent_tool_available()`): `news_search`, `research_search`, `web_search`, `patent_search`.
- **Real pipeline stages after the loop**, all inside `app/report.py::assemble_report`: `compute_corroboration()`, `extract_and_validate_citations()` (grouped-citation validation + model-URL scrub), `parse_signals_from_text()` (tier assignment from the model's own headings), section suppression, coverage build.
- **Static serving is route-by-route** (`main.py` lines 144–166): exactly `/`, `/app.css`, `/app.js`. **Any fourth asset 404s.** This single fact drives the file-layout decision below.
- **Current frontend** (`web/app.js`, 29.6 KB) already consumes the telemetry contract correctly: `openStream()` → `processTelemetryEvent()` → focus banner + numbered timeline nodes + evidence grid with `provider_kind` filters + report renderer with citation chips and provenance. It is a strong two-column workspace — **it is not the office, but its report and evidence layers are worth preserving wholesale.**

### Exact SSE event contract available today (`app/models.py::TelemetryEvent`)

`{seq: int, ts: iso8601, phase: PhaseEnum, kind: Literal[...], text: str, detail: str|null, data: dict|null}`

| `kind` | `phase` | `data` keys actually emitted | Emitted at (`agent.py`) |
|---|---|---|---|
| `objective` | Understanding the objective | `objective`, `available_tools[]` | ~line 109 |
| `planning` | Planning the next step | `step` | ~line 150 |
| `planning` | **Identifying knowledge gaps** | `step`, `next_tool`, `reason` | ~line 200 |
| `tool_selected` | Searching recent research / Checking recent industry developments / Searching the web / Searching patent records | `tool`, `args`, `query`, `reason`, `call_index` | ~line 209 |
| `tool_result` | Evidence found | `tool`, `new_evidence`, `total_evidence`, `ok` | ~line 261 |
| `note` | Source unavailable | `tool`, `ok:false`, `error`, `new_evidence:0` | ~line 276 |
| `note` | No results for that angle | `tool`, `ok:true`, `new_evidence:0` | ~line 291 |
| `error` | Error encountered | — | ~line 100 / 163 |
| `final` | Comparing and prioritising evidence | `evidence` | ~line 328 |
| `final` | Generating intelligence report | — | ~line 350 |
| `final` | Completed | `tool_calls`, `evidence`, `tools_used[]`, `signals` | ~line 377 |

**This is sufficient. No new event type and no payload change is required.** Two properties matter for the animation design:

1. `tool_selected` is emitted **immediately before** `execute_tool()` returns, and the matching `tool_result`/`note` arrives **after** it. The interval between them *is* the real tool duration — so a worker's "working" state must be an indefinite loop that ends only on the paired event. **No progress percentage may be shown, because the backend does not know one.**
2. Gemini can return **parallel** `function_call` parts, so several `tool_selected` events may arrive before any result. The office must support concurrently active workers and must pair events by `data.tool` + `data.call_index`.

### Existing frontend limitations for this requirement

- No spatial model at all: the timeline is a list, so "who did what, when" is legible but not *visible*.
- No entity identity — a second `research_search` call is just another row, not the same worker going out again.
- Idle capability is invisible: a judge cannot see that four sources were available and only two were used, which is precisely the proof of dynamic selection.
- The post-loop stages in `report.py` are completely unrepresented.
- One monolithic `app.js` with no state model between events and DOM, so adding a scene would tangle rendering with transport.

### Document drift to note

`BUILD1.md` → `Product & UI plan` and its decision #15 ("the visual system is Stage 0 scope… later stages must not replace it") no longer describe reality: the visual system has been replaced twice by explicit organizer instruction (Stage 1, then `da665b4`). Treat `BUILD2.md` → `Stage Outcome` plus the code as current truth. Also note `origin/main` (`da665b4`) is *ahead of nothing* — local `main` (`a75ede4`) is one commit ahead of the remote; do not "sync".

---

## Relevant Prior Context (binding constraints from earlier stages)

- Sources are rendered by application code from `Run.evidence` only; the model may never contribute a URL (`report.py::extract_and_validate_citations` strips them). **The office must not become a new path by which model text reaches the screen.**
- No chain-of-thought exposure. `data.reason` is a declared tool argument and is safe to display; `part.thought` content never leaves `llm.py`.
- Zero frontend dependencies, no build step, system font stack, one restrained accent, tokens declared once in CSS, `prefers-reduced-motion` honoured.
- `run_investigation(objective, emit_callback)` stays trigger-agnostic; the CLI (`python -m app.agent "<target>"`) must keep working.
- Known open item, unchanged: evidence is not de-duplicated across tool calls, so repeat calls can return overlapping articles. The office must therefore show *packet counts from `data.new_evidence`*, not claim uniqueness.

---

## Proposed Office Architecture

### Rendering technology — recommendation and reasoning

**Recommended: inline SVG scene + CSS custom-property transforms + a plain-JS state machine, with `requestAnimationFrame` used only while a figure is in transit.**

| Option | Verdict | Why |
|---|---|---|
| **SVG + CSS transforms** | **Chosen** | 8 entities is trivial for the DOM. Clicking a worker to inspect its evidence is free hit-testing; on canvas it is hand-written geometry. Each worker can be a real focusable element with `aria-label`, which the project's accessibility commitments require. CSS transitions are GPU-composited and are cancelled/retargeted for free when a new event lands mid-animation. `prefers-reduced-motion` already exists in `app.css` and disables everything in one rule. Zero bytes of dependency, no build step — matching the hard constraint. |
| Canvas 2D | Rejected | Requires a permanent render loop or manual dirty-tracking, custom hit-testing for worker clicks, and a parallel accessibility tree. Buys nothing at this entity count. |
| Three.js / WebGL | Rejected | ~600 KB plus a bundler, for eight figures that never rotate. Directly violates "do not build a full game engine" and the zero-dependency rule. |
| CSS-only (no SVG) | Rejected | Desks, floor, and travel paths are vector shapes; expressing them as divs makes the layout brittle and the path maths worse. |
| Lottie / animation lib | Rejected | New dependency; pre-baked timelines cannot be driven by unpredictable real event timing. |

**Perspective: orthographic top-down floor plan** (not isometric, not 3D). Isometric doubles the pathing maths and demands consistent light/shadow authoring for every prop; a clean top-down plan with soft drop shadows and slight desk "thickness" reads as premium, keeps travel paths to simple 2D polylines, and stays legible at 1280 px. The scene is a single `<svg viewBox="0 0 1200 700">` that scales with `width:100%; height:auto`.

**Worker visual language: abstract, not characters.** Each worker is a small group: a rounded-rect desk, a monitor rectangle whose fill changes with state, and the worker itself as a **capsule body + circle head** in a neutral tone with a single accent ring when active. No faces, no limbs, no bounce. This reads as a refined diagram that happens to move — the opposite of a mascot.

### File layout — one small backend change, with a zero-change fallback

`main.py` serves only three exact paths, so new files would 404. Two options:

- **Option A (recommended).** Add a static mount in `app/main.py` — the *only* backend change in this stage:
  ```python
  from fastapi.staticfiles import StaticFiles
  app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
  ```
  Keep the three existing routes exactly as they are so nothing breaks, and load new modules from `/static/…`. This unlocks:
  `web/office.js` (scene build + state machine), `web/office.css` (scene tokens + states), while `web/app.js` keeps transport, timeline, evidence, and report.
- **Option B (fallback, if any risk appears).** Put everything in the existing `web/app.js` and `web/app.css`. Zero backend change, larger files. This is the `Scope Cut Line` position.

### Layered design — the mapping layer is mandatory

```
SSE frame (TelemetryEvent JSON)
   |
   v
[ app.js  transport ]      openStream() — unchanged responsibilities
   |
   v
[ office.js  adapter ]     interpretEvent(ev) -> zero or more OfficeAction objects
   |                       PURE FUNCTION: no DOM, no timers, fully unit-testable
   v
[ office.js  store ]       OfficeState { manager, workers{7}, tasks[], packets[] }
   |                       reducer(state, action) -> state   (no animation logic)
   v
[ office.js  view ]        renderOffice(state) -> sets CSS custom properties and
                           data-state attributes on existing SVG nodes. Never rebuilds
                           the scene; animation is a consequence of state, never a
                           hand-rolled timeline.
```

Animations are **never** attached to arbitrary UI code. A worker's desk element carries `data-state="idle|assigned|outbound|working|inbound|reporting|empty|error"`; CSS owns every transition for that attribute; JS only sets the attribute and, for travel, drives a `--t` progress variable via rAF.

---

## Office Layout Specification

Single SVG, `viewBox="0 0 1200 700"`. Coordinates are authoritative so the implementer does not invent them.

```
+--------------------------------------------------------------------------+  y=0
|  MANAGER CABIN                        x 340..860, y 24..232              |
|  - cabin shell: rounded rect, --surface, 1px --line, soft shadow         |
|  - Manager figure at (600, 150); desk 520..680 x 168..212                |
|  - "CURRENT ASSIGNMENT" plate: 360..840 x 44..96  (the live objective)   |
|  - phase chip at (600, 116): manager state label, from real telemetry    |
|  - evidence tray at 700..840 x 150..212: fills as real evidence arrives  |
+--------------------------------------------------------------------------+
        corridor spine: horizontal y=290, vertical trunk x=600 (y 232..290)

   FIELD SOURCES  (Category A — one real external tool each)
   Desk 1 Research      centre (200, 400)   desk 120..280 x 372..428
   Desk 2 News          centre (450, 400)   desk 370..530 x 372..428
   Desk 3 Web           centre (750, 400)   desk 670..830 x 372..428
   Desk 4 Patents       centre (1000, 400)  desk 920..1080 x 372..428
        (each desk has a "field zone" 90px below it: y 470..520, where the
         worker stands while its real tool call is in flight)

   BACK OFFICE  (Category B — real post-loop code stages, visually distinct:
                 dashed desk outline + "STAGE" micro-badge, never called an agent)
   Desk 5 Evidence Verification   centre (330, 600)
   Desk 6 Signal Prioritization   centre (600, 600)
   Desk 7 Report Composition      centre (870, 600)
```

Category A desks sit on the upper floor and their workers physically leave to a field zone. Category B desks sit in a lower band, are visually dashed, never travel, and only light up during the real synthesis events. **A legend in the corner states plainly: "Field sources are real external APIs. Back office are stages of the report pipeline, not separate agents."** That single line is what keeps the metaphor honest.

Travel path for a Category A worker (polyline, no teleporting): `desk centre → (desk.x, 290) → (600, 290) → (600, 250)` to hand a packet to the Manager, and the reverse plus `→ field zone` on dispatch. Movement uses `translate()` along a precomputed polyline with eased progress; the path is derived from coordinates, so no hardcoded keyframes.

---

## Manager Design & State Machine

The Manager **is** the real Gemini loop — the one honest "agent" in the building.

| Manager state | Entered on | Visual |
|---|---|---|
| `idle` | initial / after `Completed` | dim cabin, slow monitor breathing (4s), phase chip "Standing by" |
| `receiving` | `kind:"objective"` | assignment plate types in the real objective; cabin lifts to full contrast; `available_tools[]` marks which desks are staffed vs greyed |
| `planning` | `kind:"planning"`, phase `Planning the next step` | monitor shows scanning sweep; chip "Planning step N" from `data.step` |
| `delegating` | `phase:"Identifying knowledge gaps"` | a packet forms at the cabin edge; chip shows the real `data.reason`, truncated with full text on hover |
| `awaiting` | ≥1 worker in `outbound`/`working` | steady, attentive; tray shows running total |
| `synthesizing` | `final` + `Comparing and prioritising evidence` | back-office band lifts; tray consolidates; chip "Prioritising N items" from `data.evidence` |
| `composing` | `final` + `Generating intelligence report` | Report Composition desk active; cabin monitor fills |
| `completed` | `final` + `Completed` | brief settle, then the report transition |
| `error` | `kind:"error"` | cabin border switches to `--danger`; chip carries the real `ev.detail` |

Clicking the Manager opens a **reasoning summary drawer** (progressive disclosure): current phase, objective, ordered list of every dispatch with its real query and reason, running evidence count. All values come from `state.events` — nothing generated.

---

## Worker Mapping to Real Capabilities

**Category A — directly mapped to a real external tool.** Activates *only* when a `tool_selected` event names it.

| Worker | Real tool | Real providers (verified) | Trigger |
|---|---|---|---|
| Research Intelligence | `research_search` | OpenAlex → arXiv (→ Semantic Scholar with key) | `data.tool === "research_search"` |
| News Intelligence | `news_search` | Google News RSS (→ NewsData.io with key) | `data.tool === "news_search"` |
| Web Intelligence | `web_search` | DDGS → Wikipedia API | `data.tool === "web_search"` |
| Patent Intelligence | `patent_search` | Google Patents (web-indexed) → EPO OPS with credentials | `data.tool === "patent_search"`; desk shown **unstaffed** if absent from `available_tools[]` |

**Category B — real pipeline stages, not autonomous agents.** Must be labelled "stage", drawn dashed, and never described as deciding anything.

| Position | Real code it represents | Trigger |
|---|---|---|
| Evidence Verification | `report.py::extract_and_validate_citations` + `compute_corroboration` — citation validation, unresolvable-marker stripping, model-URL scrub | `final` + `Comparing and prioritising evidence` |
| Signal Prioritization | `report.py::parse_signals_from_text` — tier extraction from the model's own headings | same event, staggered ~400 ms after Evidence Verification |
| Report Composition | `report.py::assemble_report` — section suppression, next actions, coverage assembly | `final` + `Generating intelligence report` |

Seven positions, all traceable to code. **No eighth invented worker. No worker for a capability that does not exist.**

### Worker state machine

`idle → assigned → outbound → working → inbound → reporting → idle`, with `empty` and `error` as alternative terminal-ish states that still return the worker to `idle`.

| State | Entered on | Exits on | Visual |
|---|---|---|---|
| `idle` | default | assignment | dim desk, monitor at 25%, 6s breathing; grey if tool not in `available_tools[]` |
| `assigned` | `tool_selected` for this tool | +300 ms | accent ring appears; query chip attaches to the worker |
| `outbound` | after `assigned` | path complete (~700 ms) | figure travels desk → corridor → field zone |
| `working` | arrival at field zone | **paired result event only** | indefinite: pulsing field marker, monitor sweep. Duration = real tool latency. No percentage, no ETA. |
| `inbound` | `tool_result` with `new_evidence > 0` | path complete | figure returns carrying N packet dots (capped at 8 glyphs, exact count as a numeral) |
| `reporting` | arrival at cabin | +500 ms | packets absorb into the Manager tray; tray counter increments to `data.total_evidence` |
| `empty` | `note` + `No results for that angle` | +900 ms | returns with **no** packet; a muted "0 results" plate at the desk |
| `error` | `note` + `Source unavailable` | +1200 ms | returns; desk border `--warn`; plate shows the real `data.error` |

**Repeat calls:** a worker already `idle` re-enters `assigned`; the desk keeps a visit counter badge (`×2`) driven by `data.call_index`. If a *new* `tool_selected` for the same tool arrives while that worker is still `working` (possible with parallel calls), queue it in `worker.queue[]` and show a stacked badge — never drop it, never fake a second figure.

### Task & evidence flow

```
TaskToken { id: `${tool}#${call_index}`, tool, query, reason, state }
  queued      -> tool_selected received, worker busy (queued behind current task)
  dispatched  -> worker assigned/outbound with this token
  executing   -> worker working; real call in flight
  returned    -> tool_result with new_evidence > 0
  empty       -> note / No results
  failed      -> note / Source unavailable
  absorbed    -> reporting complete; counter merged into Manager tray
```

Evidence packets are **counts and identities only** — the office never renders model prose. Full records stay in the existing evidence grid and Sources list, fetched from `GET /api/run/{run_id}` exactly as today.

---

## Backend Event → Office Action Mapping (implement literally)

`interpretEvent(ev, state)` is pure and returns an array of actions:

| Incoming | Actions |
|---|---|
| `kind:"objective"` | `MANAGER_RECEIVE{objective}`, `STAFF_DESKS{available_tools}` |
| `kind:"planning"`, phase `Planning the next step` | `MANAGER_PLAN{step}` |
| `kind:"planning"`, phase `Identifying knowledge gaps` | `MANAGER_DELEGATE{next_tool, reason}` |
| `kind:"tool_selected"` | `TASK_CREATE{id:tool#call_index, tool, query, reason}`, `WORKER_ASSIGN{tool, taskId}` |
| `kind:"tool_result"`, `data.new_evidence>0` | `TASK_RETURN{tool, count:new_evidence, total:total_evidence}`, `WORKER_INBOUND{tool}` |
| `kind:"note"`, phase `No results for that angle` | `TASK_EMPTY{tool}`, `WORKER_EMPTY{tool}` |
| `kind:"note"`, phase `Source unavailable` | `TASK_FAIL{tool, error}`, `WORKER_ERROR{tool}` |
| `kind:"error"` | `MANAGER_ERROR{detail}` |
| `final`, phase `Comparing and prioritising evidence` | `STAGE_ACTIVATE{verification}`, `STAGE_ACTIVATE{prioritization, delay:400}`, `MANAGER_SYNTHESIZE{evidence}` |
| `final`, phase `Generating intelligence report` | `STAGE_ACTIVATE{composition}`, `MANAGER_COMPOSE` |
| `final`, phase `Completed` | `OFFICE_SETTLE{tool_calls, evidence, tools_used, signals}`, `MANAGER_COMPLETE` |
| unknown `phase`/`kind` | **no action** — log once to console and ignore. Forward-compatible by design. |

**Replay safety.** `GET /api/stream/{run_id}` replays `Run.telemetry` on connect, so a page reload floods historical events. `interpretEvent` must be idempotent, and the office must **fast-forward**: if `state.hydrating` is true, apply reducer transitions with animations suppressed and settle into the correct final tableau. Never animate a stampede.

### Does SSE need changes? Do any backend changes?

**SSE: no changes.** Every field the office needs already exists; adding events would be unrequested scope and would break the "smallest reliable change" rule.

**Backend: exactly one optional line-level change** — the `StaticFiles` mount in `app/main.py` (Option A above), added *alongside* the three existing routes, which remain untouched. Nothing else in `app/` may be modified: not the loop, not the prompt, not the tools, not `report.py`, not `store.py`, not `config.py`, not `requirements.txt`.

---

## Frontend File-by-File Plan

| File | Action | Contents |
|---|---|---|
| `app/main.py` | **Touch (3 lines)** | import `StaticFiles`; `app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")`. Existing `/`, `/app.css`, `/app.js` routes unchanged. |
| `web/office.css` | **Add** | Scene tokens (floor, desk, figure, monitor, packet, stage-dash), all `[data-state="…"]` transitions, travel variables, `prefers-reduced-motion` block, responsive scene rules. Reuses the existing `:root` palette from `app.css` — **no new colour values.** |
| `web/office.js` | **Add** | `OFFICE_LAYOUT` (the coordinates above), `buildScene()` (creates the SVG once), `interpretEvent()` (pure), `reducer()`, `renderOffice()`, `travel()` (rAF polyline interpolation), `openManagerDrawer()`, `openWorkerDrawer(tool)`. Exposes `window.Office = { mount, handleEvent, hydrate, reset }`. No `fetch`, no `EventSource`. |
| `web/index.html` | **Touch** | Insert the office `<section>` (SVG host + legend + drawer containers) as the primary element of the run screen; keep the existing timeline and evidence columns beneath it as a collapsible "Detail" region; add `<link rel="stylesheet" href="/static/office.css">` and `<script src="/static/office.js">` before `app.js`. All existing IDs preserved. |
| `web/app.js` | **Touch (small, additive)** | In `startInvestigation()` → `Office.reset()`; in `openStream()`'s message handler → `Office.handleEvent(ev)` after the existing `processTelemetryEvent(ev)`; on replay detection → `Office.hydrate(events)`; in `renderReport()` → trigger the office→report transition. **Do not refactor** transport, timeline, evidence, or report rendering. |
| `web/app.css` | **Touch (small)** | Layout room for the office section; the report/office transition classes. No token changes. |

Deliberately **not** touched: `app/agent.py`, `app/llm.py`, `app/models.py`, `app/report.py`, `app/store.py`, `app/config.py`, `app/tools/*`, `requirements.txt`, `BUILD1.md`, `BUILD2.md`.

---

## Animation, Motion & Interaction Design

- **Idle life (calm, cheap).** Monitor opacity breathing 4–6 s, desynchronised per desk by a CSS `animation-delay` derived from index; one slow cursor blink on the Manager monitor. Pure CSS, no JS, no rAF. Nothing translates while idle.
- **Dispatch.** Packet forms at the cabin (140 ms scale-in), travels the corridor polyline to the desk (500 ms, `cubic-bezier(.4,0,.2,1)`), worker ring appears on arrival. The packet carries the real query as a hover title.
- **Travel.** `travel(el, polyline, ms)` walks a precomputed polyline with rAF, writing `transform: translate()`. Cancelled and retargeted if a newer action lands. rAF runs **only** while at least one figure is in transit; the loop stops itself when the transit set empties.
- **Execution.** Field marker pulse (1.6 s), monitor sweep. Indefinite by construction — it ends when the real paired event arrives. A `>15 s` marker appears near `TOOL_TIMEOUT` so a slow-but-alive call is legible.
- **Return.** Worker travels back carrying up to 8 packet glyphs plus the exact numeral; packets absorb into the tray (240 ms) and the tray counter animates to `data.total_evidence`.
- **Synthesis.** The upper floor dims to 60 %, the back-office band lifts, the three stage desks light in sequence on their real events, and the Manager monitor fills.
- **Final report.** The office scales to 0.96 and fades to a persistent 64 px-tall **"office strip"** pinned above the report — a miniature of the final tableau with per-desk visit counts. Clicking it expands the full office again. The office is never destroyed, satisfying "the user should still be able to understand what happened".
- **Progressive disclosure.** Click Manager → reasoning drawer. Click a Category A worker → drawer listing *that worker's* real evidence, filtered from `run.evidence` by `ev.tool`, with live links. Click a Category B stage → plain-language description of the code stage plus its real counts (e.g. citations validated, tiers found). All from the Run JSON.
- **Error/empty/loading.** Backend unreachable → office renders in an unstaffed "lights-off" tableau with one calm message. `gemini_ready:false` → desks staffed but Manager chip reads "Model unconfigured". `kind:"error"` → Manager cabin `--danger`, workers finish their current animation and settle, then the existing error screen takes over only if the final run `status === "error"` (preserving the Stage 0 fix that keeps partial results).
- **Accessibility.** The scene is `role="img"` with an `aria-label` summarising live state; a visually-hidden `aria-live="polite"` region announces one line per state change ("News Intelligence dispatched", "Research Intelligence returned 8 sources"); every worker is a `<g tabindex="0" role="button">` with a descriptive label; drawers are keyboard-dismissible; the existing timeline remains the full non-visual equivalent. Under `prefers-reduced-motion: reduce`, all travel becomes an instant state swap with a 1-frame cross-fade and idle breathing stops — the office still tells the whole story, statically.

---

## Responsive Strategy

- **≥1280 px** — full office, all seven desks, two-row floor as specified.
- **1024–1279 px** — same scene; SVG scales via `viewBox`; drawers become full-width sheets.
- **768–1023 px** — office compresses to a **two-column desk stack** (Category A left, Category B right) with shorter corridor paths; still real, still event-driven.
- **<768 px** — the spatial office is **not** crammed. It degrades to an **"office roster" list**: one row per worker with identity, live state chip, visit count, and evidence count, animated by the same reducer. The existing timeline and report become the primary surfaces. This is a documented, deliberate degradation, not a bug.

## Performance

Budget: ≤80 SVG nodes total; ≤8 concurrently animating elements; rAF active only during transit (typically <1 s per dispatch, 0 % CPU while idle); all motion via `transform`/`opacity` only (no layout-triggering properties); one delegated click listener on the scene root; `renderOffice()` diffs attributes rather than rebuilding nodes; no shadow/filter animation. Target: steady 60 fps on integrated graphics, and no measurable regression in SSE frame handling.

---

## Regression Risks

| # | Risk | Existing behaviour at stake | Check |
|---|---|---|---|
| 1 | Office code throws inside the SSE handler | one exception kills the stream → no timeline, no report | wrap `Office.handleEvent` in try/catch so the office can fail without taking transport down; verify by deliberately throwing once |
| 2 | Replay stampede on reload | duplicated/incoherent office state | reload mid-run: office must fast-forward, timeline must rebuild, report must still render |
| 3 | `StaticFiles` mount shadowing routes | `/`, `/app.css`, `/app.js` 404 or serve wrong content | curl all three plus `/static/office.js` after the change |
| 4 | Parallel `tool_selected` events | dropped dispatch; a tool call invisible in the office | verify office dispatch count equals `run.tool_calls.length` on every scenario |
| 5 | Worker activating without a real call | fabricated capability — the worst possible failure | assert every animated worker has a matching `tool_selected`; run a query that uses 2 tools and confirm the other 2 never leave `idle` |
| 6 | Report/evidence regression | the actual deliverable | full report render, citation chips, Sources links, evidence filters |
| 7 | CLI agent | shares `run_investigation` | `python -m app.agent "<target>"` |
| 8 | rAF loop never stops | battery/CPU burn, jank | idle for 60 s with DevTools performance: no scripting activity |
| 9 | Reduced motion | a11y commitment | OS reduced-motion on: no travel, no pulse, states still correct |
| 10 | Token drift | visual incoherence | audit `office.css` for raw colour literals — there must be none |

## Verification Plan

1. **Static:** `python -c "import app.main"`; all three legacy static paths 200; `/static/office.js` and `/static/office.css` 200.
2. **CLI:** `python -m app.agent "NVIDIA's competitive position in AI infrastructure"` — unchanged behaviour.
3. **Three live scenarios** (baselines from `BUILD2.md` → `Stage Outcome`), each verified in the browser *and* against `GET /api/run/{id}`:
   - `CRISPR base editing off-target safety` → research-led. Expect Research + Web active; **News and Patents must never leave their desks.**
   - `Quantum error correction patent landscape` → patent-led. Expect Patents first.
   - `NVIDIA's competitive position in AI infrastructure` → news-led, with a repeat call. Expect one worker dispatched **twice** with a `×2` badge.
4. **Idle proof:** for each scenario, record which desks never activated and confirm it matches the set difference between `available_tools` and `tools_used`.
5. **Pairing proof:** office dispatch count == `run.tool_calls.length`; each returned packet count == the matching `data.new_evidence`.
6. **Failure path:** simulate a provider outage → worker returns in `error`, real message shown, other workers continue, report still renders with the limitation.
7. **Integrity:** no citation outside `Run.evidence`; no URL in model prose; no `thought` content anywhere; office renders no model sentences beyond `data.reason`.
8. **A11y/responsive:** keyboard-only path; reduced-motion; 1440 / 1280 / 1024 / 800 / 390 px.
9. **Perf:** 60 s idle with no scripting; 60 fps during a dispatch.

## Rollback Plan

V2 baseline is `a75ede4` (`v2: stable baseline before UI redesign`), and a branch `ui-redesign-backup` already exists. Before implementation: `git switch -c stage-2-office` (work on a branch) or at minimum tag `git tag v2-stable a75ede4`. To abandon: `git switch main` (branch route) or `git restore --source=a75ede4 -- web app/main.py` for a surgical revert. A hard reset is **not** authorised without the user's explicit approval. Because the only backend change is three additive lines, rollback is effectively frontend-only.

## Scope Cut Line

Ship in this order; cut from the bottom if the clock runs out.
1. **Never cut:** event→action mapping, the four Category A workers activating only on real `tool_selected`, idle workers staying idle, packet counts from real `new_evidence`, the report and Sources list intact.
2. Cut first: the persistent office strip above the report (let the office simply collapse).
3. Then: Category B back-office band (keep the Manager `synthesizing` state alone).
4. Then: worker/manager drawers (the existing timeline and evidence grid already carry the detail).
5. Then: <768 px roster degradation (desktop-only, stated as a limitation).
6. Then: Option A static mount → fall back to Option B single-file.

## Architectural Decisions This Stage

1. **Pure adapter + reducer between SSE and pixels.** The only new architectural idea; it is what makes "no pre-scripted actions" enforceable rather than aspirational.
2. **SVG/CSS over canvas or 3D**, justified by entity count, hit-testing, accessibility, and the zero-dependency constraint.
3. **Two honestly-labelled worker categories**, so the office can be rich without lying about a single-agent backend.

## Must Remain Unchanged

`app/agent.py` (loop, budgets, emit payloads), `app/llm.py`, `app/models.py`, `app/report.py`, `app/store.py`, `app/config.py`, `app/tools/*`, `requirements.txt`, the four API endpoints and SSE frame format, the three existing static routes, the report/evidence/citation rendering behaviour, the CLI entry point, `.gitignore` secret rules, local-only git, `BUILD1.md`, `BUILD2.md`.

---

## Stage Outcome
