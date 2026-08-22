# AGENTX24 — Autonomous Research & Intelligence System

**AGENTX24** is an autonomous multi-agent intelligence platform designed for deep competitive tracking, academic research discovery, and strategic technology analysis. Given a user-defined objective, the system dynamically plans its search strategy, autonomously selects and executes external tools across four information domains, maintains structured context across reasoning iterations, retrieves pertinent historical findings from persistent memory, subjects findings to an independent evidence critique, and compiles an evidence-backed intelligence briefing with validated citations.

---

## Overview

Modern strategic intelligence requires synthesizing data across disconnected information silos: breaking industry news, peer-reviewed scientific literature, general web intelligence, and patent filings. Manually querying each provider, triaging hundreds of snippets, resolving conflicting signals, and drafting coherent executive summaries is time-consuming and error-prone.

AGENTX24 replaces rigid, hardcoded search pipelines with an **autonomous multi-agent system with separated responsibilities**. It executes a dynamic reasoning loop that discovers, filters, corroborates, and structures real-world intelligence in real time.

---

## The Problem

1. **Information Silos**: Breaking market events reside in news feeds, scientific breakthroughs in preprint servers, corporate overviews on the web, and technical moats in patent registries. Standard search engines lack cross-domain orchestration.
2. **Hallucination & Fabrication**: General-purpose LLMs frequently hallucinate citations, fabricate URLs, and state outdated data with false confidence.
3. **Rigid Tool Pipelines**: Hardcoded multi-step scripts call every tool regardless of relevance, wasting API bandwidth and degrading reasoning quality.
4. **Lack of Evidence Critique**: Single-agent LLM systems often accept the first superficial result they find, lacking the capacity to identify missing angles or evaluate whether collected evidence actually satisfies the original objective.
5. **Context Amnesia**: Multi-step workflows often lose intermediate discoveries or spam prompt history with unbounded raw text, degrading output quality.

---

## The Solution

AGENTX24 addresses these challenges through a unified agentic architecture:

* **Dynamic Tool Selection**: The agent autonomously determines which external tools to call turn-by-turn based on intermediate findings, rather than executing a fixed sequence.
* **Separation of Powers**: Three specialized agent roles (*Investigator*, *Critic*, and *Synthesist*) collaborate through a gated protocol to discover, audit, and structure findings.
* **Dual-Tier Context & Memory**: Short-term structured context preserves tool history and knowledge gaps across reasoning turns, while long-term persistent memory enables relevance-based continuity across investigations.
* **Anti-Fabrication Engine**: Every claim is explicitly linked to verified evidence markers (`[E1]`, `[E2]`). All citations are validated by backend code against gathered evidence, and source URLs are rendered directly from tool responses.
* **Real-Time Telemetry**: Server-Sent Events (SSE) stream the agent's internal reasoning phases, tool invocations, and critique evaluations to a real-time monitoring dashboard.

---

## Key Features

- **Autonomous Multi-Step Trajectory**: The system reasons turn-by-turn, inspecting intermediate tool outputs to determine follow-up queries.
- **Dynamic Tool Calling across 4 Domains**:
  - **News Search**: Live Google News RSS feeds with publication date parsing and freshness indicators (`days_old`).
  - **Research Search**: OpenAlex API with automatic fallback to arXiv Atom API for peer-reviewed literature.
  - **Web Search**: DuckDuckGo search with fallback to Wikipedia Search API for encyclopedic context.
  - **Patent Search**: Google Patents web-indexed database with direct patent links.
- **Specialized Multi-Agent Collaboration**:
  - `Lead Investigator`: Formulates hypotheses, executes external queries, and gathers evidence.
  - `Evidence Critic`: Evaluates evidence sufficiency and identifies missing dimensions via a dedicated function schema.
  - `Report Synthesist`: Formulates structured dossiers from verified evidence only.
