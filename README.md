# AGENTX24

**Autonomous Multi-Agent Intelligence System with Dynamic Planning, Parallel Tool Execution, and Self-Healing Graph Orchestration**

AGENTX24 is an autonomous multi-agent intelligence system that investigates complex research, technical, and market objectives. Built on a stateful **LangGraph** orchestration graph and powered by Google Gemini, the system autonomously decomposes objectives into parallel information tasks, queries real-time external providers, verifies empirical evidence, resolves factual contradictions, performs critique-gated replanning, and produces prioritized, strictly cited intelligence dossiers.

---

## 1. The Problem

Automated intelligence gathering and deep research cannot be solved by single-prompt LLM generation or static sequential workflows:

1. **Complex Information Needs:** Real-world targets require simultaneous exploration across heterogeneous domains—academic preprints, real-time news, live web sources, and patent records.
2. **Incomplete & Contradictory Evidence:** External data sources frequently return conflicting claims, stale data, or partial information that require active contradiction detection and verification.
3. **Rigid Workflows Fail:** Pre-programmed DAGs cannot pivot when an investigation reveals unexpected findings or encounters dead ends.
4. **Context & Memory Fragmentation:** Multi-turn investigations lose focus without explicit short-term context ledgers and cross-investigation historical recall.
5. **Brittle Tool Dependencies:** Network drops, rate limits, or API outages must not terminate the investigation; the agent must fail open, switch providers, or replan around the failure.
6. **Hallucination & Fabrication Risk:** Unconstrained models invent facts, citations, and URLs. Autonomous research demands strict citation safety where every assertion is backed by verifiable source records.

---

## 2. How AGENTX24 Works

AGENTX24 executes a closed-loop, self-evaluating graph lifecycle from initial objective to final synthesis:

```
                      [ User Objective ]
                              │
                              ▼
                   [ 1. Retrieve Memory ]
                 (Jaccard & Entity Matching)
                              │
                              ▼
                     [ 2. Dynamic Plan ]
              (Decompose Objective & Hypotheses)
                              │
                              ▼
                  [ 3. Lead Investigator ]
              (Select Candidate Tools & Queries)
                              │
                              ▼
                 [ 4. Parallel Dispatch ]
              (LangGraph Send() Concurrent Fan-Out)
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
          [ News Search ] [ Research ] [ Web Search ]
                └─────────────┬─────────────┘
                              ▼
                   [ 5. Collect Evidence ]
              (Normalize Items & Context Ledger)
                              │
                              ▼
                   [ 6. Detect Conflicts ]
             (Polarity & Entity Contradiction Scan)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     (Conflicts Found)                 (Clean Evidence)
              │                               │
              ▼                               ▼
    [ Resolve Conflicts ]            [ Verify Hypotheses ]
   (Preserve Uncertainty)                     │
              └───────────────┬───────────────┘
                              ▼
                   [ 7. Evidence Critic ]
             (Evaluate Sufficiency via submit_review)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     (Gaps / Insufficient)               (Sufficient)
              │                               │
              ▼                               ▼
      [ 8. Self-Evaluate ]           [ 9. Report Synthesist ]
   (Audit Budget & Loop State)      (Strict [En] Citation Check)
              │                               │
      ┌───────┴───────┐                       ▼
      ▼               ▼              [ 10. Persist Memory ]
  [ Replan ]    [ Synthesize ]     (Atomic Record Serialization)
      │               │                       │
      ▼               └───────────────┐       ▼
(New Search Cycle)                    ▼    [ END ]
(Max 3 Cycles)                  [ Intelligence Dossier ]
```

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│   Web Workspace (HTML5 / Vanilla CSS Design System / JavaScript ES6)   │
│   - Live Agent Relay Strip (Investigator → Critic → Synthesist)        │
│   - Context & Memory Ledger Strip (5 Metrics + Prior Recall Rows)       │
│   - Merged Decision Timeline & Dynamic Evidence Wall                   │
│   - Intelligence Dossier with Interactive Citation Inspector Shell     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / SSE Stream
┌───────────────────────────────────▼────────────────────────────────────┐
│                         APPLICATION API LAYER                          │
│   FastAPI Server (app/main.py)                                         │
│   - POST /api/investigate          - GET  /api/health                  │
│   - GET  /api/stream/{run_id}      - POST /api/run/{run_id}/resume     │
│   - GET  /api/run/{run_id}         - GET  /api/checkpoints/{run_id}    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    LANGGRAPH ORCHESTRATION ENGINE                      │
│   StateGraph Engine (app/graph.py)                                     │
│   - Shared Typed State: GraphState (TypedDict + Reducer Annotations)   │
│   - Durable State Checkpointer: SqliteSaver (data/checkpoints.sqlite)  │
│   - Concurrency Manager: LangGraph Send() Parallel Tool Workers        │
│                                                                        │
│   ┌─────────────────────┐   ┌─────────────────┐   ┌────────────────┐   │
│   │  LEAD INVESTIGATOR  │   │ EVIDENCE CRITIC │   │   SYNTHESIST   │   │
│   │ Dynamic Planner &   │──▶│ Sufficiency &   │──▶│ Fact-Anchored  │   │
│   │ Tool Dispatcher     │   │ Gap Evaluator   │   │ Report Writer  │   │
│   └─────────────────────┘   └─────────────────┘   └────────────────┘   │
└──────────────┬──────────────────────────────┬──────────────────────────┘
               │                              │
