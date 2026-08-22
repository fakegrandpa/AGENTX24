# BUILD2.md — Stage 1 — Dynamic Tool Calling (exposed) + Full UI Redesign

Stage record. Planning sections below are frozen once written (P9). Only `Stage Outcome` is appended after implementation. `BUILD1.md` is untouched.

---

## Requirement

Exact wording as announced (abridged only where repeated):

> **2. Tool Calling** — "Integrate at least 2 external tools/APIs relevant to the problem."
>
> "The autonomous AI agent must dynamically determine: when a tool is needed, which tool should be used, what query/arguments should be sent, whether additional tools are required after receiving results."
>
> "This must demonstrate genuine agentic tool use, not a fixed sequence where every API is always called."
>
> "The primary goal is to make the agentic tool-calling behavior unmistakable to hackathon judges."
>
> The UI/telemetry "should clearly show: which tool was selected, **why the tool was needed in the current investigation context**, the query or task sent to the tool, when the tool was called."
>
> "The **'reason' must come from actual agent telemetry or a structured backend event, not random frontend text.**"
>
> "**The current UI is NOT acceptable. The entire frontend visual experience must be redesigned.** Do not make a small CSS improvement."
>
> "Do NOT implement a hardcoded pipeline … The LLM/agent must decide dynamically."
>
> Constraints: "no unnecessary frontend framework", "vanilla HTML/CSS/JS is acceptable and preferred", "Do not break the existing working CLI agent", "Do not break existing API endpoints without a necessary migration plan", "Do not replace working external tools without evidence that they are broken."

**Parsed literally — what must exist that does not exist today:**

1. A **model-authored reason** attached to every tool call, delivered through backend telemetry.
2. A **completely redesigned frontend** (new visual system, not a CSS tweak).
3. A **numbered tool-decision timeline** that makes dynamic selection obvious in under 10 seconds.
4. A **source-coverage summary** (source count, evidence count, tools used).
5. Report signal significance presented as **High / Medium / Low**.

**Boundaries — explicitly NOT requested (every adjacent temptation parked here):**
new data sources beyond the four that exist; changing the agent loop algorithm; multi-agent or planner/executor split; a real "knowledge-gap detection" model call; scoring or ranking algorithms; report export; run history or persistence; auth; charts or graph visualisations of the tool path; React/Tailwind/npm/Docker/DB/Redis/vector store/LangChain; new API endpoints; renaming existing endpoints; touching `app/report.py` parsing; changing `Signal.tier` values; evidence de-duplication (a known open item, not this requirement); rewriting `app/llm.py`'s Gemini surface.

**Interpretation (chosen for cheapness + extensibility, no question raised):**

- "at least 2 external tools" is **already satisfied** — four live tools exist. This stage is therefore **not about adding tools**; it is about *exposing* the decision. Adding a fifth source would spend the budget on the part that is already done.
- "why the tool was needed" is obtained by adding an optional **`reason` string argument to each tool's function-declaration schema**. The model writes it as part of the tool call, so it is genuinely agent-authored and arrives in the same round trip — no extra LLM call, no quota cost. It is a *declared tool argument*, not private chain-of-thought, so it does not violate BUILD1.md's no-chain-of-thought rule.
- "Identifying Knowledge Gaps" is emitted **only** when the model requests a further tool after evidence already exists, using the model's own `reason` for that follow-up call as the detail. It is derived from real model output, never synthesised.
- High/Medium/Low is a **display mapping** of the existing `high`/`important`/`emerging` tiers. The backend `Literal` is not touched, because `app/report.py::parse_signals_from_text` keys on those exact strings.

---

## Acceptance Test

**Given** the server running with a valid `GEMINI_API_KEY`, **when** a judge opens `http://127.0.0.1:8000/`, enters `NVIDIA's competitive position in AI infrastructure` and starts the investigation, **then** the redesigned dashboard shows a numbered tool-decision timeline in which **every** tool step displays the tool name, the exact query string the agent sent, and a non-empty reason that the agent itself produced, followed by the evidence count returned; and running the three scenarios in *Verification Plan* produces **at least three different tool-usage patterns**, with no query causing all four tools to be called in a fixed order.

---

## What Already Exists (verified against the code, not the documents)

Inspected: `app/agent.py`, `app/llm.py`, `app/tools/{__init__,news,research,web,patents}.py`, `app/report.py`, `app/main.py`, `app/store.py`, `app/models.py`, `web/{index.html,app.css,app.js}`, `requirements.txt`, git log.

**Already satisfies the requirement:**

- **Genuine ReAct loop** — `app/agent.py::run_investigation` (line ~52). `while iterations < MAX_ITERATIONS and total_tool_calls < MAX_TOOL_CALLS`, breaks on `if not response.tool_calls` (model chose to answer), otherwise executes calls, appends `types.Part.from_function_response` back into `history`, and loops. There is **no hardcoded tool sequence anywhere in the codebase.**
- **Four live external tools**, dynamically advertised — `app/tools/__init__.py::TOOL_REGISTRY` and `get_advertised_tools()` (patents gated by `is_patent_tool_available()`).
- **Dynamic selection already observed in live runs** (Stage 0 audit, recorded in `BUILD1.md` → `Stage Outcome` → section 5): four targets produced four different tool paths, including recovery after a zero-result `news_search`.
- **Tool + query + timing already in telemetry** — `emit(phase=..., kind="tool_selected", detail=f'{call.name}("{query}")', data={"tool":…, "args":…})` at `app/agent.py` ~line 190, and per-call `{name, args, ok, ms}` appended to `run.tool_calls`.
- **Failure handling already correct** — `app/tools/__init__.py::execute_tool` converts unknown tool / invalid args / provider exception into structured dicts; `agent.py` emits `SOURCE_UNAVAILABLE` or `NO_RESULTS` and continues the loop. Verified live: a zero-result `news_search` did not stop the investigation.
- **All report data the new UI needs is already in the `Run` JSON** — `report.summary`, `report.signals[]` (tier/headline/detail/citations), `report.sections{research,competitor_industry,recent_developments,patents,why_it_matters}`, `report.next_actions`, `report.coverage`, `report.limitations`, `run.evidence[]`, `run.tool_calls[]`.
- **Anti-fabrication is structural** — `app/report.py::extract_and_validate_citations` validates single *and* grouped `[E1, E4]` markers against the real evidence set, strips unresolvable ones, and removes any model-authored URL. Sources are rendered from `run.evidence` only.
- **API contract** — `GET /api/health`, `POST /api/investigate`, `GET /api/stream/{run_id}` (SSE), `GET /api/run/{run_id}`, `GET /`, `GET /app.css`, `GET /app.js`.

