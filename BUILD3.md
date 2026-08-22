# BUILD3.md — Stage 3 — Specialized Agents & Orchestrated Collaboration

Stage record under AGENTS.md P9. Planning sections are frozen once written; only `Stage Outcome` is appended. `BUILD1.md` and `BUILD2.md` are untouched.

**Baseline:** commit `a75ede4` (`v2: stable baseline before UI redesign`), tag `v2-stable`, current branch `stage-2-office`, working tree clean. Verified `git log`/`git status` at planning time.

---

## Requirement

Exact wording as announced:

> "Use at least 2 specialized agents with clearly defined responsibilities. Demonstrate meaningful collaboration or orchestration between agents."

### Demanded, parsed literally

1. **At least two agents** — "at least 2 specialized agents".
2. **Specialization** — each must be *specialized*, i.e. narrower than the current do-everything agent.
3. **"clearly defined responsibilities"** — the division of labour must be explicit and inspectable, not implied.
4. **"meaningful collaboration or orchestration between agents"** — one agent's output must demonstrably change another agent's behaviour. A pipeline where agent B merely formats agent A's text is orchestration in name only.

### Acceptance Test

**Given** the server running with a valid `GEMINI_API_KEY`, **when** a judge submits `NVIDIA's competitive position in AI infrastructure`, **then** the run record at `GET /api/run/{run_id}` contains at least one `Critique` object produced by the **Evidence Critic** agent — with its own `sufficient` verdict and named `gaps` — and the telemetry shows the **Lead Investigator** signalling completion, the Critic overruling it, and the Investigator then executing a further tool call whose `reason` addresses a gap the Critic named; and the final report is composed by the **Report Synthesist** agent under its own system instruction, with every agent's contribution attributed by a first-class `agent` field on each telemetry event.

### Boundaries — NOT requested (every adjacent temptation parked here)

An agent framework (LangChain / LangGraph / CrewAI / AutoGen); an agent-to-agent message bus, blackboard, or shared scratchpad store; concurrent/parallel agent execution; agent-to-agent negotiation or voting; a supervisor tree or hierarchical planner; per-agent model selection or fine-tuning; new external tools or data sources; agent memory or persistence across runs; new API endpoints; a database; changes to the four tool providers; changes to `report.py` parsing; the BUILD3-office visualization (that plan was lost — see *What Already Exists*); evidence de-duplication; a UI redesign. None of these are needed to satisfy the sentence, and each would breach the dependency and scope rules from `BUILD1.md`.

### Interpretation (chosen for cheapness and extensibility; no blocking ambiguity)

- **"Agent" = a distinct LLM role with its own system instruction, its own input contract, its own output contract, and its own decision authority.** This is the honest reading for this codebase: `app/llm.py::propose_next_step(contents, tools_schema, system_instruction=…)` **already accepts a per-call system instruction**, so a second agent costs a new instruction plus a call site — not a framework.
- **Code stages are not agents.** `report.py` functions stay described as pipeline stages, consistent with the honesty rule carried from `BUILD2.md`. A judge asking "are these real agents?" must get the true answer.
- **Three agents, not two.** Two is the floor; the third (Synthesist) is nearly free because the forced-synthesis call already exists at `agent.py:342` and merely needs its own instruction. Three gives a clean, defensible separation: *gather / judge / compose*.
- **Collaboration is bidirectional by design.** The Critic does not sit downstream of the Investigator — it **gates** the Investigator's attempt to finish and can send it back to work. That is what makes the collaboration meaningful rather than decorative, and it is observable in the event stream.
- **Structured handoff via forced function calling, not free-form JSON.** The Critic is given exactly one tool, `submit_review`, and must call it. Reusing the existing function-calling plumbing removes all JSON parsing risk.

---

## What Already Exists (verified against the code at `a75ede4`)

Inspected: `app/agent.py`, `app/llm.py`, `app/models.py`, `app/config.py`, `app/report.py`, `app/store.py`, `app/main.py`, `app/tools/__init__.py`, `web/app.js`, git history.

### Zero multi-agent support exists today

A search across `app/` for `class .*Agent`, `critic`, `planner`, `orchestrat`, `specialist`, `AGENT_`, `reviewer`, `verdict`, `sufficien` returns **only** the `role="user"` / `role="model"` arguments of `types.Content` and prose in the system prompt. There is exactly one reasoning entity:

- `app/agent.py::run_investigation(objective, emit_callback)` — a single ReAct loop, budgets `MAX_ITERATIONS=8`, `MAX_TOOL_CALLS=12`, `WALL_CLOCK=120s`.
- `app/llm.py::propose_next_step(contents, tools_schema=None, system_instruction=SYSTEM_INSTRUCTION)` — **the seam this stage uses.** One `SYSTEM_INSTRUCTION` constant (7 numbered principles, principle 7 added in Stage 1) is the current agent's whole identity.

### The exact integration points already in the code

| Location | What it does today | Why it matters here |
|---|---|---|
| `agent.py:178-181` | `if not response.tool_calls: final_synthesis_text = response.text; break` | The Investigator's *self-declared completion*. This is the natural gate for the Critic — nothing else needs to move. |
| `agent.py:335-344` | Builds a synthesis prompt and calls `propose_next_step(contents=history, tools_schema=None)` **with the default system instruction** | The Synthesist already exists as a code path wearing the Investigator's identity. Giving it its own instruction is a one-argument change. |
| `agent.py:200-207` | Emits `PhaseEnum.IDENTIFYING_GAPS` when a follow-up tool call happens while evidence exists, using the model's own `reason` | Partial support: the gap *phase* exists but is **inferred**, not judged. `BUILD2.md` → `Stage Outcome` records this as a known limitation: *"the gap phase is inferred … it is not a separate model judgement about what is missing."* This stage closes exactly that gap. |
| `agent.py:63-79` (the `emit()` closure) | Builds every `TelemetryEvent` in one place | A single closure signature change attributes every event to an agent. |
| `app/models.py` | `PhaseEnum` (14 members, `IDENTIFYING_GAPS` added Stage 1), `TelemetryEvent`, `Run` | Additive enum members and defaulted fields are the established pattern here. |
| `app/config.py` | All budgets read from env with defaults | The established place for a new `MAX_CRITIQUES` / `ENABLE_CRITIC`. |
| `app/tools/__init__.py` | `TOOL_REGISTRY`, `get_advertised_tools()`, `execute_tool()`, `extract_reason()` | The Critic's `submit_review` tool must **not** enter this registry — it is passed directly to `propose_next_step(tools_schema=[…])` so the Investigator never sees it. |

### The existing pattern for this class of change (how Stage 1 did it)

Stage 1 added agent-authored tool reasons by: one additive `PhaseEnum` member; a schema property per tool; a helper (`extract_reason`) in `app/tools/__init__.py`; enriched `emit()` `data` payloads; one appended principle in `SYSTEM_INSTRUCTION`; then additive-only frontend wiring. **No signature of a shared function changed.** This stage follows the same shape.

### Document drift and repository facts to report

1. **A `BUILD3.md` written earlier in this session (the "Autonomous Intelligence Office" UI plan) no longer exists on disk.** It was untracked because `.gitignore:88` ignores `BUILD*.md`, and branch/restore operations discarded it. Highest surviving number is therefore **2**, and this document legitimately takes the number 3. **`.gitignore:88` has now caused real data loss — recommend removing `BUILD*.md` from that ignore block, or at minimum `git add -f` every stage document immediately on creation.** `BUILD1.md` and `BUILD2.md` are also currently untracked for the same reason.
2. `BUILD1.md` → `Stack & Key Decisions` #5 specifies the Gemini **Interactions API**; the code uses `client.models.generate_content` + `types.Tool(function_declarations=…)`. Code wins; do not migrate.
3. `BUILD1.md` → `Not To Be Built Yet` lists "Multi-agent or sub-agent orchestration; any agent framework", and `BUILD2.md` repeats it. **This stage overrides the multi-agent prohibition by explicit organizer instruction.** The framework prohibition still stands and is *reinforced* here.
4. `BUILD1.md` decision #15 (visual system frozen at Stage 0) is long superseded.
5. Repository now has **two remotes** (`origin`, `submission`) and many branches/tags, despite earlier local-only instructions. Local `main`/`stage-2-office` are at `a75ede4`; `origin/main` is at `da665b4`. Nothing in this stage may push. The `.env`-in-history exposure recorded in `BUILD2.md` → `Stage Outcome` §5 is **still unresolved**: rotate the key.

---

## Relevant Prior Context

