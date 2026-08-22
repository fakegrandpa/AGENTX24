# BUILD1.md — AGENTX24 Research & Competitor Tracking Agent — Hour 0 architecture record

Frozen planning record. Labels used throughout: **DECISION** (locked), **ASSUMPTION** (proceeding, cheap to reverse), **REQUIREMENT** (quoted from the problem statement), **OPTIONAL** (only if green and time remains).

> **Hour 0 amendment note (P9 compliance).** This document was amended in place once, still at Hour 0, after the organizer issued additional official requirements: **premium product-grade UI**, **explicit prioritization of signals**, and **adaptive report sections**. The amendment was legitimate rather than a freeze violation because, at the time of editing, verified by inspection: no application code existed, `Stage Outcome` was empty, no stage had executed against this plan, and the file was still uncommitted. **The freeze now applies.** From this point on, changes belong in `BUILD2.md`, `BUILD3.md`, … and only `Stage Outcome` may be appended here. Amended parts are marked `[amended]`.

The organizer asked for 25 content items; AGENTS.md P9 fixes the section headings. The 25 items live inside these headings: Problem Understanding / Official Requirements / MUST-SHOULD-NICE-OUT / MVP Scope → `Problem & Primary Journey` + `Scope`. Stack / Why / Gemini strategy / secrets / folder structure / run procedure → `Stack & Key Decisions` + `How to Run`. Agent architecture / loop / tools / APIs / auth / data flow / UI / telemetry / evidence / errors → `Architecture` + `Data Shapes`. Extension points → `Extension Seams`. Demo flow / acceptance / Stage 0 success → `Core Flow Test` + `Build Order`.

---

## Problem & Primary Journey

**Problem.** Monitoring publications, patents, news and competitor activity by hand is "time-consuming, inefficient, and prone to missing important updates" (REQUIREMENT, quoted). The deliverable is "an autonomous AI agent capable of continuously tracking research and competitor activities, analyzing vast information sources, and delivering concise, actionable insights" (REQUIREMENT).

**Actors.**
- **Judge / analyst (only actor in the MVP)** — types a target, watches the agent work, reads the report.
- **Gemini (the agent brain)** — plans, selects tools, interprets results, synthesizes. REQUIREMENT: "Gemini is the AGENT BRAIN."
- **Python runtime (the controller)** — validates tool calls, executes them, enforces budgets. REQUIREMENT: "Python validates the requested tool/action".

**Primary journey (one sentence).** A judge enters a target (company, competitor, research topic, technology, product or industry), Gemini reasons about what evidence it needs and dynamically selects and executes tools one at a time while the UI streams that activity, and a cited actionable intelligence report appears.

**Deliverable form.** DECISION: one locally-run Python web app — FastAPI process serving a single-page judge UI on `http://127.0.0.1:8000`. Submitted as source code in this repository. Demonstrated live in a browser.

**Hard constraints.**
- Online: every information source and Gemini require network access.
- REQUIREMENT: Python primary language; Gemini via Google AI Studio as the reasoning layer; free/realistically accessible data APIs.
- REQUIREMENT: "The system must demonstrate genuine dynamic agent behavior" and must NOT be "User → LLM → Call every API → Combine results → Answer".
- REQUIREMENT: "Do NOT expose hidden chain-of-thought or private model reasoning."
- REQUIREMENT: "Do not build an uncontrolled infinite agent loop."
- REQUIREMENT: "Create fake research/news/patent results" is forbidden.
- REQUIREMENT `[amended]`: the deliverable is a **local web dashboard** — "BROWSER → LOCALHOST WEB DASHBOARD → PYTHON BACKEND → AUTONOMOUS AI AGENT → INFORMATION TOOLS". "Do NOT introduce cloud infrastructure for the MVP."
- REQUIREMENT `[amended]`: the UI "is not an afterthought"; it "must feel polished, premium, minimal, intuitive, and presentation-ready". This makes visual quality **Stage 0 MUST scope**, not `demo-polisher` scope.
- REQUIREMENT `[amended]`: "The official requirement explicitly requires prioritization. The final report must do more than summarize."
- REQUIREMENT `[amended]`: "Do not render meaningless empty sections" — report structure adapts to the evidence actually collected.
- REQUIREMENT `[amended]`: Git stays local. No remote, no push, no upload. Verified: `git remote -v` is empty and the branch is `main`.
- Environment verified: Python 3.14.5 and pip 26.1.1 present. No `GEMINI_API_KEY` in the environment yet.

---

## Scope: MUST / SHOULD / NICE / NOT YET

