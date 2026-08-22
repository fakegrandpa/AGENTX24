# AGENTX24

**AGENTX24** is an autonomous intelligence system that investigates user-defined strategic objectives, dynamically selects external information tools, rigorously evaluates evidence through specialized multi-agent collaboration, maintains bounded investigation context across multi-step reasoning turns, retrieves relevant prior knowledge from persistent memory, and produces a verified, prioritized executive intelligence briefing.

---

## Problem Statement

Users often need to investigate complex topics, competitive moves, market shifts, and emerging scientific breakthroughs across fragmented information sources, including:

- **Industry & Competitor News**: Tracking real-time corporate announcements, executive shifts, earnings calls, and product launches.
- **Academic & Scientific Literature**: Identifying breakthroughs, preprints, and peer-reviewed journals across OpenAlex and arXiv.
- **Live Web Intelligence**: Gathering general technical overviews, encyclopedic summaries, and background context via web and Wikipedia search.
- **Patent & IP Landscapes**: Uncovering filings, claims, assignees, and intellectual property trajectories.

Manual investigation across these domains is tedious, fragmented, and prone to oversight. It requires researchers to repeatedly decide what to search for, evaluate conflicting evidence, identify missing knowledge, and synthesize findings into an actionable report. 

**AGENTX24** solves this by uniting autonomous tool selection, specialized multi-agent roles with separated powers, evidence critique, short-term context management, persistent long-term investigation memory, and structured anti-fabrication report synthesis into a single, cohesive workflow.

---

## Key Features

- **Autonomous Multi-Step Investigation**: Evaluates intermediate observations and autonomously formulates search queries without hardcoded trajectories.
- **Dynamic External Tool Selection**: Autonomously queries news, research papers, web pages, and patent records based on the investigation target.
  - **News Search**: Live Google News RSS feeds with date parsing and freshness indicators (`days_old`).
  - **Research Search**: Live OpenAlex API queries with automatic fallback to arXiv Atom API.
  - **Web Search**: DuckDuckGo search with resilient fallback to Wikipedia Search API.
  - **Patent Search**: Google Patents web-indexed database with direct patent links.
- **Specialized Multi-Agent Collaboration**:
  - **Lead Investigator**: Understands objectives, identifies knowledge gaps, and dynamically gathers external evidence.
  - **Evidence Critic**: Independently gates completion, evaluates evidence sufficiency, and identifies missing knowledge.
  - **Report Synthesist**: Composes structured, prioritized intelligence dossiers strictly from verified sources.
- **Critic-Gated Follow-Up Investigation**: If evidence is evaluated as insufficient, missing gaps are stored in context and fed back to drive targeted follow-up queries.
- **Short-Term Context Management (`InvestigationContext`)**: Maintains bounded, structured context per run (tools used, query logs, evidence digests, knowledge gaps, Critic feedback).
- **Persistent Long-Term Memory (`MemoryRecord`)**: Persists completed investigation summaries and key findings to local storage (`data/investigation_memory.json`).
- **Relevance-Based Prior Memory Retrieval**: Automatically retrieves relevant past investigations using keyword and entity overlap scoring while ignoring unrelated queries.
- **Strict Anti-Fabrication Safeguards**: Every claim is cited with bracketed markers (`[E1]`, `[E2]`). All citations are validated against collected evidence, and source URLs are rendered directly by backend code.
- **Real-Time Telemetry & SSE Stream**: Live Server-Sent Events stream reasoning phases with color-coded agent badges (`[INVESTIGATOR]`, `[CRITIC]`, `[SYNTHESIST]`) to the frontend dashboard.
- **Interactive Investigation Interface**: Responsive UI with live timer, decision timeline, expandable evidence cards, and interactive scroll-to-source citation chips.

---

## Multi-Agent Architecture

AGENTX24 employs a multi-agent architecture with separated powers orchestrated via a bidirectional ReAct loop:

```text
User Objective
      │
      ▼
Lead Investigator (AgentRole.INVESTIGATOR)
  • Understands investigation target & formulates hypotheses
  • Receives short-term InvestigationContext & prior memory
  • Autonomously selects external tools (news, research, web, patents)
  • Gathers and normalizes verified evidence
      │
      ▼
Evidence Critic (AgentRole.CRITIC) — Critic-Gated Orchestration
  • Evaluates evidence sufficiency against objective via `submit_review`
  • Has NO data-gathering tools (cannot pollute evidence)
  • Identifies concrete missing angles and recommends follow-up queries
      │
      ├── [Evidence INSUFFICIENT & within budget]
      │         │
      │         ▼
      │   Knowledge gaps stored in InvestigationContext
      │         │
      │         ▼
      └── Lead Investigator Follow-Up (Performs targeted inquiries)
                │
                ▼ [Evidence SUFFICIENT or budget reached]
Report Synthesist (AgentRole.SYNTHESIST)
  • Composes final prioritized intelligence report from verified evidence only
  • Follows strict heading schemas parsed by report.py
  • Zero model-generated URLs or unverified citations
```

### Specialized Agent Roster

| Agent Role | System Responsibility | Permitted Capabilities | Guardrails |
|---|---|---|---|
| **Lead Investigator** (`investigator`) | Understands objective, formulates search strategies, and dynamically queries external information sources. | `news_search`, `research_search`, `web_search`, `patent_search` | Cannot declare completion without Critic verification; cannot fabricate evidence. |
| **Evidence Critic** (`critic`) | Gates completion by evaluating whether the gathered evidence pool sufficiently covers all dimensions of the objective. | `submit_review` (sufficiency evaluation & gap analysis) | Has NO data-gathering tools (cannot pollute evidence); fails open on errors; bounded by `MAX_CRITIQUES=2`. |
| **Report Synthesist** (`synthesist`) | Composes the final executive intelligence briefing with prioritized signals and citations. | Structured report synthesis | Cannot introduce external unverified facts or URLs; citations validated by `report.py`. |

---

## Context & Memory Management

AGENTX24 implements a dual-tier memory system designed for multi-step reasoning continuity and longitudinal investigation memory:

### 1. Short-Term Investigation Context