- **Critic-Gated Follow-Up Inquiries**: Insufficient evidence triggers targeted follow-up searches to resolve identified knowledge gaps.
- **Bounded Short-Term Context (`InvestigationContext`)**: Preserves query history, evidence digests, and critique feedback across turns without unbounded prompt dumps.
- **Persistent Long-Term Memory (`MemoryRecord`)**: Automatically compresses and stores completed investigations in local storage (`data/investigation_memory.json`).
- **Relevance-Based Prior Memory Retrieval**: Uses Jaccard token overlap and entity matching to inject relevant historical context into new queries while ignoring unrelated topics.
- **Citation Integrity & Anti-Fabrication**: Backend validation ensures 100% genuine citations and eliminates hallucinated URLs.
- **Real-Time Telemetry Stream**: Low-latency SSE telemetry with phase indicators, agent attribution badges, and structured decision logs.
- **Interactive Web Interface**: Live timer, Decision Trace timeline, expandable evidence fragment cards, and click-to-scroll citation chips.
- **Fail-Open Resilience**: Graceful fallbacks for network interruptions, tool timeouts, and storage errors ensure uninterrupted operation.
- **LangGraph Orchestration**: The graph path provides shared state, dynamic planning, conditional routing, parallel independent tool workers, durable SQLite checkpoints, bounded replanning, conflict/uncertainty tracking, hypothesis status, resource accounting, and opt-in adversarial recovery. The original hand-written loop remains available with `ENABLE_GRAPH=0` for parity checks.

---

## Multi-Agent Architecture

AGENTX24 splits responsibilities across three dedicated LLM agent roles with strict operational guardrails:

```
                      ┌─────────────────────────┐
                      │ User Investigation Goal │
                      └────────────┬────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │    Lead Investigator    │
                      │(AgentRole.INVESTIGATOR) │
                      └────────────┬────────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
          [Dynamic Tool Selection]      [Evidence Collection]
         (news, research, web, patent)   (Normalized into E1..En)
                     │                           │
                     └─────────────┬─────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │  Investigation Context  │
                      │(Short-Term & Prior Mem) │
                      └────────────┬────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │     Evidence Critic     │
                      │   (AgentRole.CRITIC)    │
                      └────────────┬────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  ▼                                 ▼
      [Evidence Insufficient]              [Evidence Sufficient]
      • Store missing gaps                 • Approve completion
      • Recommend follow-up query          • Hand off to Synthesist
      • Loop back to Investigator                   │
                  │                                 │
                  └────────────────┐                │
                                   ▼                ▼
                      ┌─────────────────────────┐
                      │    Report Synthesist    │
                      │  (AgentRole.SYNTHESIST) │
                      └────────────┬────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │ Prioritized Dossier with│
                      │   Verified Citations    │
                      └─────────────────────────┘
```

### Specialized Agent Roster

| Agent Role | Primary Responsibility | Permitted Tools | Guardrails & Constraints |
|---|---|---|---|
| **Lead Investigator** (`investigator`) | Interprets the target, formulates inquiry angles, and queries external APIs. | `news_search`, `research_search`, `web_search`, `patent_search` | Cannot declare completion without Critic approval; cannot fabricate evidence items. |
| **Evidence Critic** (`critic`) | Evaluates evidence sufficiency against the original objective via `submit_review`. | `submit_review` (sufficiency evaluation & gap analysis) | Has NO search tools (cannot pollute evidence); fails open on error; bounded by `MAX_CRITIQUES=2`. |
| **Report Synthesist** (`synthesist`) | Compiles the final structured intelligence briefing from verified sources. | Structured synthesis (no search tools) | Strictly bounded to verified evidence; citations validated by `report.py`; zero model-generated URLs. |

---

## Context & Memory Management

AGENTX24 features a dual-tier context and memory system engineered for multi-step reasoning continuity and cross-investigation historical recall.

### 1. Short-Term Investigation Context (`InvestigationContext`)
Each investigation maintains an in-memory structured context throughout its multi-step lifecycle:
* **Target Objective & Normalized Query**: Preserved across all reasoning steps.
* **Active Agent & Phase Tracking**: Tracks state transitions between Investigator, Critic, and Synthesist.
* **Turn-by-Turn Tool History**: Logs each tool executed, exact arguments, justification reasons, and result counts to prevent redundant searches.
* **Evidence Digest**: Maintains concise summaries (`[E1] [news_search] Title (Source)`) for prompt efficiency.
* **Knowledge Gaps & Critic Logs**: Stores identified deficiencies and recommended queries from the Critic.
* **Critique Counter**: Enforces termination limits (`MAX_CRITIQUES=2`).

*Design Principle: Context is bounded and structured rather than an unconstrained chat dump, preventing context window bloat and reasoning degradation.*