### MUST
1. Gemini-driven agent loop with real tool selection — REQUIREMENT: "reasoning pattern such as ReAct or a technically equivalent agentic approach", the model must decide "what action should be taken next", "select an appropriate tool", "observe", and repeat "when necessary".
2. The agent "must NOT automatically call every available API for every request" — tool choice is the model's, not the code's.
3. Two real, working information sources are the Stage 0 floor (MVP priority order item 3): **`research_search` and `news_search`** `[amended]` — the two the organizer names as primary.
4. Loop safety: "Maximum iteration/tool-call limit. Tool timeout handling. API failure handling. Empty-result handling. Invalid tool-call handling. Retry limits. Safe termination. Clear logging/telemetry." Plus "Forced final synthesis when limits are reached."
5. Evidence capture preserving "Source name, Source URL, Publication date, Relevant title, Short evidence summary", plus authors and relevant metadata where the provider returns them `[amended]`.
6. `[amended]` **Prioritized, adaptive** final report — not a summary. Structure: INVESTIGATION SUMMARY, HIGH PRIORITY SIGNALS, KEY RESEARCH DEVELOPMENTS, COMPETITOR / INDUSTRY ACTIVITY, RECENT DEVELOPMENTS, PATENT SIGNALS *(only if genuine patent evidence exists)*, EMERGING / WATCH SIGNALS, WHY THIS MATTERS, RECOMMENDED NEXT ACTIONS, SOURCES. A section with no supporting evidence is **omitted**, not rendered empty. Priority tiers are never fabricated and never padded.
7. Report must "distinguish evidence from the agent's derived analysis" and, when a source fails or is unavailable, "clearly state the limitation" — carried in a dedicated coverage/limitations area rather than as a hollow section `[amended]`.
8. Judge UI supporting all seven listed abilities: enter query, start, watch progress, see tool choices, see action/observation telemetry, see sources, receive the report.
9. Safe telemetry only — objective, tool selected, tool executing, short action/observation summary, sources found, current step, final conclusion. Rendered as "a clean activity timeline", explicitly **not** "a giant terminal-style scrolling log" `[amended]`.
10. Gemini behind "a small model/LLM adapter so the model can be replaced later".
11. Model name not hardcoded blindly — REQUIREMENT: "Do NOT hardcode an outdated Gemini model name without verifying the currently available model/API." Configurable via `GEMINI_MODEL`.
12. Secrets in an ignored env file; runnable from a clean checkout (AGENTS.md §6). `README.md` must end up containing the exact verified run commands.
13. `[amended]` **Premium product-grade UI.** Minimal clutter, clear hierarchy, generous whitespace, excellent typography, strong alignment, consistent spacing, calm surface, purposeful motion, one restrained accent, consistent radius, subtle borders, subtle shadows only where useful, obvious single primary action, excellent readability. Must not read as a generic admin dashboard, template dump, random-card collection, hacker terminal, wall of text, neon/cyberpunk surface, gradient soup, or a screen of equally-weighted buttons.
14. `[amended]` **First-screen clarity.** Within a few seconds the screen answers: what is this, what can I investigate, what do I do next. No settings clutter on first contact.
15. `[amended]` **Four UI states, all designed:** empty (what to do), investigating (visibly alive, never looks frozen), error (human language, never a stack trace), partial (successful evidence preserved with the limitation stated plainly).
16. `[amended]` **Usability floor:** readable font sizes, sufficient contrast, clear button states, visible focus rings, labelled controls, Enter-to-start on the primary input, errors phrased for humans.
17. `[amended]` **Basic responsive behaviour** — correct on the demo laptop, not broken at narrower widths.

### SHOULD
- **`web_search` as the third advertised tool** `[amended]` — not a Stage 0 floor requirement, but a third genuinely different choice makes dynamic selection far more visible. Dropped without regret if its provider proves flaky.
- Patent source behind "a modular adapter so it can be added/replaced without rewriting the agent" — present as an adapter, inactive without verified credentials.
- Inline citation markers tying each analytical claim to a specific collected evidence item.
- Short-lived response cache so a rehearsed demo query is fast and repeatable.
- A headless CLI entry point for the same investigation (verification speed, and the trigger-independence seam).
- Evidence count / elapsed time / tool count surfaced during the investigation so progress feels real `[amended]`.

### NICE
- Elapsed-time and tool-count counters in the UI.
- Copy-report-to-clipboard / plain-text export.
- Two preset demo targets as buttons.

### OUT / NOT YET (explicitly excluded now)
Scheduled monitoring, alerts, email/notification delivery, persistent watchlists, competitor side-by-side comparison, trend charts, multi-agent investigation, PDF/report export, a database, user accounts or auth, Docker/Kubernetes, message queues, vector store or RAG, a custom crawler, an agent framework (LangChain/LlamaIndex/CrewAI), React or any npm build step, WebSockets, and every API listed by the organizer that is not needed for a compelling MVP. REQUIREMENT: "DO NOT implement these now unless required by the current problem. Only create sensible extension points."

---

## Stack & Key Decisions

Format: **decision — reason — rejected alternative and why.**