- **Honesty rule (BUILD2.md):** never present a code stage as an autonomous agent; never fabricate a capability. Applies directly — the roster must distinguish agents from pipeline stages.
- **No chain-of-thought exposure (BUILD1.md):** a Critic verdict delivered as *declared function-call arguments* is model output, not private reasoning — safe to display, exactly like `reason` in Stage 1. Free-form "thinking" text must not be surfaced.
- **Evidence integrity:** sources are rendered by code from `Run.evidence`; the model may never contribute a URL. The Critic must therefore receive an **evidence digest (ids, titles, sources, dates, tool)** and must not be able to inject new URLs or new evidence ids.
- **Zero new dependencies, no build step, seven pinned packages.**
- **Free-tier quota is a live constraint** — the switch to `gemini-3.5-flash-lite` was forced by quota. Extra agent turns must be budgeted and disableable.
- `run_investigation` stays trigger-agnostic; the CLI (`python -m app.agent "<target>"`) must keep working.
- Loop safety from `BUILD1.md` MUST #4 extends to the new agents: caps, timeouts, retry limits, safe termination, honest limitations.

---

## Affected Files & Components

```
Touch:   app/models.py     - add AgentRole str-Enum (investigator | critic | synthesist);
                             add Critique model; add 3 PhaseEnum members
                             (CRITIC_REVIEWING, CRITIQUE_RETURNED, SYNTHESIST_COMPOSING);
                             add TelemetryEvent.agent field (defaulted, additive);
                             add Run.critiques: list[Critique] = [] (defaulted, additive).
Touch:   app/config.py      - add ENABLE_CRITIC (default on) and MAX_CRITIQUES (default 2),
                             read from env exactly like the existing budgets.
Touch:   app/agent.py       - orchestration only: emit() gains an `agent` parameter defaulting
                             to AgentRole.INVESTIGATOR; the completion branch at 178-181 now
                             consults the Critic before accepting completion; the synthesis
                             call at 342 passes the Synthesist instruction; critiques appended
                             to run.critiques. The ReAct loop, budgets, tool execution and
                             evidence handling are NOT restructured.
Touch:   app/main.py        - /api/health gains an additive "agents" key exposing the roster
                             (id, name, responsibility, tools, model). No new endpoint.
Touch:   web/app.js         - additive rendering only: agent badge on timeline nodes from
                             ev.agent; a critique node showing the Critic's verdict and gaps;
                             an agent roster strip populated from /api/health.
Touch:   web/app.css        - styles for the agent badge, critique node and roster strip,
                             using the existing :root token palette only.

Add:     app/agents.py      - the agent roster and the Critic implementation:
                             AGENT_ROSTER, CRITIC_INSTRUCTION, SYNTHESIST_INSTRUCTION,
                             SUBMIT_REVIEW_SCHEMA, build_evidence_digest(), critique_evidence().
                             No existing file is the right home: app/llm.py is the transport
                             adapter and must stay model-agnostic; app/agent.py is the
                             orchestrator and must not also define roles; app/tools/ is for
                             external data providers, and submit_review is deliberately NOT a
                             registered tool.

Reuse:   app/llm.py::propose_next_step(..., system_instruction=...) - already parameterised;
         the Critic and Synthesist are new instructions through the SAME adapter, retries,
         model cache and thought-filter. Zero change to llm.py.
Reuse:   the function-calling plumbing (types.FunctionDeclaration / LLMResponse.tool_calls)
         to carry the Critic's structured verdict - no JSON parsing.
Reuse:   the emit() closure as the single telemetry chokepoint.
Reuse:   Stage 1's additive-payload pattern and the defaulted-field pattern in models.py.
Reuse:   PhaseEnum + timeline node variant rendering in web/app.js.

At risk: the investigation completion path - if the Critic loop is wrong, a run could
         never terminate or could terminate without a report. Highest-consequence risk.
At risk: free-tier quota - every run gains 1-3 LLM calls; quota exhaustion currently
         surfaces as a failed run.
At risk: TelemetryEvent shape - consumed by web/app.js, SSE replay, and GET /api/run.
At risk: the forced-synthesis path at agent.py:335-348 - the only producer of the report
         text that report.py parses; a wrong instruction here silently degrades every
         section, signal tier and citation.
At risk: the CLI entry point (agent.py __main__) - shares run_investigation and emit.
At risk: /api/health response shape - consumed by web/app.js on load.
```

