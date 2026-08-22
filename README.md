# AGENTX24 — Autonomous Research & Competitor Tracking Agent

> Autonomous AI agent that tracks competitor activities, searches academic research and global news, observes real-time evidence, and synthesizes prioritized, cited intelligence briefings.

---

## ⚡ Quick Start

### 1. Environment Setup
```powershell
# Create Python virtual environment and activate
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt

# Configure environment keys (copy template)
Copy-Item .env.example .env
# Edit .env and supply your GEMINI_API_KEY
```

### 2. Verify Diagnostics & Standalone Tools
```powershell
# Verify configuration and active tools
python -m app.config

# Test individual sources standalone
python -m app.tools.news "NVIDIA"
python -m app.tools.research "solid state battery"
python -m app.tools.web "NVIDIA Blackwell"
```

### 3. Launch Web Dashboard
```powershell
# Run the local FastAPI + Uvicorn server
python -m uvicorn app.main:app --reload --port 8000
```
Open your browser at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)** (or inspect health at `http://127.0.0.1:8000/api/health`).

### 4. Run Headless CLI Investigation
```powershell
python -m app.agent "NVIDIA"
```

---

## 🎯 Core Flow Demo (90 Seconds)

1. Open the dashboard at `http://127.0.0.1:8000/`.
2. Notice the clean arrival interface displaying live active tools (`news_search`, `research_search`, `web_search`).
3. Click a suggested target (e.g. `NVIDIA` or `Solid-State Battery Degradation`) or type a custom company/topic, then press **Enter**.
4. Watch the autonomous investigation stream in real time:
   - **Activity Timeline**: Dynamic tool selection with pulsing active phase and concrete query detail lines.
   - **Evidence Feed**: Live accumulation of cited sources, publisher names, and publication dates.
5. Review the final intelligence briefing:
   - **Executive Summary**: Core takeaway synthesis.
   - **Prioritized Signals**: High Priority, Important, and Emerging tiers with interactive `[En]` citation chips.
   - **Adaptive Sections**: Research, competitor developments, and why this matters (omitting empty sections).
   - **Verified Sources**: Numbered references where all URLs originate directly from verified tool results.
   - **Coverage & Limitations**: Honest reporting of query coverage and unconfigured adapters.

---

## 🏛️ Architecture

```
d:\AGENTX24\
  app\
    config.py       -> Environment loading, budgets, active providers
    models.py       -> Canonical data models (Evidence, Signal, Report, Run, TelemetryEvent)
    llm.py          -> Gemini adapter with preflight, tool-calling, and retries
    tools\
      __init__.py   -> Central registry and tool execution dispatcher
      news.py       -> Google News RSS search (with NewsData.io support)
      research.py   -> OpenAlex & arXiv Atom search (with Semantic Scholar support)
      web.py        -> DuckDuckGo (ddgs) & Wikipedia Search API
      patents.py    -> EPO OPS adapter (modular & inactive when unconfigured)
    agent.py        -> Autonomous ReAct loop, budgets, tool validation, and CLI entry point
    report.py       -> Citation validation, corroboration metrics, and anti-fabrication
    store.py        -> In-memory run store and SSE broadcast queues
    main.py         -> FastAPI endpoints (/api/health, /api/investigate, /api/stream, /api/run)
  web\
    index.html      -> Semantic judge dashboard markup
    app.css         -> Token-based CSS design system (4 states, no frameworks)
    app.js          -> SSE client, live timeline, and interactive citation navigation
  requirements.txt  -> Pinned dependency manifest
  .env.example      -> Placeholder configuration template
  BUILD1.md         -> Frozen Hour 0 Architecture & Stage Outcome record
```