1. **Python 3.14 + venv** — verified installed (3.14.5); REQUIREMENT names Python. — Rejected Node/TS: contradicts the stated direction.
2. **FastAPI + uvicorn** — one process serves the JSON API, the Server-Sent-Events telemetry stream and the static UI; async fits concurrent HTTP tool calls. — Rejected Streamlit: per-step live telemetry with a stop/reset flow is awkward, and its native-wheel chain (pyarrow) is a real install risk on Python 3.14. Rejected Flask: equivalent effort, no async client story.
3. **Static `web/index.html` + `web/app.css` + `web/app.js`, vanilla JS + SSE, no build step** `[amended]` — three plain files served by FastAPI. The premium-UI requirement raises the CSS from an afterthought to real work, and real work deserves its own file; it still needs no npm, no bundler, no transpiler. — Rejected React/Vite/Tailwind/component libraries: REQUIREMENT says "the visual quality should come from excellent design and implementation, not from installing half the internet". Rejected WebSockets: telemetry is one-directional; SSE is fewer moving parts.
4. **`google-genai` SDK (latest 2.19.0, `requires_python >=3.10`, verified on PyPI)** — official SDK, and the docs state it "automatically handle[s] thought signatures" for Gemini 3 function calling, which raw REST would force us to shuttle by hand. — Rejected raw REST as the primary: more code for the same result; kept as the fallback (see Risks).
5. **Gemini Interactions API with client-side history (`store=False`)** — verified from the current official function-calling docs: `client.interactions.create(model=..., input=history, tools=[...], store=False)`, model output in `interaction.steps` (`step.type == "function_call"`, `step.name`, `step.arguments`, `step.id`) and `interaction.output_text`; results returned as `{"type": "function_result", "name":…, "call_id": step.id, "result": [{"type":"text","text": …}]}`. Client-side history means our loop owns the transcript, so telemetry, replay and offline tests are possible. — Rejected `previous_interaction_id` server-side state: hides the transcript we must render. Rejected the older `generateContent` + `functionDeclarations` surface: kept as second fallback only.
6. **`GEMINI_MODEL` env var, default `gemini-flash-latest`, confirmed at startup via `models.list()`** — the alias is documented as hot-swapped to the latest flash release, and the docs currently show `gemini-3-pro-preview` as "(Shut down)", which proves the hazard the REQUIREMENT warns about. If the configured name is absent from the live list, pick the newest available `*-flash` model that supports content generation and log the substitution. — Rejected hardcoding `gemini-3.7-flash`: exactly what the problem statement forbids.
7. **Hand-written agent loop in `app/agent.py`** — REQUIREMENT: "Prefer a simple controlled Python agent loop over a large agent framework." Budgets and validation are ~80 lines. — Rejected LangChain/LlamaIndex/CrewAI: hides the loop the judges must see, and adds install risk.
8. **Persistence: none. In-memory run registry in `app/store.py`** — no MUST requirement needs durability; a dict is the weakest option that satisfies the MVP and is one file to replace later. — Rejected SQLite/Postgres: unrequested.
9. **`httpx` for all tool HTTP, stdlib `xml.etree.ElementTree` for RSS/Atom** — one client, explicit timeouts; no parser dependency. — Rejected `feedparser`/`beautifulsoup4`: stdlib is sufficient for the fields we keep.
10. **Dependency budget: `fastapi`, `uvicorn`, `httpx`, `google-genai`, `python-dotenv`.** `ddgs` is the only conditional addition, and only if `web_search` ships. Zero frontend dependencies. Any further dependency needs a written reason in that stage's build document.
11. **Config and secrets: `.env` (already gitignored) read by `python-dotenv` in `app/config.py`; `.env.example` committed with placeholder values only.** Verified `.gitignore` already covers `.env`, `.env.*`, `.venv/`, `__pycache__/`, `*.log`, `*.db`, with `!*.example` preserved — no change needed. Secrets are referenced by variable name in logs and telemetry, never by value.
12. **Server binds `127.0.0.1` and has no authentication.** ASSUMPTION: single-user localhost demo, so auth is unrequested scope. This is stated because it matters: the endpoints must not be exposed on a public interface without adding auth first.
13. `[amended]` **Hand-written CSS design system, defined once as custom properties at the top of `web/app.css`** — a fixed token set (background, surface, border, text-strong, text-muted, one accent, radius scale, spacing scale, two shadows, one type scale) is what produces visual consistency; consistency is what reads as premium. — Rejected Tailwind and any CSS framework: a token block is ~25 lines and carries no toolchain. Rejected inventing colours per component: that is exactly how a hackathon UI turns into a random-card collection.
14. `[amended]` **System font stack, no web fonts** (`ui-sans-serif, -apple-system, "Segoe UI", Roboto, Inter, system-ui, sans-serif`) — renders instantly, cannot flash or fail, and has no network dependency during a live demo. — Rejected Google Fonts: a remote request in the critical path of the one screen judges will look at.
15. `[amended]` **The visual system is Stage 0 scope and is built once, at Build Order step 10.** Recorded because the skills constrain what comes later: `demo-polisher` is explicitly forbidden from "introducing a UI framework or theme system" and from "a full redesign… late in the event". So later stages may refine copy, states, spacing and content *within* these tokens, but must not introduce or replace the visual system. If it is not built in Stage 0, it never gets built.
16. `[amended]` **Git is local-only for the whole event.** Verified no remote is configured. No `git remote add`, no push, no upload; checkpoints are local commits (P4).

### Selected APIs — and why, from live probes

`[amended]` — columns added for key requirement, Stage 0 necessity, and fallback status.