---

## Integration Strategy

**Chosen: extend in place (a branch at the completion gate + an argument at the synthesis call) plus add alongside (one new module for the new roles).**

Justification: the requirement is about *who decides what*, and the decision points already exist in the code at `agent.py:178-181` and `agent.py:342`. The Critic inserts as a guard on an existing branch; the Synthesist is an argument to an existing call. No shared function signature changes, no restructuring of the loop, and the new roles live in their own module so `agent.py` remains the orchestrator and `llm.py` remains the transport.

**Rejected alternatives:**

- *An agent framework (LangChain / LangGraph / CrewAI / AutoGen)* — rejected: hides the very loop judges must see, adds a large dependency to a zero-dependency frontend/backend budget, and `BUILD1.md` prohibits it. The whole orchestration is ~70 lines.
- *A generic multi-agent abstraction (base class, registry, message bus, blackboard)* — rejected as speculative abstraction on two-and-a-half agents. `AGENT_ROSTER` is a dict, matching the `TOOL_REGISTRY` precedent.
- *Parallel/concurrent agents* — rejected: unrequested, multiplies quota burn, and makes the telemetry harder to read, which works against the scored goal of legibility.
- *Registering `submit_review` in `TOOL_REGISTRY`* — rejected: it would be advertised to the Investigator via `get_advertised_tools()`, letting it grade itself.
- *Splitting the four tools into four "specialist agents"* — rejected as dishonest: they are HTTP adapters with no reasoning. `BUILD2.md`'s honesty rule forbids relabelling them.
- *Free-form JSON output from the Critic* — rejected: forced function calling gives the same structure with no parser to break.
- *A localized reshape of the loop into a planner/executor split* — rejected: no requirement demands it, and it would put the verified Stage-1 dynamic tool selection at risk.
- *Rebuilding, re-scaffolding, stack change, or unrelated cleanup* — rejected outright.

### Architectural Decisions This Stage

1. **An agent is a system instruction + an input contract + an output contract + decision authority**, realised through the existing `propose_next_step` seam. No framework, no base class.
2. **The Critic gates completion rather than following it.** Bidirectional flow is what makes the collaboration meaningful and observable.
3. **Handoffs are structured artifacts** (`Critique` objects persisted on `Run`), not prose passed between prompts.

### The three agents and their responsibilities

| Agent | `AgentRole` | Responsibility (single sentence) | Input | Output | Tools |
|---|---|---|---|---|---|
| **Lead Investigator** | `investigator` | Understand the objective and dynamically gather evidence from external sources. | objective + tool results + critiques | tool calls with `query` + `reason`, or a completion signal | all four real tools |
| **Evidence Critic** | `critic` | Judge whether the gathered evidence actually answers the objective and name what is missing. | objective + evidence digest + tool-call history | one `submit_review` call: `sufficient`, `gaps[]`, `recommended_tool`, `recommended_query`, `confidence` | only `submit_review` (no data tools — it cannot gather, only judge) |
| **Report Synthesist** | `synthesist` | Compose the prioritized, cited intelligence report from verified evidence only. | objective + evidence + final history | the structured report text `report.py` parses | none |

Separation of powers is the point: the Investigator cannot declare itself done, the Critic cannot gather evidence, and the Synthesist cannot introduce evidence.

### Orchestration flow (the collaboration, concretely)

```
run_investigation  (orchestrator — agent.py, not an LLM)
  |
  |-- Investigator turn ------------------------------------------------.
  |     tool_calls?  yes -> execute tools, collect evidence, loop ------'
  |     tool_calls?  no  -> Investigator claims completion
  |                            |
  |                            v
  |                     ENABLE_CRITIC and run.evidence and critiques < MAX_CRITIQUES ?
  |                            |                                  |
  |                           yes                                 no -> accept completion
  |                            v
  |                     Critic turn  (own instruction, submit_review only)
  |                            |
  |            sufficient=true |            sufficient=false
  |                            v                    v
  |                  accept completion     append Critique to run.critiques,
  |                                        inject a critique message into the
  |                                        Investigator's history naming the gaps,
  |                                        emit IDENTIFYING_GAPS (agent=critic),
  |                                        continue the loop  ------------------.
  |                                                                            |
  '----------------------------------------------------------------------------'
  |
  v
  Synthesist turn (own instruction, no tools) -> report text -> report.py::assemble_report
```