┌──────────────▼─────────────┐ ┌──────────────▼──────────────────────────┐
│     EXTERNAL TOOL LAYER    │ │      PERSISTENCE & REASONING LAYER      │
│ - News: Google News RSS    │ │ - Short-Term Context: InvestigationCtx  │
│ - Research: OpenAlex/arXiv │ │ - Long-Term Memory: Atomic JSON Store   │
│ - Web: DuckDuckGo/Wikipedia│ │ - Checkpoints: SQLite WAL Thread Store  │
│ - Patents: Google Patents  │ │ - Citations: Deterministic [En] Parser  │
└────────────────────────────┘ └─────────────────────────────────────────┘
```

---

## 4. Why LangGraph

LangGraph was selected and integrated to provide production-grade, stateful agent orchestration while preserving our verified multi-agent reasoning components:

| Capability | What LangGraph Provides | How AGENTX24 Implements It |
|---|---|---|
| **Explicit State Graph** | `StateGraph(GraphState)` compilation | 13 discrete nodes representing memory, planning, dispatch, verification, critique, replanning, and synthesis. |
| **Concurrent Execution** | `Send("worker_node", payload)` fan-out | Dispatches up to 3 independent tool queries simultaneously; results aggregate into shared state via `Annotated[list, add]`. |
| **Durable Checkpointing** | `SqliteSaver` checkpointer interface | Every graph step is saved to `data/graph_checkpoints.sqlite` with thread IDs, enabling pause, state inspection, and resumption. |
| **Conditional Routing** | `add_conditional_edges()` | Edge routers evaluate task queues, critique verdicts, conflict status, and resource budgets to branch dynamically. |
| **Cycle & Loop Bounds** | Graph recursion limits and state tracking | Prevents runaway executions using explicit replan counters, budget checks, and SHA1-based query signature tracking. |

---

## 5. The Agent System

AGENTX24 operates through three specialized agent roles with strict separation of concerns:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SPECIALIZED AGENT ROSTER                        │
├──────────────────┬──────────────────┬──────────────────────────────────┤
│ Agent            │ Primary Tools    │ Core Responsibility              │
├──────────────────┼──────────────────┼──────────────────────────────────┤
│ Lead             │ news_search      │ Analyzes the target objective,   │
│ Investigator     │ research_search  │ decomposes needs into tasks,     │
│                  │ web_search       │ generates search hypotheses, and │
│                  │ patent_search    │ selects appropriate tools.       │
├──────────────────┼──────────────────┼──────────────────────────────────┤
│ Evidence         │ submit_review    │ Evaluates evidence sufficiency,  │
│ Critic           │ (No external     │ identifies knowledge gaps, and   │
│                  │ search tools)    │ recommends targeted queries.     │
├──────────────────┼──────────────────┼──────────────────────────────────┤
│ Report           │ None (Restricted │ Composes prioritized reports     │
│ Synthesist       │ to verified state│ strictly from collected evidence │
│                  │ evidence)        │ with validated [En] citations.   │
└──────────────────┴──────────────────┴──────────────────────────────────┘
```