Every investigation run initializes and maintains a structured [`InvestigationContext`](file:///d:/AGENTX24/app/models.py) across all turns:
- **Investigation Objective & Normalized Target**
- **Current Phase & Active Agent** (`INVESTIGATOR`, `CRITIC`, `SYNTHESIST`)
- **Turn-by-Turn Tool History**: Records every tool called, search query, justification reason, status, and result count (preventing redundant queries).
- **Evidence Digest**: Compact summaries (`[E1] [news_search] Title (Source)`).
- **Identified Knowledge Gaps**: Specific missing information angles.
- **Critic Feedback Log**: Structured verdicts, gap lists, and recommended queries.
- **Critique Count**: Bounded counter enforcing `MAX_CRITIQUES=2` termination safety.
- **Prior Memories**: Relevant historical records retrieved for the run.

*Note: Context is curated and bounded rather than continuously appending unlimited raw LLM chat history, ensuring high signal-to-noise ratio.*

### 2. Critic Feedback Continuity

When the Lead Investigator proposes completion:
1. The **Evidence Critic** reviews the evidence pool against the objective.
2. If gaps remain, the Critic calls `submit_review(sufficient=False, gaps=[...], recommended_query="...")`.
3. The gaps and recommendations are stored directly into `InvestigationContext.knowledge_gaps` and `InvestigationContext.critic_feedback`.
4. A concise critique instruction is injected into the conversation history, enabling the **Lead Investigator** to execute a targeted follow-up search turn.
5. Context cleanly survives and bridges across these multiple reasoning steps.

### 3. Long-Term Investigation Memory

Upon completion of a successful run, AGENTX24 compresses the result into a compact [`MemoryRecord`](file:///d:/AGENTX24/app/models.py):
- `memory_id`: Unique identifier (e.g. `mem_7326c43f`).
- `created_at`: Timestamp.
- `objective`: Original target query.
- `summary`: Concise investigation summary (bounded to ~350 chars).
- `key_findings`: Top strategic findings extracted from report signals.
- `entities_or_keywords`: Normalized keywords, entities, and acronyms.
- `tools_used`: External tools that produced results.
- `evidence_refs`: Evidence IDs collected during the investigation.
- `signal_count`: Total strategic signals identified.

Records are persisted to local JSON storage (`data/investigation_memory.json`) with atomic writes and bounded history (up to 100 recent investigations). If storage is corrupt or missing, the system fails open gracefully without interrupting execution.

### 4. Relevance-Based Retrieval

When a new investigation begins:
1. **Keyword Extraction**: The target query is tokenized into high-signal terms (excluding common English stopwords).
2. **Relevance Scoring**: Jaccard token overlap is computed against all stored memory records, boosted by exact phrase and entity matches.
3. **Thresholding**: Only memories exceeding `min_score=0.25` are retrieved (capped at `MEMORY_RETRIEVAL_LIMIT=3`). Unrelated queries receive `0` memories.
4. **Context Injection**: Retrieved memories are formatted into a concise prior context block for the Lead Investigator.
5. **Evidence Integrity Rule**: **Prior memory is strictly context, NOT verified current evidence.** The agent is instructed that prior memory provides historical continuity and hypotheses only; all current report claims must be supported by fresh evidence gathered in the current run.

### Visual Architecture Diagram

```text
New Investigation Target
        │
        ▼
Retrieve Relevant Prior Memory (Keyword & Entity Match)
        │
        ▼
Structured InvestigationContext (Initialized)
        │
        ▼
Lead Investigator (Formulates search queries)
        │
        ▼
External Tools (news, research, web, patents)
        │
        ▼
Evidence Critic (Evaluates sufficiency)
        │
        ├── Evidence insufficient & within budget
        │       │
        │       ▼
        │   Knowledge gaps stored in InvestigationContext
        │       │
        │       ▼
        └── Targeted Follow-Up Investigation
                │
                ▼ Evidence sufficient / budget reached
        Report Synthesist
                │
                ▼
        Final Intelligence Report (Validated Citations)
                │
                ▼
        Persistent Memory Record (Saved to data/investigation_memory.json)
```

---

## External Tools

AGENTX24 integrates 4 real-world external intelligence providers:

1. **`news_search` (Industry & Competitor News)**:
   - Queries **Google News RSS** with topic-tailored feeds.
   - Extracts article headlines, sources, publication dates, and calculates `days_old` freshness.
2. **`research_search` (Academic & Scientific Literature)**:
   - Queries **OpenAlex API** for peer-reviewed research, authors, venues, and citation counts.
   - Automatically falls back to **arXiv Atom API** for preprints and scientific literature.
3. **`web_search` (Live Web & Reference Intelligence)**:
   - Performs live web search via **DuckDuckGo**.
   - Resiliently falls back to **Wikipedia API** for foundational entity overviews.
4. **`patent_search` (Patent Records & IP Filings)**:
   - Queries web-indexed **Google Patents** database, returning titles, assignees, publication dates, and direct links.
   - Modular support for **EPO OPS** (European Patent Office) OAuth credentials when provided.

---

## Technology Stack

- **Backend Framework**: Python 3.10+, FastAPI, Uvicorn
- **AI / LLM Engine**: Google Gemini 3.5 Flash Lite via `google-genai` SDK
- **Data Validation & Schemas**: Pydantic v2
- **Network & API Clients**: HTTPX, Requests, Feedparser, BeautifulSoup4
- **Real-Time Streaming**: Server-Sent Events (SSE) via `StreamingResponse`
- **Frontend Dashboard**: HTML5, Vanilla CSS3 (Custom Design System with Token Palette), Vanilla JavaScript (ES6+)
- **Memory Persistence**: Local Atomic JSON Storage (`data/investigation_memory.json`)

---

## Installation

### Step-by-Step Setup (Windows PowerShell / Bash)

```powershell
# 1. Clone the repository
git clone https://github.com/fakegrandpa/AGENTX24.git
cd AGENTX24

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Linux/macOS: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
Copy-Item .env.example .env    # On Linux/macOS: cp .env.example .env
```

Open `.env` and insert your Gemini API Key:
```dotenv
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

### Running the Application

```powershell
# Start the FastAPI Web Dashboard
python -m uvicorn app.main:app --port 8000 --reload
```

Open your browser at: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## Configuration

All configuration is managed via `.env` with sensible defaults:

| Variable | Default Value | Description |
|---|---|---|
| `GEMINI_API_KEY` | `""` | **Required**. Google Gemini API key from Google AI Studio. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Active Gemini reasoning model. |
| `MAX_ITERATIONS` | `8` | Maximum reasoning iterations allowed per run. |
| `MAX_TOOL_CALLS` | `12` | Hard limit on total external tool invocations per run. |
| `TOOL_TIMEOUT` | `15.0` | Individual external tool request timeout in seconds. |
| `WALL_CLOCK` | `120.0` | Maximum wall-clock time in seconds for an investigation run. |
| `ENABLE_CRITIC` | `1` | Enable/disable Evidence Critic gating (`1` = enabled, `0` = disabled). |
| `MAX_CRITIQUES` | `2` | Maximum sufficiency review loops permitted before forced synthesis. |
| `ENABLE_MEMORY` | `1` | Enable/disable Stage 4 Context & Memory Management (`1` = enabled). |
| `MEMORY_RETRIEVAL_LIMIT` | `3` | Maximum number of relevant prior memories to inject. |

---

## How It Works

1. **User enters an investigation objective**: Submitted via web dashboard or CLI.
2. **Relevant prior memory is checked**: `find_relevant_memories()` scans `investigation_memory.json` using keyword/entity matching.
3. **Lead Investigator begins investigation**: Ingests the objective and any relevant prior context.
4. **Relevant tools are dynamically selected**: The Investigator evaluates findings turn-by-turn and dispatches external tools.
5. **Evidence is collected**: Live APIs return structured evidence items (`[E1]`, `[E2]`, etc.).
6. **InvestigationContext is updated**: Tool history, query parameters, reasons, and evidence summaries are updated.
7. **Evidence Critic evaluates sufficiency**: Reviews evidence against the objective using `submit_review`.
8. **Knowledge gaps trigger follow-up**: If insufficient, gaps are stored in context and fed back to the Investigator for another search turn.
9. **Report Synthesist creates the final report**: Structures findings into signals (`HIGH`, `IMPORTANT`, `EMERGING`) with verified citations.
10. **Completed investigation is stored**: A compact `MemoryRecord` is appended to long-term memory for future continuity.

---

## Verification

The system has been verified through an automated test suite (`scratch/test_stage4_suite.py`):

| Test Scenario | Verification Target | Observed Result | Status |
|---|---|---|---|
| **TEST 1 — Normal Investigation** | Multi-step `InvestigationContext` preservation across tools and agents | Context recorded 2 tool calls and 16 evidence items | **PASSED** |
| **TEST 2 — Critic Feedback** | Critic feedback and gap persistence into follow-up reasoning | Critique feedback entry and gap list stored in context | **PASSED** |
| **TEST 3 — Related Memory Retrieval** | Completed run saved; follow-up related query retrieves prior context | Related query retrieved 1 prior memory with `PRIOR_CONTEXT_FOUND` event | **PASSED** |
| **TEST 4 — Unrelated Memory Rejection** | Unrelated query does not inject irrelevant memory | Retrieved exactly `0` prior memories for unrelated topic | **PASSED** |
| **TEST 5 — Storage Resilience** | Corrupted memory storage file handling | Handled corrupted JSON gracefully with zero crashes | **PASSED** |
| **TEST 6 — Existing Flow & Citations** | Multi-agent collaboration, tool dispatch, and `[En]` citations | 7 prioritized signals produced with verified citations | **PASSED** |

---

## Team

- **ABHALE ATHARV**
- **TUSHAR MATE**
- **YASH SUPEKAR**
- **GAURAV SONAWANE**
- **SHARDUL GAIKWAD**

---

## Project Status

**AGENTX24** is fully operational and includes:
- **Autonomous tool selection** across 4 live intelligence providers.
- **Multi-agent orchestration** with separated powers (*Investigator, Critic, Synthesist*).
- **Context & Memory Management** with short-term structured context and persistent long-term investigation memory.