The Critic's `gaps` therefore *cause* the Investigator's next tool call — and Stage 1's `IDENTIFYING_GAPS` phase stops being inferred and becomes a real second-agent judgement, closing the limitation recorded in `BUILD2.md`.

**Termination safety:** the Critic is bounded by `MAX_CRITIQUES` (default 2) **and** by the pre-existing `MAX_ITERATIONS` / `MAX_TOOL_CALLS` / `WALL_CLOCK` budgets, which it cannot extend. Any Critic failure (API error, no `submit_review` call, malformed args) **fails open**: treated as `sufficient=true`, a limitation is recorded, and the run proceeds. A Critic problem can never prevent a report.

---

## Regression Risks

| # | Risk | Concrete existing behaviour that could break | How it will be checked |
|---|---|---|---|
| 1 | **Non-termination** — Critic keeps rejecting completion | investigations never finish; wall-clock kills them at 120 s with no report | force `sufficient=false` via a stub and confirm the run still ends and produces a report; assert `len(run.critiques) <= MAX_CRITIQUES` |
| 2 | **Report degraded by the Synthesist instruction** — `report.py` parses the model's headings (`INVESTIGATION SUMMARY`, `HIGH PRIORITY SIGNALS`, `KEY RESEARCH DEVELOPMENTS`, `COMPETITOR / INDUSTRY ACTIVITY`, `RECENT DEVELOPMENTS`, `WHY THIS MATTERS`, `RECOMMENDED NEXT ACTIONS`) and tier words `HIGH PRIORITY` / `IMPORTANT` / `EMERGING` | silently empty sections, zero signals, canned-free but empty reports | the Synthesist instruction must reproduce those exact headings and tier words verbatim; verify ≥1 signal, ≥3 sections and ≥1 next action on all three scenarios, matching the `BUILD2.md` baseline |
| 3 | **`submit_review` leaks into the Investigator's tool set** | the Investigator could grade itself; tool-selection telemetry corrupted | assert `"submit_review" not in [t["name"] for t in get_advertised_tools()]` and not in `TOOL_REGISTRY` |
| 4 | **Quota exhaustion** from +1..3 calls per run | today a quota failure yields `status="error"` and a bland run | run all three scenarios back-to-back; verify `ENABLE_CRITIC=0` cleanly restores Stage-1 behaviour |
| 5 | **`TelemetryEvent.agent` shape change** | `web/app.js` node rendering, SSE replay, `GET /api/run` consumers | field must be defaulted; reload mid-run and confirm replay rebuilds the timeline; confirm an event without `agent` still renders |
| 6 | **`Run.critiques` shape change** | `GET /api/run/{id}` response consumed by `web/app.js` | must default to `[]`; a run with the Critic disabled must serialize and render identically to today |
| 7 | **`emit()` signature change** | every telemetry call site in `agent.py`, plus the CLI printer using `ev.phase.value` / `ev.text` / `ev.detail` | `agent` must be an optional keyword with a default; `python -m app.agent "<target>"` must print unchanged lines plus the new ones |
| 8 | **Dynamic tool selection regression** — a critique nudging the Investigator could flatten variety | Stage 1's verified proof that different objectives produce different tool paths | re-run the three `BUILD2.md` baseline scenarios; ≥3 distinct tool patterns must remain, and no run may call all four tools in a fixed order |
| 9 | **Critic injecting evidence** | anti-fabrication guarantee | the Critic receives only an evidence digest and cannot add ids or URLs; assert no SOURCES URL outside `Run.evidence` and no `[En]` outside the store |
| 10 | **`/api/health` shape** | `web/app.js::loadHealth()` reads `gemini_ready`, `gemini_model`, `advertised_tools`, `providers` | those keys must remain; `agents` is additive; confirm the arrival screen still renders when `agents` is absent |
| 11 | **Global CSS additions** | the current premium UI | audit new rules for raw colour literals; walk all screens at 1440 / 1024 / 800 px |

---

## Implementation Plan

Each step is independently verifiable and leaves the project runnable. Backend first; the CLI is the fastest verifier.