### Lead Investigator
* **Role:** Exploration & Task Execution.
* **Operation:** Prompts Gemini with dynamic tool declarations (`app/tools/__init__.py`), formulates search arguments, and specifies explicit technical justifications (`reason`) for every query.

### Evidence Critic
* **Role:** Quality Assurance & Gating.
* **Operation:** Has **no external search tools**. Evaluates existing evidence against the original objective using structured function calling (`submit_review`). If evidence is insufficient, it names 1–3 concrete knowledge gaps and recommends specific follow-up queries.
* **Fail-Open Design:** If the Critic encounters an unexpected API exception, it defaults to `sufficient: true` to prevent workflow deadlocks.

### Report Synthesist
* **Role:** Fact-Anchored Dossier Composition.
* **Operation:** Translates gathered evidence into a structured intelligence dossier across standardized signal tiers. Operates under strict anti-fabrication constraints: all claims must cite valid evidence IDs `[E1]`, and model-generated URLs are stripped.

---

## 6. Dynamic Investigation Engine

### Dynamic Planning
Upon receiving an objective, the planner node analyzes the inquiry against any retrieved historical context. It emits a prioritized task queue and testable hypotheses:
```json
{
  "tasks": [
    {"id": "task_1", "objective": "recent production updates", "candidate_tools": ["news_search"], "priority": 1},
    {"id": "task_2", "objective": "electrolyte degradation mechanisms", "candidate_tools": ["research_search"], "priority": 2}
  ],
  "hypotheses": [
    {"id": "h1", "claim": "Interface degradation remains the primary failure mode in solid-state cells."}
  ]
}
```

### Adaptive Task Decomposition
Different inquiries produce entirely distinct execution graphs:
* *Corporate & Market Inquiries:* Prioritize news feeds, executive announcements, and web intelligence.
* *Scientific & Deep-Tech Inquiries:* Prioritize OpenAlex and arXiv preprints, technical whitepapers, and patent filings.
* *Patent & IP Inquiries:* Automatically advertise and route queries through patent search when credentials/queries require IP validation.

### Autonomous Replanning
When the Evidence Critic identifies gaps or when a tool encounters an outage, the system replans without human intervention:
1. **Tool Failure Trigger:** If a provider fails, the graph generates an alternative task targeting a secondary provider.
2. **Critic Gap Trigger:** Critic gaps are injected into the task queue, decrementing `replans_remaining` and prompting the Investigator to pursue missing angles.
3. **Contradiction Trigger:** Conflicting evidence prompts a focused verification task to cross-examine disputed claims.

---

## 7. Parallel Execution

AGENTX24 implements dynamic parallel tool execution using LangGraph's `Send` API:

```
                     [ Investigator Node ]
                 (Selects N Independent Calls)
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
     Send(Worker 1)    Send(Worker 2)    Send(Worker 3)
     [news_search]   [research_search]    [web_search]
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                 [ State Reducer (add) ]
               worker_results: Annotated[list, add]
                              │
                              ▼
                   [ Collect Evidence Node ]
               (Sequential State Normalization)
```

* **Safe State Aggregation:** Worker results are isolated and merged into `worker_results` using list addition reducers before atomic normalization in `collect_evidence`.
* **Resource Bounds:** Parallel dispatch is capped by `PARALLEL_TOOL_CALLS = 3` to prevent rate-limit exhaustion.

---

## 8. Evidence, Conflicts & Hypotheses

### Evidence Normalization
Every search result is normalized into a structured `Evidence` record containing:
* Unique sequential ID (`E1`, `E2`, etc.)
* Provider metadata (`provider`, `provider_kind`, `source`, `url`)
* Temporal recency (`published`, `days_old`)
* Snippet and domain-level corroboration scores