| Tool exposed to Gemini | Provider chosen | Probe result | Needs key | Stage 0 | Role | Rejected alternative |
|---|---|---|---|---|---|---|
| `research_search` | **OpenAlex** primary, **arXiv Atom** fallback | both `200` | NO | **YES** | required | **Semantic Scholar** (organizer's suggestion) returned **`429` on two separate unauthenticated attempts** — cannot be the MVP spine. Kept as an optional provider inside the same adapter when `SEMANTIC_SCHOLAR_API_KEY` is set. |
| `news_search` | **Google News RSS** (`/rss/search?q=`) | `200`, 132 KB XML with title, link, pubDate, source | NO | **YES** | required | **NewsData.io** needs signup and a small daily credit pool; REQUIREMENT: "Do not depend on signup-only providers unless credentials are available and verified." Optional provider if `NEWSDATA_API_KEY` is set. **GDELT** returned `429`. |
| `web_search` | **DuckDuckGo** via `ddgs` primary, **Wikipedia search+extract API** fallback | DDG HTML `200`; Wikipedia `200` | NO | NO | SHOULD, third tool | Tavily/Brave/Serper all need keys we do not have. REQUIREMENT: "Do NOT build a web crawler from scratch." |
| `patent_search` | **none available — adapter only, inactive** | **EPO OPS `403`** without OAuth credentials; **PatentsView host did not resolve** | YES (EPO key+secret) | NO | optional, gated | Nothing accessible was found. REQUIREMENT: "Do NOT register a broken patent tool" and "Patent functionality must NOT block the MVP." Registered **only** when `EPO_OPS_KEY` and `EPO_OPS_SECRET` exist and a live probe succeeds, so Gemini is never offered a broken tool. When absent: the PATENT SIGNALS section is **omitted** and the limitation is stated in the report's coverage area `[amended]`. |

DECISION: Stage 0 requires **two** working tools and advertises a **third** if it is healthy. Distinct tools with model-chosen arguments produce visibly divergent investigation paths, which is what the "genuine dynamic agent behavior" requirement is scored on. Registering more sources than that adds surface, not evidence.

### Likely judging priorities (inference, not fact — each tied to text)
- **Dynamic tool selection is the headline.** Inference from "The system must demonstrate genuine dynamic agent behavior" plus an explicit anti-pattern diagram. Highest weight.
- **Autonomy must be legible fast.** Inference from "The UI should make the autonomous behavior obvious within seconds."
- **Evidence integrity.** Inference from "Avoid inventing facts" and "Create fake research/news/patent results" appearing under WHAT NOT TO DO.
- **Product quality is now scored directly** `[amended]`. Not an inference any more: the organizer states the UI "is not an afterthought" and must be "presentation-ready", and supplies an explicit list of visual failure modes. Treated as a MUST.
- **Prioritization is scored directly** `[amended]`. "The final report must do more than summarize" is stated, not implied.
- **The MVP PRIORITY ORDER list reads as the rubric** (working agent → real loop → two real sources → evidence → useful report → telemetry → citations → error handling → clean UI → polish). Treated literally as weights.
- **Never being broken is scored in practice**, because a new requirement lands every 3 hours (AGENTS.md §1).

---

## How to Run

Planned commands (Windows PowerShell, from `D:\AGENTX24`):

```powershell
# setup (once)
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env      # then put the real GEMINI_API_KEY in .env

# verify config without any key
.\.venv\Scripts\python.exe -m app.config          # prints resolved model + enabled tool providers

# verify one tool standalone
.\.venv\Scripts\python.exe -m app.tools.news "NVIDIA"

# verify the whole agent headlessly (first end-to-end slice)
.\.venv\Scripts\python.exe -m app.agent "NVIDIA"

# run the app
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# then: http://127.0.0.1:8000/  and  http://127.0.0.1:8000/api/health
```

`.env` keys: `GEMINI_API_KEY` (required), `GEMINI_MODEL` (optional), `SEMANTIC_SCHOLAR_API_KEY`, `NEWSDATA_API_KEY`, `EPO_OPS_KEY`, `EPO_OPS_SECRET` (all optional).

---

## Architecture

```
D:\AGENTX24\
  app\
    config.py      env + budgets + resolved model; also a __main__ that prints them
    models.py      every data shape (Evidence, TelemetryEvent, Signal, Report, Run)
    llm.py         ONLY file that knows about Gemini: model preflight, propose_next_step(history, tools)
    tools\
      __init__.py  TOOL_REGISTRY: name -> (json schema, callable); builds the advertised list from config
      news.py      news_search      (Google News RSS; NewsData.io if key)
      research.py  research_search   (OpenAlex; arXiv fallback; Semantic Scholar if key)
      web.py       web_search        (ddgs; Wikipedia fallback)          [SHOULD]
      patents.py   patent_search     (EPO OPS; registered only when credentials probe OK)  [OPTIONAL]
    agent.py       the ReAct loop, budgets, tool validation, evidence store; CLI __main__
    report.py      report assembly: citation validation, empty-section suppression, coverage notes
    store.py       in-memory {run_id: Run}
    main.py        FastAPI: routes + SSE + static mount
  web\
    index.html     judge dashboard markup
    app.css        design tokens + all styling
    app.js         SSE client + rendering
  requirements.txt
  .env.example
  README.md
```

**Ownership rule:** `agent.py` never imports `httpx` and never mentions Gemini; `llm.py` never touches tools; tool modules never import the agent; `report.py` never calls the network. That is what keeps the loop swappable and the sources addable.

### The agent loop (ReAct-equivalent)

```
history = [user_input(objective)]
while iterations < MAX_ITERATIONS and tool_calls < MAX_TOOL_CALLS and elapsed < WALL_CLOCK:
    interaction = llm.propose_next_step(history, advertised_tools)   # Gemini decides
    append every returned step to history exactly as received        # required for thought signatures
    emit safe telemetry for each step
    calls = [s for s in interaction.steps if s.type == "function_call"]
    if not calls:
        return finalize(interaction.output_text)                      # Gemini chose to answer
    for call in calls:                                                # parallel calls supported
        result = controller.execute(call)                             # validate -> run -> normalize
        history.append(function_result(call.id, call.name, result))
        emit telemetry + newly collected evidence
return forced_synthesis()   # budget exhausted: one final call with tools=[], "state your limitations"
```

Budgets (DECISION, in `config.py`): `MAX_ITERATIONS = 8`, `MAX_TOOL_CALLS = 12`, `TOOL_TIMEOUT = 15s`, `WALL_CLOCK = 120s`, `TOOL_RETRIES = 1` (transport error or 5xx only), `LLM_RETRIES = 2` with backoff.

`controller.execute` is where every failure mode becomes data rather than a crash — the model always gets a JSON object back and reasons about it:

| Situation | What Gemini receives |
|---|---|
| Unknown tool name | `{"error":"unknown_tool","available":[…]}` |
| Missing/invalid argument | `{"error":"invalid_arguments","expected":{…}}` |
| Timeout / transport failure after retry | `{"error":"tool_unavailable","tool":…,"detail":…}` and a `limitations` entry on the Run |
| Zero results | `{"results":[],"note":"no matching results for <query>"}` |
| Success | `{"results":[{id,title,url,source,date,snippet}, …]}` |

### Evidence, citations and anti-fabrication

Every successful tool result is normalized into `Evidence` records with stable ids `E1, E2, …` and appended to the Run. The system prompt instructs Gemini to cite claims as `[E7]` and to say so plainly when evidence is thin. **The SOURCES section is rendered by our code in `report.py` from the evidence store, not by the model** — so no URL can appear in the report unless a tool actually returned it. `report.py` validates every `[En]` marker against the store: unresolvable markers are stripped from the prose and recorded in `Run.limitations`, never silently rendered. `[amended]`

### Prioritization `[amended]`

REQUIREMENT: "The final report must do more than summarize… identify the most strategically important signals." Split of responsibility:

- **Code supplies the measurable inputs.** For each evidence item `report.py`/tool adapters compute `days_old` from the publication date, `corroboration` (count of other evidence items sharing a resolved URL host or a near-identical title), and `provider_kind` (`research` / `news` / `web` / `patent`). These are facts, so code owns them.
- **Gemini supplies the judgement.** Relevance to the objective, strategic impact and novelty are analytical, so the model assigns each finding a tier — `high` / `important` / `emerging` — and must attach at least one `[En]` citation per finding.
- **Code enforces honesty.** A tier with no findings is omitted. A finding whose citations do not all resolve is dropped. Tiers are never padded to look full, and the model is instructed not to invent a priority level to fill a heading.

This is the difference between the deliverable and an aggregator, so it is verified explicitly (A8).

### Telemetry (safe by construction)

`llm.py` emits only a whitelisted projection of each step; nothing else may reach a `TelemetryEvent`. Any step of a private-reasoning kind (thought/thinking) is counted and rendered as a neutral phase label only — its content is **never** placed in a telemetry event, never sent to the browser, never logged. It stays in `history` for the API and is dropped at the display boundary.

`[amended]` Each event carries both a **human phase label** (what the UI shows prominently) and a **concrete detail line** (what makes it credible):

| Phase label shown | Detail line shown | Emitted when |
|---|---|---|
| Understanding the objective | the objective as the agent restated it | run start |
| Planning the next step | — | model turn in progress |
| Searching recent research | `research_search("solid-state battery degradation")` | `function_call` |
| Checking recent industry developments | `news_search("NVIDIA data centre")` | `function_call` |
| Evidence found | `9 results · 6 new sources` | tool success |
| No results for that angle | `0 results` | empty result |
| Source unavailable | `news_search timed out` | tool failure |
| Comparing and prioritising evidence | `21 evidence items` | final model turn |
| Generating intelligence report | — | synthesis |

The phase vocabulary is a fixed enum in `models.py`, so the UI can style states instead of parsing strings.

### UI and data flow

```
browser  --POST /api/investigate {query}-->  main.py  -->  store.create(Run)  -->  background task: agent.run_investigation(objective, emit)
browser  --GET  /api/stream/{id} (SSE)  <--  emit() pushes TelemetryEvent -> asyncio.Queue -> SSE frames
                                                  |
                                          agent -> llm -> Gemini      (decide)
                                          agent -> tools -> web APIs  (execute, observe)
                                                  |
browser  <-- final "report" SSE event + GET /api/run/{id} for the full record
```

Routes: `POST /api/investigate`, `GET /api/stream/{run_id}` (SSE), `GET /api/run/{run_id}`, `GET /api/health` (reports resolved model and advertised tool names), `GET /` (the UI).

### Product & UI plan `[amended]`

**Hierarchy, fixed:** INPUT → AUTONOMOUS INVESTIGATION → PRIORITIZED INTELLIGENCE. One page, one column of content on a calm neutral background, max content width ~880 px, centred. No sidebar, no nav bar, no tabs, no settings panel — there is only one thing to do here.

**Design tokens** (declared once in `web/app.css`; nothing may introduce a value outside this set):

```
surface        near-white neutral page, one slightly raised card surface
text           one strong near-black, one muted grey — that is all
accent         ONE colour, used for the primary button, the active phase, and focus rings
semantic       one amber for "limitation/partial", one muted red for "error" — never decorative
radius         two values: control and card
spacing        4 / 8 / 12 / 16 / 24 / 32 / 48
type           4 sizes: display, section, body, meta — one weight jump, generous line-height
shadow         two: resting card, raised card. No glow, no gradient, no glass.
motion         120ms ease-out for state, 200ms for entry. Nothing loops except one 1.5s pulse
               on the active phase dot. Honour prefers-reduced-motion.
```

**Screen 1 — arrival (empty state).** Product name, one sentence saying what it does ("Autonomous research and competitor intelligence — enter a target and watch the agent investigate"), then the single large input with a clear label and one primary button. Below it, two or three example targets as quiet text buttons that fill the input, plus a one-line note naming which sources are live this session (read from `/api/health`). Below that, a short "what will happen" line — three phase names, greyed. Nothing else on the screen. Enter submits. Focus starts in the input.

**Screen 2 — investigating.** The input collapses to a compact header showing the target, elapsed time, and a Stop affordance. Two regions:
- **Activity timeline** (primary, left/top): a vertical list of phase entries, each with a small status dot, the phase label, and the muted detail line. Completed phases stay collapsed to one line; the current phase is the only one with the accent dot and a subtle pulse. New entries fade in. **Capped at the most recent ~12 entries** with older ones collapsed behind "earlier steps" — the requirement explicitly forbids a giant scrolling terminal log.
- **Evidence panel** (secondary, right/below): a live count and a compact list of sources as they arrive — title, source name, date — each item entering with a 200 ms fade. This is the panel that makes autonomy feel real, because it fills while the agent works.

Nothing about this screen may look frozen: the elapsed timer always ticks, the active phase always pulses, and a phase label is always present.

**Screen 3 — report.** The timeline collapses to a one-line summary ("7 steps · 3 tools · 21 sources · 48 s") that stays expandable, so the evidence of autonomy is not thrown away. Then, in order and only where evidence supports them: INVESTIGATION SUMMARY (2–3 sentences, largest text), HIGH PRIORITY SIGNALS (each a short headline plus one explanatory line plus its citation chips), KEY RESEARCH DEVELOPMENTS, COMPETITOR / INDUSTRY ACTIVITY, RECENT DEVELOPMENTS, PATENT SIGNALS *(only with real patent evidence)*, EMERGING / WATCH SIGNALS, WHY THIS MATTERS, RECOMMENDED NEXT ACTIONS, SOURCES. Priority tier is conveyed by a single small label and position, **not** by three competing colours. Citation chips `[E7]` are clickable and scroll to the matching source. SOURCES is a plain numbered list with real links, visually distinct from the analysis above it — that distinction is the visible form of "evidence vs interpretation".

**Coverage & limitations block.** A quiet bordered note directly above SOURCES, shown only when non-empty: which sources were unavailable, which yielded nothing, and whether budgets were hit. Amber, one line each, no icons. This is where "patent data not configured" lives.

**Error state.** A run that cannot start at all (no API key, model unreachable) replaces the timeline with a single calm card: what happened in one human sentence, what to do about it, and a Retry button. Never a traceback, never a raw provider error string — those go to the server log only.

**Partial state.** If some tools failed but evidence exists, the report renders normally and the coverage block states the gap. A partial result is never presented as complete, and never discarded.

**Responsive.** Desktop-first, single-column flow that reflows rather than breaks: the two investigation regions sit side by side above ~900 px and stack below it. One breakpoint, no more. Text never smaller than 14 px.

**Accessibility floor.** Semantic landmarks and heading order, a real `<label>` on the input, `aria-live="polite"` on the timeline so phase changes are announced once, visible accent focus rings on every interactive element, contrast checked against the neutral background, full keyboard path (Tab to input → Enter to start → Tab to results).

**Explicitly out of the UI:** dark-mode toggle, icon library, web fonts, charts, animated backgrounds, glassmorphism, gradients, multiple accents, skeleton shimmer beyond a plain pulse, and any second screen or route.

---

## Data Shapes

All in `app/models.py` — one file, so adding a field is one edit. `[amended]`: `authors`/`meta`/`days_old`/`corroboration` added to `Evidence`, `phase` added to `TelemetryEvent`, and `Report` restructured around prioritized signals.

```python
Evidence      = {id: "E3", tool: str, provider: str, provider_kind: "research"|"news"|"web"|"patent",
                 source: str, title: str, url: str, published: str | None,   # ISO date
                 days_old: int | None, authors: [str], snippet: str,
                 corroboration: int, meta: dict}      # meta: venue, citation count, doi, …
TelemetryEvent= {seq: int, ts: iso8601, phase: PhaseEnum, kind: "objective" | "planning"
                 | "tool_selected" | "tool_result" | "note" | "error" | "final",
                 text: str, detail: str | None, data: dict | None}
Signal        = {tier: "high" | "important" | "emerging", headline: str,
                 detail: str, citations: ["E3", "E9"]}
Report        = {target: str, summary: str, signals: [Signal],
                 sections: {research, competitor_industry, recent_developments,
                            patents, why_it_matters: str | None},   # None => omitted, not empty
                 next_actions: [str], coverage: [str], limitations: [str]}
Run           = {id: str, query: str, status: "running" | "done" | "error",
                 started_at, finished_at, telemetry: [TelemetryEvent],
                 evidence: [Evidence], tool_calls: [{name, args, ok, ms}],
                 report: Report | None, limitations: [str]}
```

`Run` is the single serialization contract between backend and UI. `tool_calls` exists so the divergent-path acceptance test is checkable from data, not from watching. A `sections` value of `None` and an empty `signals` tier both mean *omit the heading* — the UI never renders an empty section.

---

## Extension Seams

Bought only because each is already free. *Flexibility is bought by small files and clear seams, not by abstractions.*

- **`agent.run_investigation(objective, emit)` is trigger-agnostic.** The CLI, the HTTP route, and any future scheduler or alert job call the same function — nothing about it knows what started it. `[amended]` This is the seam the official "continuous gathering" concept attaches to:

```
        MANUAL DASHBOARD REQUEST  ──┐
                                    ├──►  run_investigation(objective, emit)  ──►  Run
        FUTURE SCHEDULED TRIGGER  ──┘        (Stage 0 builds only the top path)
```

  Stage 0 proves the core investigation works; a later requirement adds a caller, not a rewrite. Covers scheduled monitoring, alerts, notification delivery.
- **`TOOL_REGISTRY` is a dict.** A new source = one module + one dict entry, no core change. Covers more research sources, more patent sources, comparison tools.
- **`models.py` holds every shape.** A new report field or evidence attribute is one edit that flows to API and UI. Covers report generation and trend data.
- **`report.py` owns presentation of findings** `[amended]`. Export, alternative formats, or a digest view attach here without touching the loop.
- **`web/app.js` renders `Run` JSON; `web/app.css` holds the tokens.** A new panel is additive and inherits the visual system automatically, so it cannot look foreign or break existing panels.
- **Domain naming** — `Evidence`, `Investigation`, `Signal`, `Report`, `Run`; never `Item`, `Data`, `Manager`.

Deliberately **not** built: plugin registry, event bus, abstract base classes, strategy interfaces, dependency injection, repository layer, task queue. If a future requirement needs one, that stage will justify it.

---

## Core Flow Test

`[amended]` — the original sentence named a fixed section list including an always-present PATENT SIGNALS. That now contradicts two official requirements ("Do not render meaningless empty sections"; PATENT SIGNALS "only if genuine patent evidence exists") and omitted prioritization. Amended at Hour 0, before any stage ran against it. This version is now the frozen baseline.

**Given a running server with `GEMINI_API_KEY` set, when a judge enters a target such as "NVIDIA" and presses Enter, the dashboard visibly streams the agent's objective and each tool Gemini selects and executes with human-readable phase labels and concrete detail lines, sources accumulate in the evidence panel while it works, and the run ends in a prioritized intelligence report that leads with an investigation summary and HIGH PRIORITY SIGNALS carrying resolvable `[En]` citations, omits any section the evidence does not support, states any coverage gap plainly, and ends in a SOURCES list in which every URL came from a real executed tool result.**

This exact sentence is the baseline regression check for the whole hackathon. Every later stage re-runs it.

**Additional acceptance criteria for Stage 0 (Definition of Done):**
- **A1 — genuinely dynamic:** run `"NVIDIA"` and `"CRISPR base editing off-target safety"`; the recorded `tool_calls` sequences must differ in tool choice or order. Identical fixed sequences fail the mandatory-capability requirement.
- **A2 — budget safety:** with `MAX_ITERATIONS = 1`, the run still terminates and produces a report that states its limitation. No infinite loop.
- **A3 — tool failure tolerated:** point one tool at an unreachable host; the run completes, the model adapts, the successful evidence is preserved, and the coverage block names the failed source.
- **A4 — no fabrication:** every SOURCES URL is present in `Run.evidence`; every `[En]` in the prose resolves; unresolvable markers were stripped and logged.
- **A5 — no leaked reasoning:** no telemetry event or SSE frame contains model thought content.
- **A6 — clean checkout:** fresh clone + setup commands reach a working run; `.env` and `.venv/` are untracked.
- **A7 — patent honesty:** without verified EPO credentials, `patent_search` is not advertised to the model, the PATENT SIGNALS section is absent from the report, and the coverage block says no patent source is configured.
- **A8 — prioritization is real** `[amended]`: at least one HIGH PRIORITY signal exists with ≥1 resolvable citation; no tier is rendered empty; the report is not merely a chronological list of what the tools returned.
- **A9 — premium UI checklist** `[amended]`: every colour, radius, spacing and font size in the rendered page traces to a token in `app.css`; there is exactly one primary button on screen 1; the timeline shows a pulsing active phase and never exceeds ~12 visible entries; no gradient, glow, glass, second accent, or web font is present; the page reflows without breakage at 1440 px, 1024 px and 800 px widths.
- **A10 — states exist** `[amended]`: empty, investigating, partial, and error states each reachable and each observed — error state produced by unsetting `GEMINI_API_KEY`, partial state by A3.
- **A11 — usability floor** `[amended]`: focus is visible on every control, Enter starts the run, the input has a real label, and the whole primary flow is keyboard-only navigable.

**Judge demo flow (90 seconds):** open the dashboard → the one-line value proposition and single input are the only things on screen → type `NVIDIA` → Enter → narrate the phase labels as Gemini picks its first tool → point out that the second tool choice is a consequence of the first observation, not a script → show the evidence panel filling in real time → the report resolves to HIGH PRIORITY SIGNALS first → click a citation chip to jump to the real source → run the research-topic query to show a different tool path.

---

## Build Order

`[amended]` — resequenced so that prioritization and evidence integrity are proven on the CLI **before** any pixel is written. REQUIREMENT: "Do not spend hours polishing an interface connected to a broken agent. First make it real. Then make it beautiful." Each step is independently verifiable; the first end-to-end slice is step 4.

**Hard gate: do not start step 10 until step 7 has passed.** The premium UI is a MUST, but a beautiful shell over a broken agent scores nothing and cannot be fixed in the freeze window.

1. **Skeleton** — `requirements.txt`, `.env.example`, `app/config.py`, `app/models.py`. *Verify:* `python -m app.config` prints the resolved model, budgets, and which tool providers are enabled. No key needed.
2. **Gemini adapter** — `app/llm.py` with `models.list()` preflight and `propose_next_step`. *Verify:* `python -m app.llm` prints the chosen model and one short completion.
3. **First real tool** — `app/tools/news.py` + registry. *Verify:* `python -m app.tools.news "NVIDIA"` prints ≥3 normalized Evidence dicts with title, url, published, days_old.
4. **Agent loop + CLI** — `app/agent.py` with budgets, tool validation, evidence store, and one tool. *Verify:* `python -m app.agent "NVIDIA"` streams phase lines and prints a draft report. **First end-to-end slice — commit here.**
5. **Second real tool** — `app/tools/research.py` (OpenAlex, arXiv fallback). *Verify:* standalone, then confirm the agent chooses it unprompted for a research-flavoured query. **Two real sources: the Stage 0 floor is met.**
6. **`app/report.py`** — citation validation, `days_old`/`corroboration` computation, prioritized `Signal` tiers, empty-section suppression, coverage notes. *Verify:* A4 and A8 from the CLI alone. **The intelligence is now real; no UI exists yet.**
7. **Error hardening** — every row of the `controller.execute` failure table, forced synthesis, safe termination. *Verify:* A2 and A3 from the CLI. **Gate for UI work.**
8. **Third tool, SHOULD** — `app/tools/web.py` (ddgs, Wikipedia fallback). *Verify:* standalone, then in a run. Skip without regret if flaky; two tools already satisfy the floor.
9. **FastAPI layer** — `app/main.py`: health, investigate, SSE stream, run JSON. *Verify:* `Invoke-RestMethod /api/health`, start a run, watch SSE frames arrive in the terminal.
10. **Design tokens + static shell** — `web/app.css` token block, `web/index.html`, arrival/empty state only. *Verify:* open in a browser with no run started; check the token audit and single-primary-button parts of A9, plus contrast and focus rings.
11. **Live investigation view** — `web/app.js`: SSE client, phase timeline with pulsing active dot and ~12-entry cap, evidence panel, elapsed timer. *Verify:* the Core Flow Test through to the investigating state.
12. **Report rendering** — prioritized signals, adaptive sections, citation chips, coverage block, error and partial states. *Verify:* the full Core Flow Test, plus A9, A10, A11.
13. **`README.md` with the exact verified commands + full acceptance sweep** A1–A11, then green checkpoint: `git commit -m "stage-0: ..."`.
14. **OPTIONAL, only after 13 and only if EPO credentials exist and probe successfully** — `app/tools/patents.py`.

Scope cut line, in order of what goes first if the clock runs out: step 8 (third tool), then step 12's citation chips, then step 11's evidence-panel animation. The CLI from step 6 remains a demonstrable fallback deliverable, and any cut is stated in `Stage Outcome` (P6).

---

## Risks & Fallbacks

| # | Risk | Likelihood | Impact | Pre-decided fallback |
|---|---|---|---|---|
| 1 | **No Gemini API key** — verified absent from the environment | Certain until supplied | Blocks everything | The app must still start: `/api/health` reports `model: "unconfigured"` and the UI shows its calm error state with what to do. The `--replay` fixture below is **contingency only, gated**: build it only if no key exists by step 4, or after step 13 is green with time to spare. Never build it speculatively. **Blocking question to the user.** |
| 2 | `google-genai` install or `client.interactions` shape differs on Python 3.14 | Medium | High | Same `llm.py` interface over raw REST: `POST https://generativelanguage.googleapis.com/v1beta/interactions` with header `x-goog-api-key` (shape verified in the official docs). Second fallback: `:generateContent` with `functionDeclarations`. |
| 3 | Model name churn — docs show `gemini-3-pro-preview` as "(Shut down)" | Medium | Medium | `GEMINI_MODEL` env var + `models.list()` preflight + auto-substitute the newest available `*-flash`, logging the substitution. |
| 4 | Semantic Scholar rate limiting — **verified `429` twice** | High | Medium if relied on | Already avoided: OpenAlex primary, arXiv secondary, S2 only with a key. |
| 5 | A free source rate-limits or dies mid-demo (GDELT already `429`) | Medium | High during judging | 5-minute in-process cache keyed by `(tool, normalized query)` so rehearsed queries are instant and repeatable; failures return structured errors so the agent adapts and the report states the limitation. |
| 6 | DuckDuckGo HTML/`ddgs` parsing breaks | Medium | Low | Wikipedia search+extract API (verified `200`) behind the same `web_search` signature. |
| 7 | Agent runs long or loops | Medium | High | Hard caps (8 iterations / 12 tool calls / 120 s) then one forced synthesis call with `tools=[]`; telemetry shows "investigation budget reached". |
| 8 | Gemini free-tier request limits during judging | Medium | High | Flash-class model, one concurrent run, tool cache, and the `--replay` fixture from risk 1. |
| 9 | No network at the venue | Low–Medium | High | Same `--replay` fixture mode; stated honestly as a replay, never presented as live. |
| 10 | Judge asks about the patent capability | High | Low | The adapter exists and is documented; the coverage block states that no patent source is configured, and the report omits the section entirely rather than showing an empty heading. Honest limitation beats a fake section. |
| 11 | A later 3-hour requirement pushes toward a rewrite | Medium | High | The seams above absorb scheduling, sources, fields and views additively. P7: stop and report rather than re-platform. |
| 12 | **The premium UI eats the implementation budget** `[amended]` | High | High | The step 10 gate makes UI work unreachable until the agent is real. If time then runs short, ship tokens + calm layout + the four states and cut motion, citation chips and the evidence-panel animation first — a restrained static-but-consistent interface already satisfies most of the visual requirement; an unfinished animated one satisfies none. |
| 13 | **Gemini pads priority tiers or invents a signal to fill a heading** `[amended]` | Medium | High — it would make us the aggregator the brief forbids, but dishonestly | `report.py` drops any finding whose citations do not all resolve, omits empty tiers instead of filling them, and the system prompt explicitly permits "only one high-priority signal was supported by the evidence". Verified by A8. |
| 14 | **Google News RSS is the only news provider and could change shape or throttle** `[amended]` | Medium | High — news is half the Stage 0 floor | Parsing keeps only five stable RSS fields, so cosmetic markup changes do not break it; `news_search` returns a structured `tool_unavailable` result so the agent adapts to research-only evidence and the coverage block says so; `NEWSDATA_API_KEY` activates the alternate provider in the same adapter if a key becomes available. |

---

## Not To Be Built Yet

Blunt list. Do not start any of these in Stage 0, even if they seem quick:

- Scheduled monitoring, cron, background pollers, alerting, email or webhook delivery.
- Persistent watchlists, saved targets, run history browsing, any database or ORM or migration.
- Competitor side-by-side comparison, trend charts, dashboards, PDF or DOCX export.
- Multi-agent or sub-agent orchestration; any agent framework.
- Vector store, embeddings, RAG, semantic dedupe of evidence.
- Authentication, accounts, roles, API keys for our own endpoints, rate limiting, multi-tenancy.
- Docker, Compose, Kubernetes, reverse proxy, cloud deployment, CI pipelines.
- Message queues, Celery, Redis, background worker processes beyond one asyncio task.
- A custom crawler or scraper beyond the two provider fallbacks named above.
- Every additional API from the organizer's list: NewsData.io, GDELT, PatentsView, EPO OPS, Crossref, Hacker News, Tavily, Brave. Adapters may be *stubbed by config flag only*, never built speculatively.
- A plugin system, event bus, abstract tool base class, or configurable "engine".
- React, npm, TypeScript, Tailwind, a component library, or any frontend build step.
- Streaming token-by-token model output, WebSockets, or optimistic UI.
- `[amended]` **UI scope creep, specifically:** dark-mode toggle, icon library or icon font, web fonts, charts or sparklines, a second page or route, run-history list, saved targets, settings panel, animated background, glassmorphism, gradients, a second accent colour, shimmer skeletons, drag-and-drop, tooltips library, or any CSS framework. The premium requirement is satisfied by restraint and consistency, not by additions.
- `[amended]` Fabricated priority tiers, invented confidence scores, simulated "thinking" animations not tied to a real model turn, or placeholder sections rendered to look complete.
- Unit-test scaffolding for code that does not exist yet; verification in Stage 0 is the numbered commands above plus A1–A11.
- `[amended]` `git remote add`, `git push`, or publishing this repository anywhere.

---

## Stage Outcome