### 2. Critic Feedback Continuity
When the Investigator proposes completion:
1. The Critic audits the evidence pool against the objective.
2. If critical dimensions are absent, the Critic calls `submit_review(sufficient=False, gaps=[...], recommended_query="...")`.
3. Gaps and query recommendations are stored in `InvestigationContext.knowledge_gaps` and `InvestigationContext.critic_feedback`.
4. A structured critique instruction is injected into the context, directing the Investigator to perform targeted follow-up inquiries.

### 3. Long-Term Investigation Memory (`MemoryRecord`)
Upon completion of an investigation, AGENTX24 compresses the result into a compact `MemoryRecord`:
* `memory_id`: Unique identifier (e.g., `mem_a745c394`).
* `created_at`: ISO8601 timestamp.
* `objective`: The investigation topic.
* `summary`: High-level synthesis bounded to ~350 characters.
* `key_findings`: Strategic takeaways extracted from prioritized signals.
* `entities_or_keywords`: Normalized keywords, entities, and acronyms.
* `tools_used`: Active tools that contributed evidence.
* `evidence_refs`: Evidence identifiers gathered during the run.

Memory records are saved to local atomic JSON storage (`data/investigation_memory.json`) with a sliding window of the 100 most recent records. The loader is fail-open: corrupt or missing files return an empty list without crashing.

### 4. Relevance-Based Retrieval
When a new investigation is launched:
1. The target query is tokenized into high-signal terms (excluding common stopwords).
2. A Jaccard token overlap score is computed against all stored memories, with boosts for exact phrase and entity matches.
3. Memories exceeding `min_score=0.25` are retrieved (up to `MEMORY_RETRIEVAL_LIMIT=3`). Unrelated queries receive `0` memories.
4. **Evidence Integrity Rule**: Prior memory is injected solely as inquiry context and historical hypotheses. It cannot be cited as current evidence; all claims in the active report must be backed by newly gathered tool results.

---

## Dynamic Tool Intelligence

The system dynamically routes queries across four dedicated tools:

```
                               ┌─────────────────────────────────┐
                               │       Tool Dispatcher           │
                               └────────────────┬────────────────┘
                                                │
         ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
         ▼                  ▼                   ▼                   ▼                  ▼
┌─────────────────┐┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   news_search   ││ research_search │ │   web_search    │ │  patent_search  │ │  submit_review  │
│(Google News RSS)││(OpenAlex/arXiv) │ │(DuckDuckGo/Wiki)│ │(Google Patents) │ │(Critic Internal)│
└─────────────────┘└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

1. **`news_search`**:
   - Primary: Google News RSS feeds with topic parsing.
   - Outputs: Headlines, publishers, publication dates, and computed freshness (`days_old`).
2. **`research_search`**:
   - Primary: OpenAlex REST API for peer-reviewed academic works, author affiliations, and citation metrics.
   - Fallback: arXiv Atom API for preprints across physics, computer science, and quantitative biology.
3. **`web_search`**:
   - Primary: DuckDuckGo HTML search for live web intelligence.
   - Fallback: Wikipedia Search API for encyclopedic overviews and historical context.
4. **`patent_search`**:
   - Primary: Google Patents web-indexed query parser for claims, assignees, and filing dates.
   - Modular: EPO OPS (European Patent Office) OAuth connector when configured.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Interface"]
        UI["Web Dashboard (HTML / CSS / JS)"]
        CLI["Command Line Interface (CLI)"]
    end

    subgraph Server ["FastAPI Application Backend"]
        API["FastAPI Routes (/api/investigate, /api/health)"]
        SSE["Server-Sent Events Stream (/api/stream/{id})"]
        Store["In-Memory Run Store (_RUNS)"]
    end

    subgraph Engine ["Multi-Agent Execution Engine"]
        Controller["Agent Controller (app/agent.py)"]
        LLM["Gemini 3.5 Flash Lite (app/llm.py)"]
        MemoryEngine["Memory Engine (app/memory.py)"]
        Context["InvestigationContext (app/models.py)"]
        ReportEng["Report Assembly Engine (app/report.py)"]
    end

    subgraph Tools ["External Intelligence Tools"]
        T_News["news_search (Google News)"]
        T_Research["research_search (OpenAlex / arXiv)"]
        T_Web["web_search (DuckDuckGo / Wiki)"]
        T_Patent["patent_search (Google Patents)"]
    end

    subgraph Storage ["Local Persistence"]
        MemFile[("data/investigation_memory.json")]
    end

    UI -->|POST /api/investigate| API
    UI -->|GET /api/stream/{id}| SSE
    CLI -->|Direct invocation| Controller

    API --> Controller
    Controller -->|Read / Write Context| Context
    Controller -->|Retrieve Prior Context| MemoryEngine
    MemoryEngine <--> MemFile

    Controller <-->|Prompt / Function Calling| LLM
    Controller -->|Dispatch| T_News & T_Research & T_Web & T_Patent
    T_News & T_Research & T_Web & T_Patent -->|Raw Data| Controller

    Controller -->|Broadcast Events| SSE
    Controller -->|Persist Completed Run| Store
    Controller -->|Raw Synthesis & Evidence| ReportEng
    ReportEng -->|Verified Briefing| Store
    Controller -->|Save Record| MemoryEngine
```