### Conflict Detection & Resolution
* **Polarity & Keyword Analysis:** `detect_conflicts` compares evidence pairs across shared entities and opposing semantic sentiment (e.g., *growth/adoption* vs. *decline/failure*).
* **Uncertainty Tracking:** Conflicting pairs are flagged with unique digests and recorded in `GraphState.conflicts`. If unresolvable within budget, the conflict is preserved as `high` uncertainty and explicitly documented in the report's limitations.

### Hypothesis Verification
Hypotheses generated during planning are audited against collected evidence:
* **SUPPORTED:** Empirical evidence corroborates the hypothesis.
* **UNCERTAIN:** Evidence is inconclusive or missing, increasing the uncertainty score.

---

## 9. Memory & Context Management

```
┌────────────────────────────────────────────────────────────────────────┐
│                     DUAL-TIER MEMORY ARCHITECTURE                      │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Short-Term Investigation Context │ Long-Term Investigation Memory      │
├──────────────────────────────────┼─────────────────────────────────────┤
│ - Scope: Single run lifecycle    │ - Scope: Persistent across runs     │
│ - Structure: Pydantic Model      │ - Storage: data/investigation_      │
│   (InvestigationContext)         │   memory.json (Atomic JSON)         │
│ - Tracks: Active agent, tool     │ - Retrieval: Jaccard token overlap  │
│   history, evidence summaries,   │   + alphanumeric entity matching    │
│   knowledge gaps, critiques      │ - Threshold: Jaccard >= 0.25        │
│ - Telemetry: Emitted on every    │ - Isolation: Historical only;       │
│   agent transition               │   cannot be cited as fresh facts    │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### Durable Checkpointing
In addition to memory, LangGraph checkpoints the entire execution state after every node transition to SQLite (`data/graph_checkpoints.sqlite`). An interrupted investigation can be resumed at any time using `POST /api/run/{run_id}/resume`.

---

## 10. Failure Recovery & Resilience

AGENTX24 is engineered to survive partial system failures without crashing:

```
[ Primary Tool Call (e.g., OpenAlex) ]
                 │
           (HTTP Timeout)
                 │
                 ▼
[ Secondary Adapter Fallback (arXiv Atom API) ]
                 │
           (HTTP Timeout)
                 │
                 ▼
[ Graph Fallback: Emit SOURCE_UNAVAILABLE ]
                 │
                 ▼
[ Append to run.limitations & Generate Recovery Task ]
                 │
                 ▼
[ Replan with Web/News Search & Complete Investigation ]
```

* **Multi-Tier Tool Adapters:** Research tool automatically falls back across OpenAlex → arXiv → Semantic Scholar. Web search falls back across DuckDuckGo → Wikipedia API.
* **Corrupt Store Resilience:** If memory or checkpoint files are malformed, the loaders log a warning and fall back to clean empty states.
* **Graceful Degradation:** If model synthesis fails, the system renders all verified evidence records directly so no gathered intelligence is lost.

---

## 11. Loop & Resource Management

To ensure deterministic termination within hackathon constraints:

1. **Query Signature Hashing:** Every tool query is hashed (`SHA1(tool:query)`). Identical repeated queries are tracked in `loop_signatures`.
2. **No-Progress Detection:** If two consecutive turns yield zero new evidence, `PhaseEnum.LOOP_DETECTED` is emitted and the planner is forced to change tools or synthesize.
3. **Hard Budgets:**
   * `MAX_ITERATIONS = 8`
   * `MAX_TOOL_CALLS = 12`
   * `MAX_CRITIQUES = 2`
   * `MAX_REPLANS = 3`
   * `WALL_CLOCK = 120.0s`

---

## 12. Adversarial Recovery Test

AGENTX24 includes an opt-in adversarial test harness (`app/adversarial.py`) to demonstrate live fault tolerance, conflict detection, and autonomous recovery:

### Adversarial Execution Trace
```powershell
# Run the adversarial verification command
.\.venv\Scripts\python.exe -c "import app.graph; res = app.graph.run_graph('NVIDIA Blackwell Moat', adversarial=True); print('Status:', res.status, '| Conflicts:', len(res.conflicts), '| Limitations:', len(res.limitations), '| Signals:', len(res.report.signals))"
```

### Observed Adversarial Lifecycle
1. **Fault Injected:** `news_search` simulates a network timeout; `research_search` simulates a service outage.
2. **Conflict Injected:** `web_search` receives a synthetic contradictory evidence record.
3. **Fault Handled:** Faults are captured; `collect_evidence` records tool limitations and dispatches fallback tasks.
4. **Conflict Detected:** `detect_conflicts` flags the contradiction (`CONFLICT_DETECTED`).
5. **State Transition:** `resolve_conflicts` marks the conflict as `PARTIALLY_RESOLVED` and updates uncertainty to `high`.
6. **Autonomous Recovery:** The graph completes all 35 node transitions and outputs a fully cited dossier with 8 prioritized signals.

---

## 13. Tools & Data Sources

| Tool | Primary Provider | Fallback Provider | Data Collected |
|---|---|---|---|
| `news_search` | Google News RSS | Feedparser Text Extraction | Real-time industry announcements, corporate developments, breaking news. |
| `research_search`| OpenAlex REST API | arXiv Atom API / Semantic Scholar | Academic preprints, peer-reviewed methodology, citation counts. |
| `web_search` | DuckDuckGo (`ddgs`) | Wikipedia Search API | Broad web intelligence, documentation, company overviews. |
| `patent_search` | Google Patents | In-Memory Patent Parser | IP filings, patent abstracts, claims, filing dates. |

*Tool selection is strictly dynamic—the agent selects only the tools relevant to the objective.*

---

## 14. Live Observability & UI

The web interface (`http://127.0.0.1:8000/`) provides real-time visibility into the multi-agent graph:

* **Agent Relay Strip:** Live status stations for `Lead Investigator`, `Evidence Critic`, and `Report Synthesist` (`STANDBY`, `ACTIVE`, `HANDED OFF`, `COMPLETE`).
* **Context & Memory Ledger:** Live counters for prior memory hits, verified evidence items, knowledge gaps, and memory writes.
* **Merged Decision Timeline:** Visualizes tool dispatches (`DISPATCHING…` → `RETURNED · N` / `UNAVAILABLE`).
* **Interactive Citation Inspector:** Hovering over any `[En]` chip displays an evidence inspection card with the verified title, source, publication date, and snippet.

---

## 15. Project Structure

```text
AGENTX24/
├── app/
│   ├── graph.py             # LangGraph StateGraph, 13 nodes, checkpointer, and runner
│   ├── agent.py             # Agent interface, legacy fallback loop, and CLI runner
│   ├── agents.py            # Agent roster definitions, system prompts, and Critic review schema
│   ├── models.py            # Pydantic data models (Run, Evidence, Context, Telemetry)
│   ├── memory.py            # Long-term memory storage, Jaccard keyword & entity relevance
│   ├── adversarial.py       # Deterministic fault & conflict injection harness
│   ├── llm.py               # Google GenAI SDK interface, model resolution, and preflight
│   ├── report.py            # Report assembler, citation validator, and corroboration scorer
│   ├── store.py             # In-memory run store and SSE subscription queues
│   ├── config.py            # Environment configuration, timeouts, and execution budgets
│   └── tools/               # External provider tool adapters
│       ├── __init__.py      # Tool registry and argument validation
│       ├── news.py          # Google News RSS adapter
│       ├── research.py      # OpenAlex & arXiv Atom adapter
│       ├── web.py           # DuckDuckGo & Wikipedia API adapter
│       └── patents.py       # Google Patents adapter
├── web/
│   ├── index.html           # Single-page intelligence workspace UI
│   ├── app.css              # Editorial design system & responsive typography
│   └── app.js               # Event-driven SSE client, state machine, and citation inspector
├── data/
│   ├── investigation_memory.json  # Persistent long-term memory store
│   └── graph_checkpoints.sqlite   # SQLite durable checkpointer database
├── requirements.txt         # Pinned production dependencies
├── .env.example             # Template for API keys and configuration
└── README.md                # Comprehensive technical documentation
```

---

## 16. Installation & Quick Start