1. **`app/models.py`** — add `AgentRole(str, Enum)` with `INVESTIGATOR="investigator"`, `CRITIC="critic"`, `SYNTHESIST="synthesist"`; add three `PhaseEnum` members `CRITIC_REVIEWING="Reviewing evidence sufficiency"`, `CRITIQUE_RETURNED="Critique returned"`, `SYNTHESIST_COMPOSING="Composing intelligence report"`; add `class Critique(BaseModel)` with `seq: int`, `sufficient: bool`, `gaps: list[str] = []`, `recommended_tool: str | None`, `recommended_query: str | None`, `confidence: float | None`, `note: str | None`; add `agent: AgentRole = AgentRole.INVESTIGATOR` to `TelemetryEvent`; add `critiques: list[Critique] = Field(default_factory=list)` to `Run`.
   *Verify:* `python -c "from app.models import AgentRole, Critique, PhaseEnum, TelemetryEvent, Run; print(AgentRole.CRITIC, PhaseEnum.CRITIC_REVIEWING.value, Run(id='r',query='q',status='running',started_at='t').critiques)"`.
2. **`app/config.py`** — add `ENABLE_CRITIC = os.getenv("ENABLE_CRITIC", "1").strip() not in ("0","false","False")` and `MAX_CRITIQUES = int(os.getenv("MAX_CRITIQUES", "2"))`; surface both in `print_config_summary()`.
   *Verify:* `python -m app.config` prints them.