---

## How an Investigation Works

```
[01] User Submits Target Query (e.g. "NVIDIA Blackwell AI infrastructure moat")
      │
[02] Relevant Memory Checked (Scans local store; retrieves relevant prior investigations)
      │
[03] Lead Investigator Initializes (Ingests objective, prior context, and available tools)
      │
[04] Dynamic Tool Dispatch (Step 1: Executes news_search for market announcements)
      │
[05] Evidence Ingestion (Normalizes snippets into structured items E1..E8)
      │
[06] Gap Analysis & Follow-Up (Step 2: Identifies need for technical benchmarks; calls web_search)
      │
[07] Evidence Accumulation (Evidence items E9..E16 gathered; InvestigationContext updated)
      │
[08] Completion Proposed (Investigator signals completion)
      │
[09] Evidence Critic Gate (Critic reviews evidence; confirms sufficiency or injects gaps)
      │
[10] Report Synthesist Composes Briefing (Builds prioritized signals and sections)
      │
[11] Anti-Fabrication Validation (report.py validates citations and scrubs unverified IDs)
      │
[12] Dossier Saved to Memory (Persists compact MemoryRecord to local JSON store)
      │
[13] Live UI Delivery (Renders interactive dossier with clickable citations)
```

---

## Real-Time Agent Telemetry

The platform provides visibility into the agent's internal operations via Server-Sent Events (SSE) at `/api/stream/{run_id}`:

### Telemetry Event Structure
```json
{
  "seq": 4,
  "ts": "2026-08-22T16:06:05.123456Z",
  "phase": "Checking recent industry developments",
  "kind": "tool_selected",
  "text": "Selected news_search",
  "agent": "investigator",
  "detail": "news_search(\"NVIDIA Blackwell architecture moat\")",
  "data": {
    "tool": "news_search",
    "query": "NVIDIA Blackwell architecture moat",
    "reason": "Identify recent market disclosures regarding Blackwell cluster adoption"
  }
}
```

### Monitored Phases
- `Understanding the objective` — Initial analysis and scope definition.
- `Relevant prior context retrieved` — Historical memory hit and context injection.
- `Planning the next step` — Model reasoning over gathered findings.
- `Searching recent research / Checking news / Searching web / Searching patents` — Tool execution.
- `Evidence found` — Normalized evidence added to context.
- `Identifying knowledge gaps` — Follow-up search formulation.
- `Reviewing evidence sufficiency` — Evidence Critic evaluation.
- `Critique returned` — Critic verdict (`sufficient` / `insufficient`) and gap breakdown.
- `Investigation context updated` — Context updated with critique feedback.
- `Composing intelligence report` — Report Synthesist dossier assembly.
- `Investigation saved to memory` — Long-term persistence.
- `Completed` — Final dossier ready.

---

## Technology Stack

```
┌────────────────────────────────────────────────────────────────────────┐
│                          AGENTX24 STACK                                │
├─────────────────────────┬──────────────────────────────────────────────┤
│ Language & Runtime      │ Python 3.10+ (tested on Python 3.14)         │
│ Backend Framework       │ FastAPI, Uvicorn (ASGI)                      │
│ Reasoning Model         │ Google Gemini 3.5 Flash Lite (`google-genai`)│
│ Data Validation         │ Pydantic v2                                  │
│ HTTP & Scraping Clients │ HTTPX, Requests, Feedparser, BeautifulSoup4  │
│ Real-Time Streaming     │ Server-Sent Events (SSE) StreamingResponse   │
│ Memory Persistence      │ Local Atomic JSON Store                      │
│ Frontend Architecture   │ Vanilla HTML5, Modern CSS3 Tokens, ES6+ JS   │
└─────────────────────────┴──────────────────────────────────────────────┘
```