### Prerequisites
* Python 3.10 to 3.14
* Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 1. Clone & Setup Environment
```powershell
git clone https://github.com/fakegrandpa/AGENTX24.git
cd AGENTX24

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment
```powershell
cp .env.example .env
# Edit .env and insert your GEMINI_API_KEY
```

### 4. Start the Application Server
```powershell
python -m uvicorn app.main:app --port 8000 --reload
```

Open your browser at: **`http://127.0.0.1:8000/`**

---

## 17. Configuration Reference

| Variable | Description | Default | Required |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | None | **Yes** |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.5-flash-lite` | No |
| `ENABLE_GRAPH` | Enable LangGraph orchestration | `1` | No |
| `ENABLE_CRITIC` | Enable Evidence Critic review gate | `1` | No |
| `ENABLE_MEMORY` | Enable short/long-term memory engine | `1` | No |
| `ADVERSARIAL_MODE` | Enable fault & conflict injection | `0` | No |
| `PARALLEL_TOOL_CALLS` | Maximum concurrent tool worker threads | `3` | No |
| `GRAPH_CHECKPOINT_PATH` | Path to SQLite checkpointer database | `data/graph_checkpoints.sqlite` | No |
| `MEMORY_STORAGE_PATH` | Path to persistent memory JSON file | `data/investigation_memory.json` | No |

---

## 18. Running Investigations

### Option A: Web Dashboard (Interactive)
1. Navigate to `http://127.0.0.1:8000/`.
2. Enter an investigation objective or click a suggested prompt.
3. Observe live agent transitions, parallel tool executions, and the synthesized report.

### Option B: Headless CLI Runner
```powershell
python -m app.agent "NVIDIA competitive strategy & AI hardware moat"
```

### Option C: REST API
```powershell
# Dispatch run
$run = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/investigate" `
  -ContentType "application/json" `
  -Body '{"query": "Solid-State Battery Degradation", "adversarial": false}'

# Fetch result
Invoke-RestMethod "http://127.0.0.1:8000/api/run/$($run.run_id)"
```

---

## 19. Requirement Coverage Matrix

| Hackathon Requirement | AGENTX24 Architectural Implementation | Status |
|---|---|---|
| **Agentic Framework** | Native `langgraph` StateGraph with 13 functional nodes and SQLite saver. | **VERIFIED** |
| **Dynamic Planning** | `plan` node prompts Gemini with `submit_plan` to generate prioritized task lists. | **VERIFIED** |
| **Multi-Agent Orchestration** | Distinct nodes for `investigator`, `critic`, and `synthesist` with dedicated prompts. | **VERIFIED** |
| **Conditional Routing** | 4 graph routing functions (`route_after_plan`, `route_after_critic`, etc.). | **VERIFIED** |
| **Parallel Execution** | `dispatch_workers` emits `Send("parallel_tool_worker", ...)` for concurrent execution. | **VERIFIED** |
| **Shared State** | `GraphState` TypedDict with reducer annotations for thread-safe state merging. | **VERIFIED** |
| **Checkpointing & Resume** | `SqliteSaver` persists state transitions; resumable via `/api/run/{id}/resume`. | **VERIFIED** |
| **Autonomous Replanning** | `replan` node generates follow-up tasks based on Critic feedback or tool errors. | **VERIFIED** |
| **Failure Recovery** | Tool fallbacks across providers, fail-open Critic, and limitation recording. | **VERIFIED** |
| **Tool Fallback** | Multi-tier adapters (OpenAlex → arXiv, DuckDuckGo → Wikipedia). | **VERIFIED** |
| **Conflict Resolution** | `detect_conflicts` finds contradictions; `resolve_conflicts` tracks uncertainty. | **VERIFIED** |
| **Uncertainty Awareness** | Uncertainty scores (`low`/`medium`/`high`) dynamically alter routing decisions. | **VERIFIED** |
| **Resource Awareness** | Dynamic `resource_ledger` enforces hard tool and iteration limits. | **VERIFIED** |
| **Self-Evaluation** | `self_evaluate` node audits progress and budget to branch to replan or synthesis. | **VERIFIED** |
| **Hypothesis Verification** | `verify_hypotheses` node audits claims against empirical evidence. | **VERIFIED** |
| **Memory Reasoning** | Jaccard + entity relevance retrieval from persistent multi-run memory. | **VERIFIED** |
| **Loop / Deadlock Detection** | SHA1 query signature tracking and consecutive zero-evidence loop breaker. | **VERIFIED** |
| **Adaptive Decomposition** | Target-specific task graphs dynamically tailored to market, tech, or IP domains. | **VERIFIED** |
| **Adversarial Testing** | Opt-in deterministic fault & contradiction harness in `app/adversarial.py`. | **VERIFIED** |