3. **`app/agents.py` (new)** — `AGENT_ROSTER: dict[str, dict]` (id, name, responsibility, tools, category="agent"); `CRITIC_INSTRUCTION`; `SYNTHESIST_INSTRUCTION` (must reproduce `report.py`'s exact headings and tier words); `SUBMIT_REVIEW_SCHEMA` (`sufficient: boolean` required, `gaps: array[string]`, `recommended_tool: string`, `recommended_query: string`, `confidence: number`, `note: string`); `build_evidence_digest(evidence, tool_calls) -> str` (ids, titles, sources, dates, tool per item — **no URLs**); `critique_evidence(objective, evidence, tool_calls, seq) -> Critique` calling `propose_next_step(contents=[digest_prompt], tools_schema=[SUBMIT_REVIEW_SCHEMA], system_instruction=CRITIC_INSTRUCTION)`, reading `tool_calls[0].args`, and **failing open** to `Critique(sufficient=True, note="critic unavailable: …")` on any error.
   *Verify:* `python -c "from app.agents import AGENT_ROSTER, critique_evidence; print(list(AGENT_ROSTER))"`; then a live single-call check with two hand-built `Evidence` objects prints a real `Critique`.
4. **`app/agent.py` — telemetry attribution** — add `agent: AgentRole = AgentRole.INVESTIGATOR` to the `emit()` closure and pass it into `TelemetryEvent`. No other call site changes yet.
   *Verify:* `python -m app.agent "NVIDIA"` behaves exactly as before; `run.telemetry[0].agent == AgentRole.INVESTIGATOR`.
5. **`app/agent.py` — Critic gate** — replace the body of the completion branch at `178-181` with: if `ENABLE_CRITIC` and `run.evidence` and `len(run.critiques) < MAX_CRITIQUES` → emit `CRITIC_REVIEWING` (`agent=critic`), call `critique_evidence(...)`, append to `run.critiques`, emit `CRITIQUE_RETURNED` (`agent=critic`, `data={"sufficient","gaps","recommended_tool","confidence"}`); if `sufficient` → accept completion and break; else → emit `IDENTIFYING_GAPS` (`agent=critic`, detail = first gap), append a `types.Content(role="user", …)` critique message to `history` naming the gaps and the recommended tool/query, and `continue` the loop. Preserve the existing `final_synthesis_text = response.text` capture as a fallback.
   *Verify:* `python -m app.agent "NVIDIA's competitive position in AI infrastructure"` shows a Critic review and, when it rejects, a further Investigator tool call whose `reason` addresses a named gap; run terminates; `len(run.critiques) <= 2`.
6. **`app/agent.py` — Synthesist** — always route the final report through the Synthesist: pass `system_instruction=SYNTHESIST_INSTRUCTION` to the synthesis call at `342`, emit `SYNTHESIST_COMPOSING` (`agent=synthesist`) before it, and use it on both the budget-exhausted path and the accepted-completion path. Keep the existing exception handling and `synthesis_from_model` honesty flag untouched.
   *Verify:* report still contains ≥1 signal, ≥3 sections, ≥1 next action; `Run.status` logic unchanged.
7. **`app/main.py`** — `/api/health` gains `"agents": [AGENT_ROSTER[k] for k in ("investigator","critic","synthesist")]` plus `"critic_enabled": ENABLE_CRITIC`. Existing keys untouched; no new endpoint.
   *Verify:* `Invoke-RestMethod /api/health` shows the roster and all pre-existing keys.
8. **Green checkpoint** — commit the backend before touching the frontend.
9. **`web/app.js`** — additive only: render an agent badge on each timeline node from `ev.agent` (default `investigator` when absent); render a critique node for `CRITIQUE_RETURNED` showing the verdict and gaps from `ev.data`; populate an agent roster strip from `/api/health.agents`. Do not refactor transport, evidence, or report rendering.
   *Verify:* browser run shows badges, the critique node with real gaps, and the roster.
10. **`web/app.css`** — badge, critique node and roster styles using existing tokens only.
    *Verify:* token audit; layouts at 1440 / 1024 / 800 px.
11. **Verification sweep** — the Acceptance Test; `BUILD1.md` → `Core Flow Test`; the three `BUILD2.md` baseline scenarios for tool-path diversity; every risk row 1-11; `ENABLE_CRITIC=0` parity check; CLI; SSE replay; anti-fabrication.
12. **Append `Stage Outcome`** to this document; update `README.md` if the run commands or feature set changed; green checkpoint `stage-3: specialized agents with critic-gated orchestration`.

### Dependency decision

**No new dependency.** `requirements.txt` stays at the seven pinned packages. Everything needed already exists: `propose_next_file`-style per-call system instructions, function-calling for structured output, and pydantic models. A framework would add hundreds of KB to replace ~70 lines of orchestration.

### Verification commands (exact)

```powershell
python -m app.config
python -c "from app.tools import get_advertised_tools; print([t['name'] for t in get_advertised_tools()])"   # must NOT contain submit_review
python -m app.agent "NVIDIA's competitive position in AI infrastructure"
python -m app.agent "CRISPR base editing off-target safety"
python -m app.agent "Quantum error correction patent landscape"
$env:ENABLE_CRITIC="0"; python -m app.agent "NVIDIA"; Remove-Item Env:\ENABLE_CRITIC   # Stage-1 parity
python -m uvicorn app.main:app --port 8000
# then: GET /api/health, POST /api/investigate, GET /api/stream/{id}, GET /api/run/{id}, GET /
```

---

## Must Remain Unchanged

`app/llm.py` in full (`propose_next_step`, `resolve_model` and its per-key cache, the `generate_content` surface, retries, the `part.thought` filter, and the existing `SYSTEM_INSTRUCTION` — which remains the Investigator's identity); `app/report.py` in full (heading splitter, grouped-citation validation, URL scrub, tier aliases, section suppression); `app/store.py`; all four provider modules and their signatures `f(query, limit)`; `TOOL_REGISTRY` and `get_advertised_tools()` membership; the four API endpoints, the SSE frame format and the `stream_end` sentinel; the three static routes; `Signal.tier` literals `high` / `important` / `emerging`; `Evidence` field names; the ReAct loop's dynamic tool selection and its budgets; the CLI entry point; `requirements.txt`; `.gitignore` secret rules; local-only git; `BUILD1.md` and `BUILD2.md`.

## Scope Cut Line

Minimum version that still satisfies "at least 2 specialized agents … meaningful collaboration": **the Lead Investigator plus the Evidence Critic, with the Critic gating completion and its gaps causing a further tool call, persisted in `Run.critiques` and visible in telemetry.** That is steps 1-5 plus step 11.

Cut in this order if the clock runs out:
1. `web/app.css` polish for the new elements (unstyled but functional is acceptable).
2. The agent roster strip in the UI (`/api/health.agents` still proves the roster to a judge).
3. Step 6, the **Report Synthesist** — drop to two agents, which still satisfies "at least 2"; the report then keeps its current behaviour exactly.
4. Step 7, the `/api/health` roster key.

**Never cut:** the Critic's structured `Critique` artifact, the completion gate, the injection of gaps back into the Investigator, `MAX_CRITIQUES` termination safety, fail-open behaviour, and the working report.

---

## Stage Outcome