---

## Project Structure

```text
AGENTX24/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── agent.py             # ReAct loop controller & multi-agent orchestration
│   ├── agents.py            # Agent roster, roles, instructions & review schema
│   ├── config.py            # Environment configuration & loop budgets
│   ├── llm.py               # Google GenAI client, model resolution & retries
│   ├── main.py              # FastAPI server, REST routes & SSE streaming
│   ├── memory.py            # Context & persistent long-term memory engine
│   ├── models.py            # Pydantic data models & telemetry schemas
│   ├── report.py            # Report assembly & citation validation engine
│   ├── store.py             # In-memory run store & SSE event broadcaster
│   └── tools/
│       ├── __init__.py      # Tool registry & dispatcher
│       ├── news.py          # Google News RSS adapter
│       ├── patents.py       # Google Patents / EPO OPS adapter
│       ├── research.py      # OpenAlex & arXiv Atom adapter
│       └── web.py           # DuckDuckGo & Wikipedia adapter
├── web/
│   ├── app.css              # Custom CSS design system with token palette
│   ├── app.js               # Frontend controller, SSE listener & renderer
│   └── index.html           # Single-page intelligence workspace
├── .env.example             # Environment configuration template
├── .gitignore               # Secret hygiene & build artifact exclusion
├── README.md                # Technical system documentation
└── requirements.txt         # Pinned production dependencies
```

---

## Installation