---

## 20. Verification & Test Suite

All system capabilities were validated through automated execution tests:

```powershell
# 1. Module & Framework Import Safety
python -c "import app.main, app.graph; print('All modules imported successfully')"

# 2. Configuration & Preflight Health Check
python -m app.config
Invoke-RestMethod http://127.0.0.1:8000/api/health

# 3. Live LangGraph Execution Test
python -m app.graph "NVIDIA Blackwell Moat"

# 4. Live Adversarial Fault & Conflict Recovery Test
python -c "import app.graph; res = app.graph.run_graph('Quantum Computing Scalability', adversarial=True); print('Status:', res.status, '| Conflicts:', len(res.conflicts), '| Evidence:', len(res.evidence))"

# 5. Checkpoint Durability Test
python -c "import sqlite3; conn = sqlite3.connect('data/graph_checkpoints.sqlite'); cur = conn.cursor(); cur.execute('SELECT count(*) FROM checkpoints'); print('Durable checkpoints:', cur.fetchone()[0])"
```

---

## 21. Evaluation Harness & Measurable Criteria (Stage 6)

AGENTX24 features a dedicated, offline evaluation harness under `eval/` that measures multi-agent intelligence performance across **6 core dimensions** and **19 deterministic metrics**:

1. **Accuracy & Groundedness**: Grounded citation rate (`>= 95%`), citation density, evidence utilisation, unsupported claim rate, and blocked fabrication attempts.
2. **Task Completion**: Synthesis completion rate (`>= 90%`), section population, and signal count.
3. **Reliability & Consistency**: Multi-run stability, evidence count variance, signal count variance, and tool selection Jaccard similarity.
4. **Robustness & Recovery**: Failure recovery rate (`>= 75%`), adversarial conflict detection, calibrated uncertainty identification, and honest refusal on fictitious subjects.
5. **Evidence Quality**: Multi-source provider diversity, provider kinds covered (news, research, web, patent), publication recency, and cross-source corroboration.
6. **Efficiency**: Wall-clock latency (`<= 120s`), total tool latency, LLM call budget consumption (`<= 14`), and resource efficiency ratio.

### Running Automated Evaluations

```powershell
# 1. Inspect criteria definitions, dimensions, and human rubrics
python -m eval.criteria

# 2. Inspect declarative scenario suites and projected run counts
python -m eval.scenarios

# 3. Run the standard Quick Evaluation Suite (5 scenarios, isolated memory)
python -m eval.runner --suite quick

# 4. Run the complete Full Evaluation Suite (6 scenarios including ablations)
python -m eval.runner --suite full --yes

# 5. Run a single target scenario (e.g. adversarial recovery or incomplete refusal)
python -m eval.runner --scenario adversarial
python -m eval.runner --scenario incomplete

# 6. Re-generate a Markdown scorecard from existing run artifacts offline
python -m eval.scorecard eval/results/<timestamp>/metrics.json
```

### Generated Evaluation Artifacts

* `eval/results/<timestamp>/runs/*.json`: Full standalone serialized `Run` records for every executed scenario and repeat.
* `eval/results/<timestamp>/metrics.json`: Aggregated metrics, per-scenario evaluations, multi-run consistency scores, and baseline delta.
* `eval/results/<timestamp>/scorecard.md`: Formatted publication-ready evaluation report with automated summary tables, baseline comparisons, and the unfilled human evaluation rubric.

---

## License

MIT License. Built for the AGENTX24 Autonomous Agents Hackathon.