**Gaps that must be closed this stage:**

| Gap | Evidence from code |
|---|---|
| No reason for any tool call | grep for `reason` across `app/` returns only `finish_reason` and prose; no tool schema has a reason field |
| No knowledge-gap event | `PhaseEnum` (`app/models.py` lines 7–20) has no gap member |
| No numbered decision timeline | `web/app.js::handleTelemetryEvent` appends flat rows and hard-caps at 12 by `removeChild(firstChild)` — step numbers are discarded |
| No source-coverage panel | `web/app.js::renderReport` shows `tool_calls.length · evidence.length · elapsed` in one badge only; tools-used list is not shown |
| Significance labels | `web/app.js` renders `` `${sig.tier} Priority` `` → "emerging Priority", not Low |
| Visual system rejected by the organizer | `web/app.css` (13.4 KB), `web/index.html`, `web/app.js` are the Stage 0 design |

**Document drift found (code wins — reported, not "fixed"):**

1. `BUILD1.md` → `Stack & Key Decisions` #5 specifies the **Gemini Interactions API** with `client.interactions.create(..., store=False)`. The code actually uses `client.models.generate_content` with `types.FunctionDeclaration` + `types.Tool(function_declarations=[…])` (`app/llm.py` lines 143–164). The implemented surface works and is verified; **do not migrate it this stage.**
2. `BUILD1.md` #6 specifies default model `gemini-flash-latest`. Code defaults to `gemini-3.5-flash-lite` (`app/config.py` line 11) — a deliberate free-tier quota decision.
3. `BUILD1.md` scopes `web_search` as SHOULD and `patent_search` as inactive. Code advertises **all four**, patents via a credential-free Google Patents provider added in the Stage 0 audit.
4. `BUILD1.md` decision #15 declares the visual system Stage 0 scope that later stages must not replace. **Stage 1 overrides this by explicit organizer instruction** ("The current UI is NOT acceptable"). Recorded so the override is traceable rather than silent.
5. **SECURITY / P5 violation in git history:** `.env` containing a real 53-character `GEMINI_API_KEY` was committed in `434e91c` and untracked again in `c5e45e8`. It is correctly ignored and untracked now, but **the value remains recoverable from local history**. Not fixable without history rewrite (destructive — requires the user's explicit approval). Recommendation: rotate the key in Google AI Studio.

---

## Relevant Prior Context

Constraints inherited from `BUILD1.md` that bind this stage:

- `Core Flow Test` remains the baseline regression check and must still pass after the redesign.
- No chain-of-thought exposure. A declared tool argument is model *output*, not private reasoning — permitted; `part.thought` text stays filtered in `app/llm.py` line 181.
- Sources are rendered by application code from the evidence store; the model may never contribute a URL.
- Adaptive report sections: "a section with no supporting evidence is omitted, not rendered empty."
- Dependency budget: 7 pinned packages, zero frontend dependencies, no build step.
- `run_investigation(objective, emit_callback)` stays trigger-agnostic — the CLI, HTTP route, and any future scheduler share it.
- Design tokens live once in `web/app.css`; no value may be introduced outside the token set.
- Git is local-only. No remote, no push.

---

## Affected Files & Components

```
Touch:   app/models.py        - add ONE PhaseEnum member: IDENTIFYING_GAPS = "Identifying knowledge gaps".
                                Additive to a str-Enum; no field added to any model.
Touch:   app/tools/news.py    - add "reason" to NEWS_SEARCH_SCHEMA.parameters.properties (string,
                                described as a one-sentence justification). Provider function untouched.
Touch:   app/tools/research.py- same addition to RESEARCH_SEARCH_SCHEMA. Provider function untouched.
Touch:   app/tools/web.py     - same addition to WEB_SEARCH_SCHEMA. Provider function untouched.
Touch:   app/tools/patents.py - same addition to PATENT_SEARCH_SCHEMA. Provider function untouched.
Touch:   app/tools/__init__.py- execute_tool(): extract args["reason"] for telemetry and MUST NOT
                                forward it to func(); provider signatures are func(query=, limit=) only.
Touch:   app/llm.py           - SYSTEM_INSTRUCTION: one new numbered principle instructing the agent to
                                always supply `reason`, and to stop once evidence is sufficient.
                                No change to propose_next_step / resolve_model / the Gemini surface.
Touch:   app/agent.py         - enrich existing emit() payloads (data dict keys only), add the
                                IDENTIFYING_GAPS emission, carry reason into run.tool_calls entries.
                                Loop algorithm, budgets, and evidence handling unchanged.
Touch:   web/index.html       - full rewrite (new information architecture).
Touch:   web/app.css          - full rewrite (new token set + new visual system).
Touch:   web/app.js           - full rewrite (new render layer against the SAME endpoints).

Add:     (no new files)       - the three static files already exist and app/main.py serves exactly
                                /app.css and /app.js. Introducing a fourth static asset would require
                                a new route in main.py, so the redesign stays within these three files.

Reuse:   app/agent.py::emit() closure and the existing TelemetryEvent.data free-form dict - carries all
         new fields with zero schema change.
Reuse:   app/tools/__init__.py::TOOL_REGISTRY + get_advertised_tools() - the registry-dict seam from
         BUILD1.md; schema edits are data edits.
Reuse:   the entire Run JSON contract - every field the new report screen needs already exists.
Reuse:   app/store.py SSE broadcast + web/app.js EventSource + stream_end sentinel pattern.
Reuse:   the existing 4-state screen model (arrival / investigating / report / error) as the skeleton
         of the new IA, extended with empty-results and invalid-input states.

At risk: every tool call - if `reason` reaches func() as a kwarg, all four providers raise TypeError
         and every investigation returns zero evidence. Highest-consequence risk in this stage.
At risk: the CLI agent (`python -m app.agent "NVIDIA"`) - shares run_investigation and the emit path.
At risk: SSE consumers - app.js is rewritten, but the frame format (TelemetryEvent.model_dump_json)
         must not change or replay-on-reconnect breaks.
At risk: app/report.py signal parsing - keys on the literal strings "high"/"important"/"emerging".
At risk: /api/health field names consumed by the new app.js (gemini_ready, gemini_model,
         advertised_tools, providers).
```

---

## Integration Strategy

**Chosen: extend in place for the backend (a parameter and a field), full replace for the frontend only.**

- Backend is **extend in place**: one enum member, one schema property per tool, one argument-stripping branch, richer `data` dicts. No new module, no signature change to `run_investigation`, `propose_next_step`, or any provider function. The requirement is about surfacing a decision the loop already makes, so the loop is not touched.
- Frontend is a **full rewrite of three files**, which is the organizer's explicit instruction, not our choice. It is safe precisely because the API contract is frozen: the rewrite consumes the same four endpoints and the same `Run` JSON.

**Rejected alternatives, with reasons:**

- *Add alongside (a new `app/telemetry.py` or a `Decision` model)* — rejected: `TelemetryEvent.data` is already `dict[str, Any]`, so a new module and a new shape would add surface for zero capability.
- *Second LLM call to ask "why did you choose that tool?"* — rejected: doubles model turns and quota on a free tier that already forced the flash-lite switch, and invites post-hoc rationalisation rather than the actual decision.
- *Frontend-generated reason text* — rejected: explicitly forbidden by the requirement, and it would be fabrication.
- *Migrating `app/llm.py` to the Interactions API to match `BUILD1.md`* — rejected: the current surface is verified working; a migration is unrelated cleanup with real breakage risk (feature-integrator anti-pattern).
- *Adding a fifth data source* — rejected: "at least 2" is already exceeded four-fold; it would consume the budget on the satisfied half of the requirement.
- *Changing `Signal.tier` to high/medium/low* — rejected: breaks `app/report.py::parse_signals_from_text` tier aliases and the model-facing prompt vocabulary, for a label that can be mapped in one line of view code.
- *Re-scaffolding, stack change, React/Tailwind, npm, evidence de-dup, report export, run history* — rejected: not requested, and explicitly forbidden by the requirement's technical constraints.

**Architectural decisions this stage:** one — *the model authors its own tool-selection rationale as a declared `reason` tool argument.* This is the only new architectural idea; everything else is data and presentation.

---

## Proposed Dynamic Tool-Selection Architecture (unchanged loop, new visibility)

```
objective
   |
   v
[UNDERSTANDING_OBJECTIVE]                emit kind=objective
   |
   v
+-----------------------------------------------+
| while iterations < 8 and calls < 12 and       |
|       elapsed < 120s                          |
|                                               |
|  [PLANNING_NEXT_STEP]      emit kind=planning |
|  propose_next_step(history, advertised_tools)  <-- Gemini decides: tool(s) or final text
|                                               |
|  if no tool_calls -> break (model is done)    |
|                                               |
|  for each call:                               |
|    if evidence already exists and iteration>1:|
|      [IDENTIFYING_GAPS]    emit kind=planning |  detail = the model's own reason
|    [SEARCHING_* / CHECKING_NEWS]              |  emit kind=tool_selected
|        data = {tool, query, reason, step}     |
|    execute_tool(name, args)  (reason stripped)|
|    [EVIDENCE_FOUND | NO_RESULTS |             |
|     SOURCE_UNAVAILABLE]    emit tool_result   |
|        data = {tool, new_evidence, total}     |
|    function_response -> history               |
+-----------------------------------------------+
   |
   v
[COMPARING_EVIDENCE] -> [GENERATING_REPORT] -> assemble_report() -> [COMPLETED]
```

Nothing about tool order is expressed in code. The only code-side gate remains `get_advertised_tools()`, which hides `patent_search` when no provider can run.

---

## Exact Telemetry Contract Needed (all additive, inside `TelemetryEvent.data`)

| `kind` | `phase` | `text` | `detail` | `data` keys (new in bold) |
|---|---|---|---|---|
| `objective` | Understanding the objective | `Target: <objective>` | short restatement | `{"objective": str, **"available_tools": [str]**}` |
| `planning` | Planning the next step | `Planning step <n>` | `null` | `{**"step": int**}` |
| `planning` | **Identifying knowledge gaps** | `Additional evidence required` | **the model's `reason`** | `{**"step": int, "next_tool": str, "reason": str**}` |
| `tool_selected` | Searching recent research / Checking recent industry developments / Searching the web / Searching patent records | `Selected <tool>` | `<tool>("<query>")` | `{"tool": str, "args": {...}, **"query": str, "reason": str \| null, "call_index": int**}` |
| `tool_result` | Evidence found | `Evidence gathered from <tool>` | `<n> results · <total> total sources` | `{"tool": str, "new_evidence": int, **"total_evidence": int, "ok": true**}` |
| `note` | No results for that angle | `No results for '<query>'` | `0 results returned` | `{**"tool": str, "new_evidence": 0, "ok": true**}` |
| `note` | Source unavailable | `<tool> unavailable` | provider error detail | `{**"tool": str, "ok": false, "error": str**}` |
| `final` | Comparing and prioritising evidence | `Comparing and prioritising signals` | `Synthesising from <n> sources` | `{**"evidence": int**}` |
| `final` | Generating intelligence report | `Generating prioritized intelligence report` | existing string | `{}` |
| `final` | Completed | `Intelligence report ready` | `<n> tool calls · <n> sources · <n> signals` | `{**"tool_calls": int, "evidence": int, "tools_used": [str], "signals": int**}` |

`seq` (already present) is the timeline step number — the UI must render it as `01`, `02`, … rather than discarding it.

`run.tool_calls[]` entries gain a `"reason"` key (`dict[str, Any]`, so additive) so the coverage panel survives a page reload via `GET /api/run/{run_id}`.

**Honesty rules, non-negotiable:** if the model omits `reason`, the UI shows nothing in the reason slot — never a placeholder sentence. `IDENTIFYING_GAPS` is emitted only when a real follow-up tool call occurs. No UI phase may appear that has no corresponding telemetry event.

---

## Backend Changes Required (precise)

1. **`app/models.py`** — insert after `SEARCHING_PATENTS` (line 13):
   `IDENTIFYING_GAPS = "Identifying knowledge gaps"`. Nothing else in this file changes.

2. **Each of `app/tools/{news,research,web,patents}.py`** — in `*_SEARCH_SCHEMA["parameters"]["properties"]`, add:
   ```python
   "reason": {
       "type": "string",
       "description": "One short sentence stating why this tool is needed right now, given the investigation objective and the evidence already gathered.",
   },
   ```
   Add `"reason"` to that schema's `"required"` list so the model reliably supplies it. **Do not change any provider function signature.**

3. **`app/tools/__init__.py::execute_tool`** — after the existing `query` validation:
   ```python
   reason = args.get("reason")
   reason = reason.strip() if isinstance(reason, str) and reason.strip() else None
   ```
   The final call must remain exactly `func(query=query.strip(), limit=limit)`. `reason` is telemetry-only and is **never** forwarded. Optionally return it in the result dict under a key the agent reads back; simpler is for `agent.py` to read `call.args.get("reason")` directly — prefer that, so `execute_tool`'s return contract is untouched.
   `reason` must **not** be treated as required for validation: a missing reason is never an error.

4. **`app/llm.py::SYSTEM_INSTRUCTION`** — append one principle (no other change to this file):
   ```
   7. TOOL JUSTIFICATION: Every time you call a tool you MUST populate its `reason`
      argument with one short sentence explaining why that tool is needed at this point
      in the investigation. Choose the minimum number of tools that answers the
      objective; stop calling tools as soon as the evidence is sufficient. Do not call
      every available tool by default.
   ```

5. **`app/agent.py`** — five surgical edits inside `run_investigation`, no restructuring:
   - `objective` emit: add `data={"objective": objective, "available_tools": [t["name"] for t in advertised_tools]}`.
   - `PLANNING_NEXT_STEP` emit: add `data={"step": iterations}`.
   - Inside the `for call in response.tool_calls` loop, before the `tool_selected` emit:
     ```python
     reason = call.args.get("reason")
     reason = reason.strip() if isinstance(reason, str) and reason.strip() else None
     if run.evidence and iterations > 1:
         emit(phase=PhaseEnum.IDENTIFYING_GAPS, kind="planning",
              text="Additional evidence required",
              detail=reason,
              data={"step": iterations, "next_tool": call.name, "reason": reason})
     ```
   - `tool_selected` emit: `text=f"Selected {call.name}"`, keep `detail` as today, extend
     `data={"tool": call.name, "args": call.args, "query": arg_preview, "reason": reason, "call_index": total_tool_calls}`.
   - `run.tool_calls.append({...})`: add `"reason": reason`.
   - `tool_result` / `note` / `final` emits: add the `data` keys listed in the telemetry table.

6. **`app/main.py`, `app/store.py`, `app/report.py`, `app/config.py`, `requirements.txt`** — **no changes.** Endpoints, SSE framing, report assembly, and dependencies are all unchanged.

---

## Frontend / API Contract Changes

**API contract: unchanged.** No endpoint added, renamed, or removed; no response field removed. Every addition is a new key inside the already-free-form `TelemetryEvent.data` and `run.tool_calls[]`. Therefore no migration plan is required, and an old client would still work.

**Static asset constraint:** `app/main.py` serves only `/`, `/app.css`, `/app.js`. The redesign must ship within those three files — no fonts, images, or extra stylesheets — otherwise `main.py` needs new routes. System font stack only (BUILD1.md decision #14: no web fonts in the demo critical path).

---

## Complete UI Redesign Plan

### Design direction

An **Autonomous Intelligence Workspace**: premium, calm, precise, information-dense without crowding. Reference register: Linear / Vercel dashboard / Apple product clarity. Explicitly forbidden: cyberpunk, neon, hacker/terminal green, gaming UI, purple-gradient AI landing page, glassmorphism, decorative "AI AGENT ONLINE" text, excessive animation, fake futuristic ornament, spinners everywhere.

### Token set (declared once at the top of `web/app.css`; no value outside this set)

```
Surfaces   --canvas        near-white neutral (light) page ground
           --surface       card/panel ground, one step from canvas
           --surface-sunk  inset wells (timeline rail, code/query chips)
Lines      --line          hairline border (the primary structural device)
           --line-strong   emphasised divider
Text       --text          near-black primary
           --text-secondary  supporting copy
           --text-tertiary   meta / labels / timestamps
Accent     --accent        ONE restrained accent (deep blue), used for: primary button,
                           active timeline node, focus ring, citation chips. Nothing else.
Semantic   --warn          amber, only for limitations / unavailable sources
           --danger        muted red, only for error state
           --ok            muted green, only for completed nodes
Radius     --r-sm 6px      --r-md 10px      --r-pill 999px
Space      4 8 12 16 24 32 48 64  (8-point rhythm)
Type       --t-display 30px/1.15  --t-title 20px  --t-body 15px/1.6
           --t-label 13px  --t-mono 12.5px (ui-monospace, for queries + tool names)
           weights: 400 / 500 / 600 only
Shadow     --shadow-1 resting card   --shadow-2 raised/modal   (no glow, no gradient)
Motion     --fast 120ms ease-out (state)   --enter 200ms ease-out (entry)
           one 1.6s pulse on the single active timeline node; honour prefers-reduced-motion
Layout     --measure 1100px max content width, centred
```

Typography and hairline borders carry the design. Monospace is used **only** for machine facts (tool names, query strings) — that contrast is what makes the tool calls read as real system activity rather than decoration.

### Screen / information architecture

**Top bar** (persistent, 56px, hairline bottom border): `AGENTX24` wordmark at 600 weight, thin vertical divider, `Autonomous Research Intelligence` in `--text-tertiary`. Right side: a status cluster reading from `/api/health` — a small `--ok`/`--warn` dot, the resolved model name in mono, and `N sources online` with the tool names as a hover title. No logo art, no nav.

**State 1 — Initial (arrival).** Vertically generous, centred, single column, nothing but the investigation affordance:
- Line 1, `--t-display`: `What do you want to investigate?`
- Line 2, `--text-secondary`: one sentence — the agent selects its own sources and cites everything it finds.
- **Investigation input**: full-width, 56px tall, `--r-md`, hairline border that thickens to `--accent` on focus; a right-aligned primary button labelled `Investigate` with a subtle keyboard hint (`↵`). Real `<label>`, `autofocus`, Enter submits.
- Four example chips (pill, `--surface-sunk`, hairline) that fill the input on click, chosen to imply different tool paths: `NVIDIA's competitive position in AI infrastructure` · `Solid-state battery commercialization` · `CRISPR base editing off-target safety` · `Quantum error correction patent landscape`.
- A single quiet line naming the live sources.
- **Invalid input state:** empty or <3 chars → the border turns `--warn`, one inline message under the field, button disabled. No modal, no toast.

**State 2 — Investigating.** Two-column above 1000px (`grid-template-columns: minmax(0,1.35fr) minmax(0,1fr)`), stacked below.
- **Investigation header bar** (full width): the target in `--t-title`, a live `mm:ss`, live counters `N tool calls · N sources`, and a quiet `New investigation` text button. The clock always ticks — nothing may ever look frozen.
- **Left: Tool Decision Timeline** — the centrepiece. A vertical hairline rail with one node per telemetry event, rendered from `ev.seq` as a zero-padded step number in mono (`01`, `02`, …). Node anatomy:
  ```
  02 ●   Selected news_search                          ← phase-derived title, 500 weight
         QUERY   "NVIDIA competitor AI infrastructure"  ← mono, --surface-sunk chip
         REASON  Recent market developments may reveal  ← --text-secondary, italic-free
                 competitive shifts.
  ```
  Node variants keyed off `ev.kind` / `ev.phase`: `planning` = hollow node, title only; `tool_selected` = filled `--accent` node with QUERY + REASON rows (REASON row omitted entirely when `data.reason` is null); `tool_result` = `--ok` node reading `Analyzed N sources · N total`; `note`/unavailable = `--warn` node with the honest provider message; `IDENTIFYING_GAPS` = `--warn`-outline node titled `Identified knowledge gap` with the reason beneath; `final` = `--accent` node.
  Only the newest node carries the pulse. Completed nodes collapse to a single line. **Cap 14 visible nodes with a `Show earlier steps (N)` disclosure that expands — do not silently drop nodes as the current build does**, because the discarded steps are exactly the evidence of autonomy. `aria-live="polite"` on the rail.
- **Right: Evidence stream** — sticky header `Evidence · N`, then cards entering at `--enter` with a fade+2px rise: `[E7]` chip in mono `--accent`, source name and date in `--text-tertiary`, title in `--t-body`, and a small `--surface-sunk` pill naming the originating tool. Newest first.
- **Empty/no-results state:** if the run completes with zero evidence, the right column shows a calm panel — heading `No verifiable evidence found`, one sentence on what the agent tried, and the list of tools it called. Never an empty white box.

**State 3 — Report.** The timeline collapses to a one-line expandable summary (`7 steps · 3 tools · 24 sources · 48s`) so the proof of autonomy stays reachable. Then, in order, omitting any block whose data is absent:
1. **EXECUTIVE INTELLIGENCE** — `report.summary`, largest readable measure (~68ch), citation chips inline.
2. **KEY SIGNALS** — `report.signals[]`, one card each: a significance pill (**High** / **Medium** / **Low**, mapped `high→High`, `important→Medium`, `emerging→Low`) using weight and a single accent tint rather than three competing colours; headline in `--t-title`; `report.signals[].detail` as "why it matters"; citation chips that scroll to the matching source and briefly tint it.
3. **COMPETITIVE IMPLICATIONS** ← `sections.competitor_industry` · **RESEARCH SIGNALS** ← `sections.research` · **RECENT DEVELOPMENTS** ← `sections.recent_developments` · **PATENT SIGNALS** ← `sections.patents` · **WHY THIS MATTERS** ← `sections.why_it_matters`. Each rendered only when non-null.
4. **RECOMMENDED NEXT ACTIONS** — `report.next_actions[]` (preserve this working feature).
5. **KNOWLEDGE GAPS / LIMITATIONS** — `report.limitations[]` in a `--warn`-bordered panel, shown only when non-empty.
6. **SOURCE COVERAGE** — a compact stat row (`sources`, `evidence items`, `tool calls`) plus one row per tool used, taken from `run.tool_calls` + `report.coverage`, each showing the tool name in mono, its call count, and its evidence contribution.
7. **SOURCES** — numbered list from `run.evidence` only; real `target="_blank" rel="noopener noreferrer"` links, publisher, date, authors. Visually separated from the analysis above by `--line-strong`, because that separation *is* the evidence/interpretation boundary.

**State 4 — Error.** Replaces the workspace with one calm card: plain-language cause, one recovery hint, `Try again` primary button. Never a stack trace or raw provider string. Recoverable mid-run problems must **not** reach this state — they stay as `--warn` timeline nodes (behaviour already fixed in the Stage 0 audit; preserve it).

**Accessibility & responsive:** semantic `<header>/<main>/<section>`, correct heading order, real label, visible `--accent` focus ring on every interactive element, contrast checked against `--canvas`, full keyboard path, `aria-live="polite"` on the timeline only. One breakpoint at 1000px: two columns above, stacked below; nothing under 13px; no horizontal scroll at 800px.

### Data flow (agent → SSE → UI)

```
POST /api/investigate {query}  ->  {run_id}
GET  /api/stream/{run_id}      ->  text/event-stream
       replay of run.telemetry, then live TelemetryEvent JSON frames,
       terminated by {"event":"stream_end"}
   app.js: handleEvent(ev)
       ev.seq   -> timeline step number
       ev.phase -> node title + variant
       ev.kind  -> node variant
       ev.data.query / ev.data.reason -> QUERY / REASON rows
       ev.kind === "tool_result" -> refresh evidence via GET /api/run/{run_id}
   on stream_end -> GET /api/run/{run_id} -> renderReport(run)
   on EventSource error -> GET /api/run/{run_id}; render report if status==="done",
                           error card only if status==="error"
```

---

## Regression Risks

| # | Risk | Concrete existing behaviour that could break | How it will be checked |
|---|---|---|---|
| 1 | **`reason` forwarded to provider functions** | `news_search(query, limit)` etc. raise `TypeError`, `execute_tool` swallows it into `tool_execution_failed`, and **every investigation returns zero evidence** while still looking like it ran | `python -m app.agent "NVIDIA"` must report ≥8 evidence items and `ok=True` tool calls; `python -m app.tools.news "NVIDIA"` must still return 5 articles |
| 2 | `reason` made mandatory in validation | a model turn omitting it would produce `invalid_arguments` and lose the tool call | inspect `execute_tool`: absence of `reason` must not produce an error; force it by calling `execute_tool("news_search", {"query": "x"})` directly |
| 3 | New `PhaseEnum` member | `TelemetryEvent.phase` is a `PhaseEnum`; a value the frontend does not recognise must degrade to its raw string, not crash the timeline | run the patent scenario (which triggers the gap phase) and confirm the node renders |
| 4 | Frontend rewrite loses `/api/health` field names | arrival status cluster shows "failed" though the server is fine | `Invoke-RestMethod /api/health` and confirm `gemini_ready`, `gemini_model`, `advertised_tools`, `providers` are the keys read by the new `app.js` |
| 5 | SSE frame format or `stream_end` sentinel altered | reconnect/replay breaks; the report never appears | reload the page mid-run: replayed telemetry must rebuild the timeline and the report must still render |
| 6 | CLI telemetry printer | `cli_telemetry_printer` in `app/agent.py` `__main__` uses `ev.phase.value`, `ev.text`, `ev.detail` | `python -m app.agent "CRISPR base editing off-target safety"` prints phases and a full report |
| 7 | `Signal.tier` literals changed while relabelling | `app/report.py::parse_signals_from_text` tier aliases stop matching → zero signals parsed | grep that `models.py` still declares `Literal["high","important","emerging"]`; report must show ≥1 signal |
| 8 | System-prompt edit degrades tool use | over-restricting ("minimum number of tools") could collapse every run to a single tool call | the three verification scenarios must still produce ≥2 tool calls each and ≥3 distinct patterns |
| 9 | Global CSS rewrite | all four screens share the token set; a token error breaks every screen at once | walk all four states plus empty-results and invalid-input in the browser at 1440 / 1024 / 800px |
| 10 | Timeline disclosure regression | silently dropping nodes past the cap would delete the proof of autonomy | run a ≥4-tool investigation and confirm `Show earlier steps` restores the dropped nodes |
| 11 | Extra static asset added | `main.py` serves only `/app.css` and `/app.js`; anything else 404s | DevTools network panel: exactly three document/asset requests, all 200 |

---

## Implementation Plan

Each step is independently verifiable and leaves the project runnable. Backend first so the UI is built against real payloads.

1. **`app/models.py`** — add `IDENTIFYING_GAPS = "Identifying knowledge gaps"` to `PhaseEnum`.
   *Verify:* `python -c "from app.models import PhaseEnum; print(PhaseEnum.IDENTIFYING_GAPS.value)"`.
2. **Four tool schemas** — add the `reason` property (and add `"reason"` to `required`) in `app/tools/news.py`, `research.py`, `web.py`, `patents.py`.
   *Verify:* `python -c "from app.tools import get_advertised_tools; import json; print([list(t['parameters']['properties']) for t in get_advertised_tools()])"` shows `reason` on each.
3. **`app/tools/__init__.py::execute_tool`** — read `reason` for telemetry; keep the call exactly `func(query=..., limit=...)`; never treat a missing reason as an error.
   *Verify:* `python -c "from app.tools import execute_tool; r=execute_tool('news_search', {'query':'NVIDIA','reason':'test'}); print(len(r.get('results',[])))"` prints a non-zero count. **This is the step that de-risks regression #1 — do not proceed until it passes.**
4. **`app/llm.py`** — append principle 7 to `SYSTEM_INSTRUCTION`. Nothing else in the file.
   *Verify:* `python -m app.llm` still prints the model and a completion.
5. **`app/agent.py`** — the five emit/`tool_calls` enrichments and the `IDENTIFYING_GAPS` emission.
   *Verify:* `python -m app.agent "NVIDIA's competitive position in AI infrastructure"` — every `tool_selected` line carries a non-empty reason; evidence count > 0; report renders. Backend is now complete and the old UI still works.
6. **Green checkpoint** — commit the backend slice before touching the frontend, so the redesign has a known-good rollback point.
7. **`web/app.css`** — new token block and full visual system (top bar, arrival, workspace grid, timeline nodes, evidence cards, report blocks, all states).
   *Verify:* open `/` — arrival state renders in the new system; audit that every colour/space/radius/type value traces to a token; check focus rings and contrast.
8. **`web/index.html`** — new markup and information architecture: top bar, four state sections, all IDs the new `app.js` will bind to.
   *Verify:* `/` loads, exactly three asset requests, all 200; heading order and the input label are correct.
9. **`web/app.js`** — health cluster, input + invalid-input handling, SSE client, timeline renderer (step numbers, node variants, QUERY/REASON rows, earlier-steps disclosure), evidence stream, report renderer with High/Medium/Low mapping, source-coverage panel, sources list, error and empty states.
   *Verify:* full Acceptance Test in the browser.
10. **Verification sweep** — the three scenarios below, the `BUILD1.md` → `Core Flow Test`, and every at-risk item in the table above.
11. **Append `Stage Outcome`** to this document; update `README.md` only if run commands or the feature set changed; green checkpoint `stage-1: dynamic tool-call telemetry + redesigned intelligence workspace`.

**Dependency decision: no new dependency.** Requirements stay at the seven pinned packages; the frontend stays at zero dependencies and no build step. Nothing in this stage needs a library — `reason` is a schema string and the redesign is CSS and DOM.

---

## Verification Plan

**Acceptance test:** as stated above.

**Core flow test:** the `BUILD1.md` → `Core Flow Test` sentence, re-run unchanged.

**Three scenarios proving different dynamic tool selection.** Run each from the dashboard, record `run.tool_calls`, and require that at least three distinct patterns appear and that **no** run calls all four tools in the same fixed order. Stage 0 audit baselines are given for comparison:

| # | Investigation | Expected shape | Observed in Stage 0 audit |
|---|---|---|---|
| 1 | `CRISPR base editing off-target safety` | research-led; research_search first | `research → news → news` |
| 2 | `NVIDIA's competitive position in AI infrastructure` | competitor-led; news first, then web/research | `news → news` for bare "NVIDIA" |
| 3 | `Quantum error correction patent landscape` | patent-led; patent_search first | `patent → web → news(0 results) → web` for the NVIDIA IP variant |
| 4 | `Solid-state battery commercialization` | mixed | `news → research → web` |

Per-scenario checks: every `tool_selected` event carries a non-empty `data.reason`; each reason is specific to that investigation (not boilerplate repeated verbatim across runs); step numbers are contiguous; the UI reason text matches the telemetry payload exactly.

**Failure handling:** temporarily point one provider at an unreachable host — the run must complete, the timeline must show a `--warn` node with the honest message, other tools must still contribute, no fabricated evidence may appear, and the report must state the gap. (Scenario 3's real zero-result `news_search` already exercises the no-results path.)

**Anti-fabrication:** every SOURCES URL present in `run.evidence`; every `[En]` in prose resolvable; no model-authored URL in any rendered text; no `thought` content in any SSE frame.

**Definition of Done**
- [ ] `reason` present on all four tool schemas; stripped before provider invocation; never required for validation.
- [ ] Every `tool_selected` telemetry event in a live run carries a model-authored reason.
- [ ] `IDENTIFYING_GAPS` emitted only on real follow-up tool calls, carrying the model's reason.
- [ ] Numbered tool-decision timeline with QUERY and REASON rows; earlier steps recoverable, not dropped.
- [ ] Source-coverage block shows source count, evidence count, and tools used.
- [ ] Signals labelled High / Medium / Low; backend tier literals untouched.
- [ ] All nine UI states implemented and observed: initial, running, tool executing, evidence arriving, report generating, completed, empty/no-results, tool failure, invalid input.
- [ ] Redesign lives in exactly `web/index.html`, `web/app.css`, `web/app.js`; no new static asset, no new dependency, no framework.
- [ ] Three scenarios produce ≥3 distinct tool patterns; no fixed all-tools sequence.
- [ ] `python -m app.agent "<target>"` (CLI) still works; all four endpoints unchanged.
- [ ] `BUILD1.md` → `Core Flow Test` passes; all 11 regression items checked.
- [ ] No secrets staged; git remains local-only; green checkpoint committed.

---

## Must Remain Unchanged

- `app/agent.py::run_investigation` **loop algorithm, budgets (8/12/120s/15s), termination and forced-synthesis behaviour**, and its trigger-agnostic signature.
- `app/llm.py` — `propose_next_step`, `resolve_model` and its per-key cache, the `generate_content` + `FunctionDeclaration` surface, retry policy, and the `part.thought` filter. Only `SYSTEM_INSTRUCTION` text may change.
- All four provider function signatures `f(query: str, limit: int) -> dict` and their fallback chains (OpenAlex→arXiv, Google News RSS, DDGS→Wikipedia, EPO→Google Patents web) and 5-minute caches.
- `app/report.py` in full — heading splitter, grouped-citation validation, URL scrub, tier aliases, empty-section suppression.
- `Signal.tier` literals `high` / `important` / `emerging`; `Evidence` and `Run` field names.
- `app/main.py` and `app/store.py` — all four endpoints, SSE framing, `stream_end` sentinel, replay-on-subscribe, the three static routes.
- `app/config.py` budgets and provider reporting; `requirements.txt`.
- `.gitignore` secret rules; no remote; `.env` untracked.
- `BUILD1.md` and every earlier document.

## Scope Cut Line

Minimum version that still satisfies the requirement, cut in this order if the clock runs out:

1. **Cut first:** micro-interactions and entry animations (ship static states — a calm consistent interface beats a half-animated one).
2. **Then:** the `IDENTIFYING_GAPS` phase node (the reason rows on each tool call already prove dynamic decision-making).
3. **Then:** the `Show earlier steps` disclosure (raise the cap to 20 and keep all nodes visible).
4. **Then:** the SOURCE COVERAGE stat block (`report.coverage` already lists per-tool counts).
5. **Then:** the sub-1000px stacked layout (desktop-only, stated as a known limitation).

**Never cut:** the `reason` argument and its telemetry, the numbered timeline with tool + query + reason, real clickable evidence-derived sources, and the working four-tool dynamic selection. If even the redesign cannot be finished, the backend telemetry slice (steps 1–6) ships alone as a verified green checkpoint and the visual work is stated as incomplete — a broken redesign over working telemetry scores worse than the reverse.

---

## Stage Outcome

**Stage 1 complete (GREEN).** Verified by live runs on `gemini-3.5-flash-lite`; no mocked data.

### 1. What was actually built
- **Agent-authored tool reasons.** `reason` added to all four `*_SEARCH_SCHEMA` definitions (required in the schema so the model reliably supplies it). New `app/tools/__init__.py::extract_reason()`; `execute_tool` still calls providers as `func(query=, limit=)` only, so `reason` never reaches a provider. A missing reason is not an error.
- **`app/llm.py`** � SYSTEM_INSTRUCTION principle 7 (TOOL JUSTIFICATION + minimum-tools instruction). No change to `propose_next_step`, `resolve_model`, or the Gemini surface.
- **`app/models.py`** � one new `PhaseEnum` member, `IDENTIFYING_GAPS`.
- **`app/agent.py`** � telemetry enrichment only: `available_tools` on the objective event, `step` on planning events, `IDENTIFYING_GAPS` emitted when a follow-up tool call is made while evidence already exists (detail = the model's own reason), `query`/`reason`/`call_index` on `tool_selected`, `total_evidence`/`ok` on results, `tool`/`ok`/`error` on failures, `tools_used`/`signals` on completion, and `reason` carried into `run.tool_calls[]`. Loop, budgets and evidence handling untouched.
- **Full frontend redesign** � `web/app.css` (new token system: one accent, hairline structure, monospace reserved for machine facts, one 1000px breakpoint, `prefers-reduced-motion`), `web/index.html` (top bar with live health, arrival state, workspace, report, error), `web/app.js` (numbered tool-decision timeline with QUERY/REASON rows, earlier-steps disclosure, live evidence stream, High/Medium/Low signal mapping, source-coverage stats, evidence-only sources, citation chips).

### 2. Verified � three distinct dynamic tool paths
| Investigation | Observed tool path | Reasons present |
|---|---|---|
| CRISPR base editing off-target safety | `research_search -> web_search -> web_search` | 3/3 |
| Quantum error correction patent landscape | `patent_search -> web_search -> web_search` | 3/3 |
| NVIDIA's competitive position in AI infrastructure | `news_search -> web_search -> news_search` | 3/3 |

Each run: `status=done`, 23-24 evidence items, 5-6 prioritized signals, 4 adaptive sections, 3 model-authored next actions, max SSE inter-event gap 6.8-7.8 s (the synthesis turn), 2 `IDENTIFYING_GAPS` events. The first tool differs per objective and no run called all four tools.

Commands: `python -m app.config`; `python -m app.tools.{news,research,web,patents} "<q>"`; `python -m app.agent "NVIDIA's competitive position in AI infrastructure"`; `python -m uvicorn app.main:app --port 8000`; `GET /api/health`, `POST /api/investigate`, `GET /api/stream/{id}`, `GET /api/run/{id}`, `GET /`, `/app.css`, `/app.js` all 200.

Failure paths (verified by simulating a provider outage): `tool_unavailable` returned with `results == []` and no fabricated evidence; other tools kept working; `unknown_tool` and `invalid_arguments` still returned as structured data. Integrity across all runs: zero citations outside the evidence store, zero URLs in model prose, zero thought leakage.

### 3. Deviations from the plan
- **None functional.** All 11 planned steps implemented as specified in `Implementation Plan`; nothing from `Scope Cut Line` was cut.
- `/api/health` is polled once on load rather than continuously (not specified either way).

### 4. Known limitations
- The gap phase is inferred from "a follow-up tool call while evidence exists" plus the model's own reason; it is not a separate model judgement about what is missing.
- Evidence is still not de-duplicated across tool calls (carried over from Stage 0).
- `store.broadcast_event` still calls `put_nowait` from the worker thread; observed reliable in every run.
- Report prose is rendered as pre-wrapped text, so markdown bullet markers from the model appear literally.
- Verified on Chromium-class rendering at 1440/1024/800 px only.

### 5. Repository hygiene issues found during this stage (NOT introduced by it)
- **A GitHub remote exists** (`origin -> github.com/fakegrandpa/AGENTX24`) and `origin/main` matched local `HEAD`, contradicting the local-only instruction.
- **Commit `434e91c` added `.env` containing a real 53-character `GEMINI_API_KEY`.** `c5e45e8` only untracked the file; the value remains in history and, given the remote, was likely published. **The key must be rotated.** Not remediable without history rewrite, which is destructive and needs explicit approval.
- `.gitignore` line 88 ignores `BUILD*.md`, so `BUILD1.md` and `BUILD2.md` are untracked; `BUILD2.md` was force-added for this stage's checkpoints.