### Prerequisites
- **Python 3.10+** (Tested on Python 3.10, 3.11, 3.12, 3.14)
- **Git**
- **Google Gemini API Key** (Obtain from [Google AI Studio](https://aistudio.google.com/))

### Step-by-Step Setup

```powershell
# 1. Clone the repository
git clone https://github.com/fakegrandpa/AGENTX24.git
cd AGENTX24

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Linux/macOS: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create local environment configuration
Copy-Item .env.example .env    # On Linux/macOS: cp .env.example .env
```

### Agent Framework Verification

```powershell
# Normal LangGraph graph execution with real Gemini/tools
.\.venv\Scripts\python.exe -m app.graph "NVIDIA AI infrastructure moat"

# Opt-in deterministic tool-failure/conflicting-evidence recovery demonstration
$env:ADVERSARIAL_MODE="1"
.\.venv\Scripts\python.exe -m app.graph "NVIDIA AI infrastructure moat"
Remove-Item Env:\ADVERSARIAL_MODE

# Legacy V3/V4 loop parity check
$env:ENABLE_GRAPH="0"
.\.venv\Scripts\python.exe -m app.agent "NVIDIA AI infrastructure moat"
Remove-Item Env:\ENABLE_GRAPH
```

Graph checkpoints are stored in `data/graph_checkpoints.sqlite` and are addressed by the
stable API run id. An interrupted run can be resumed with the additive endpoint
`POST /api/run/{run_id}/resume`.

Open `.env` and configure your Gemini API Key:
```dotenv
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

---

## Configuration

All configuration is managed through environment variables with production defaults:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | `""` | **Required**. Google Gemini API key from Google AI Studio. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Active reasoning model. |
| `MAX_ITERATIONS` | `8` | Maximum reasoning iterations per investigation. |
| `MAX_TOOL_CALLS` | `12` | Maximum external tool calls permitted per run. |
| `TOOL_TIMEOUT` | `15.0` | Timeout per external HTTP request in seconds. |
| `WALL_CLOCK` | `120.0` | Maximum investigation execution time in seconds. |
| `ENABLE_CRITIC` | `1` | Enable/disable Evidence Critic gating (`1` = enabled, `0` = disabled). |
| `MAX_CRITIQUES` | `2` | Maximum sufficiency review loops per run. |
| `ENABLE_MEMORY` | `1` | Enable/disable Stage 4 Context & Memory Management (`1` = enabled). |
| `MEMORY_RETRIEVAL_LIMIT`| `3` | Maximum number of relevant prior memories to inject. |

---

## Running AGENTX24

### 1. Web Dashboard (Interactive Mode)
```powershell
python -m uvicorn app.main:app --port 8000 --reload
```
Access the application at: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

### 2. Headless CLI (Terminal Mode)
To run an investigation directly from the command line:

```powershell
# Default target (NVIDIA)
python -m app.agent

# Custom target
python -m app.agent "CRISPR base editing off-target safety"
python -m app.agent "Quantum error correction superconducting qubits"
python -m app.agent "Solid-state battery commercialization barriers"
```

---

## API Overview

The backend exposes a clean REST and streaming API:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Returns server health, model status, active tools, agent roster, and memory statistics. |
| `POST` | `/api/investigate` | Initiates an asynchronous investigation. Body: `{"query": "string"}`. Returns `{"run_id": "string", "status": "running"}`. |
| `GET` | `/api/stream/{run_id}` | Server-Sent Events (SSE) stream delivering real-time telemetry events. |
| `GET` | `/api/run/{run_id}` | Returns the full investigation record, telemetry log, gathered evidence, critique history, and finalized report. |

---

## Example Investigation Flow

Target: **"NVIDIA's competitive position in AI infrastructure"**

1. **Memory Lookup**: `find_relevant_memories()` scans `data/investigation_memory.json` and retrieves relevant historical records on GPU datacenter architecture.
2. **Step 1 (Market Intelligence)**: Investigator selects `news_search("NVIDIA Blackwell NVL72 hyperscaler adoption")`, gathering 8 news fragments (`E1`–`E8`).
3. **Step 2 (Technical & Scientific Context)**: Investigator identifies a knowledge gap regarding hardware benchmarks and invokes `research_search("AI cluster interconnect bandwidth NVLink vs Ethernet")`, gathering 8 research papers (`E9`–`E16`).
4. **Step 3 (Critic Evaluation)**: Investigator proposes completion. The Evidence Critic reviews the 16 gathered items and verifies coverage of hardware architecture, software ecosystem (CUDA), and competitor landscape.
5. **Step 4 (Synthesis & Citation Audit)**: Report Synthesist composes the intelligence briefing. `report.py` validates all citations against `E1`–`E16`, organizes findings into strategic tiers (`HIGH`, `IMPORTANT`, `EMERGING`), and scrubs unverified claims.
6. **Step 5 (Memory Persistence)**: A compact summary is appended to `data/investigation_memory.json` for future continuity.

---

## Reliability and Guardrails

* **Hard Resource Budgets**: Hard-coded limits on iterations (`MAX_ITERATIONS=8`), tool calls (`MAX_TOOL_CALLS=12`), request timeouts (`15s`), and execution time (`120s`) prevent runaways.
* **Termination-Safe Critique Cycles**: The Critic loop is strictly bounded by `MAX_CRITIQUES=2` to eliminate infinite critique loops.
* **Defensive Fail-Open Critic**: If the Critic API call fails or times out, the system defaults to `sufficient=True` with a diagnostic note, ensuring reports are always delivered.
* **Resilient Tool Adapters**: Automatic fallbacks (OpenAlex → arXiv, DuckDuckGo → Wikipedia) prevent tool failures from halting investigations.
* **Anti-Fabrication Engine**: Model-authored URLs are scrubbed; all links are populated directly by backend code from verified tool records.

---

## Limitations

* **External API Rate Limits**: High-frequency queries may occasionally be throttled by public endpoints (e.g., DuckDuckGo or OpenAlex), in which case automated fallbacks engage.
* **Dynamic JavaScript Scraping**: Web search relies on direct HTML feeds and public APIs; pages requiring complex JavaScript execution are not rendered.
* **Static Context Limits**: Long-term memory uses local keyword/entity scoring rather than external vector embeddings, optimizing for zero-dependency portability and execution speed.

---

## Team

- **Abhale Atharv**
- **Tushar Mate**
- **Yash Supekar**
- **Gaurav Sonawane**
- **Shardul Gaikwad**

---

## Project Status

**AGENTX24** is fully operational and submission-ready:
- **Autonomous Tool Intelligence**: 4 external providers with dynamic selection.
- **Multi-Agent Orchestration**: Specialized Investigator, Critic, and Synthesist roles with critic-gated workflows.
- **Context & Memory Management**: Structured short-term context and persistent long-term memory.
- **Verified Citations**: 100% genuine evidence provenance with zero fabricated links.
