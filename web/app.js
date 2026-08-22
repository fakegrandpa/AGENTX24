/* ==========================================================================
   AGENTX24 — Autonomous Research & Competitor Intelligence Workspace
   Client JavaScript Architecture
   ========================================================================== */

const VISIBLE_NODE_CAP = 20;
const SIGNIFICANCE_LABEL = { high: "HIGH PRIORITY", important: "IMPORTANT", emerging: "EMERGING / WATCH" };
const SIGNIFICANCE_CLASS = { high: "high", important: "important", emerging: "emerging" };

const state = {
  runId: null,
  source: null,
  clock: null,
  startedAt: 0,
  events: [],
  evidenceList: [],
  seenEvidence: new Set(),
  toolCalls: 0,
  showEarlier: false,
  activeFilter: "all",
  activeFocus: null,
};

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  loadHealth();
  wireForm();
  wireExamples();
  wireNavigation();
  wireEvidenceFilters();
});

/* ------------------------------------------------------------------ Health Check */

async function loadHealth() {
  const dot = $("status-dot");
  const model = $("status-model");
  const sources = $("status-sources");
  const arrivalTools = $("arrival-tools");

  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const tools = data.advertised_tools || [];
    dot.className = `status-dot ${data.gemini_ready ? "ok" : "warn"}`;
    model.textContent = data.gemini_ready ? data.gemini_model : "model unconfigured";
    sources.textContent = `${tools.length} tools online`;
    sources.title = tools.join(", ");

    if (tools.length && arrivalTools) {
      arrivalTools.innerHTML = tools.map((t) => {
        let label = t;
        if (t === "news_search") label = "news_search (Google News)";
        else if (t === "research_search") label = "research_search (OpenAlex · arXiv)";
        else if (t === "web_search") label = "web_search (DuckDuckGo · Wikipedia)";
        else if (t === "patent_search") label = "patent_search (Google Patents)";
        return `<span class="tool-pill mono">${label}</span>`;
      }).join("");
    }

    const arrivalAgents = $("arrival-agents");
    if (data.agents && arrivalAgents) {
      arrivalAgents.innerHTML = data.agents.map((a) => {
        return `<span class="tool-pill mono agent-pill" title="${a.responsibility}">${a.id} (${a.name})</span>`;
      }).join("");
    }

    if (!data.gemini_ready) {
      showFieldError(data.gemini_status_message || "The reasoning model is not configured.");
    }
  } catch (err) {
    dot.className = "status-dot down";
    model.textContent = "backend unreachable";
    sources.textContent = "";
  }
}

/* ------------------------------------------------------------------ Navigation */

function showScreen(id) {
  ["screen-arrival", "screen-run", "screen-report", "screen-error"].forEach((s) => {
    const el = $(s);
    if (el) el.hidden = s !== id;
  });
  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

function wireNavigation() {
  const reset = () => {
    stopStream();
    $("target-input").value = "";
    clearFieldError();
    showScreen("screen-arrival");
    $("target-input").focus();
  };

  $("btn-new-run").addEventListener("click", reset);
  $("btn-restart").addEventListener("click", reset);
  $("btn-retry").addEventListener("click", reset);

  const traceToggle = $("trace-toggle");
  if (traceToggle) {
    traceToggle.addEventListener("click", () => {
      const runScreen = $("screen-run");
      const isHidden = runScreen.hidden;
      runScreen.hidden = !isHidden;
      traceToggle.setAttribute("aria-expanded", String(isHidden));
      traceToggle.querySelector("span").textContent = isHidden ? "Hide Decision Trace" : "Inspect Decision Trace";
      if (isHidden) runScreen.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }
}

/* ------------------------------------------------------------------ Input Form & Starters */

function wireExamples() {
  $("examples").querySelectorAll(".fragment-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const input = $("target-input");
      input.value = chip.dataset.q;
      clearFieldError();
      input.focus();
      // Auto-trigger on chip click for immediate discovery
      startInvestigation(chip.dataset.q);
    });
  });
}

function showFieldError(message) {
  const errEl = $("input-error");
  const shellEl = $("input-shell");
  if (errEl) errEl.textContent = message;
  if (shellEl) shellEl.classList.add("invalid");
}

function clearFieldError() {
  const errEl = $("input-error");
  const shellEl = $("input-shell");
  if (errEl) errEl.textContent = "";
  if (shellEl) shellEl.classList.remove("invalid");
}

function wireForm() {
  const form = $("investigate-form");
  const input = $("target-input");

  input.addEventListener("input", clearFieldError);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (query.length < 3) {
      showFieldError("Please enter at least 3 characters describing what you want to investigate.");
      input.focus();
      return;
    }
    clearFieldError();
    startInvestigation(query);
  });
}

/* ------------------------------------------------------------------ Live Run Lifecycle */

async function startInvestigation(query) {
  state.events = [];
  state.evidenceList = [];
  state.seenEvidence = new Set();
  state.toolCalls = 0;
  state.showEarlier = false;
  state.activeFilter = "all";
  state.startedAt = Date.now();

  $("run-target-heading").textContent = query;
  $("run-id-label").textContent = "initializing…";
  $("timeline").innerHTML = "";
  $("evidence-list").innerHTML = "";
  $("evidence-count").textContent = "0 items";
  $("evidence-placeholder").hidden = false;
  $("timeline-count").textContent = "0 steps";
  $("metric-calls").textContent = "0";
  $("metric-sources").textContent = "0";
  $("earlier-toggle").hidden = true;

  updateFocusBanner({
    phase: "INVESTIGATION STARTED",
    title: `Target: ${query}`,
    query: null,
    reason: null,
  });

  showScreen("screen-run");
  startClock();

  try {
    const res = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to start investigation." }));
      throw new Error(err.detail || "Server error.");
    }

    const data = await res.json();
    state.runId = data.run_id;
    $("run-id-label").textContent = data.run_id;
    startStream(data.run_id);
  } catch (err) {
    stopClock();
    showError(err.message, "Verify the backend server is running on port 8000.");
  }
}

function startClock() {
  tickClock();
  clearInterval(state.clock);
  state.clock = setInterval(tickClock, 1000);
}

function tickClock() {
  const s = Math.floor((Date.now() - state.startedAt) / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  const clockEl = $("metric-clock");
  if (clockEl) clockEl.textContent = `${mm}:${ss}`;
}

function stopClock() {
  clearInterval(state.clock);
}

function stopStream() {
  if (state.source) {
    state.source.close();
    state.source = null;
  }
  stopClock();
}

function startStream(runId) {
  stopStream();
  state.source = new EventSource(`/api/stream/${runId}`);

  state.source.onmessage = async (msg) => {
    if (msg.data.includes('"stream_end"')) {
      stopStream();
      await finalizeRun(runId);
      return;
    }

    try {
      const ev = JSON.parse(msg.data);
      state.events.push(ev);
      processTelemetryEvent(ev);
      renderTimeline();

      if (ev.kind === "tool_result" || ev.kind === "note") {
        refreshEvidence(runId);
      }
    } catch (err) {
      console.error("Failed to parse telemetry event", err);
    }
  };

  state.source.onerror = async () => {
    stopStream();
    try {
      const res = await fetch(`/api/run/${runId}`);
      if (!res.ok) throw new Error("Run state unavailable");
      const run = await res.json();
      if (run.status === "done") {
        renderReport(run);
      } else if (run.status === "error") {
        showError(run.limitations[0] || "Investigation failed.", "See server logs for details.");
      }
    } catch (err) {
      showError("Connection to intelligence stream lost.", "The backend may have stopped.");
    }
  };
}

async function finalizeRun(runId) {
  try {
    const res = await fetch(`/api/run/${runId}`);
    if (!res.ok) throw new Error("Could not load completed run.");
    const run = await res.json();
    if (run.status === "error") {
      showError(run.limitations[0] || "The investigation encountered an error.", "No verifiable evidence produced.");
      return;
    }
    renderReport(run);
  } catch (err) {
    showError(err.message, "Reload and try again.");
  }
}

/* ------------------------------------------------------------------ Agent Focus Banner */

function processTelemetryEvent(ev) {
  const d = ev.data || {};
  let phaseTag = "REASONING";
  let title = ev.text || ev.phase;
  let query = d.query || null;
  let reason = d.reason || ev.detail || null;

  if (ev.kind === "tool_selected") {
    phaseTag = "TOOL EXECUTION";
    title = `Dispatching ${d.tool || "tool"}`;
  } else if (ev.kind === "tool_result") {
    phaseTag = "ANALYZING EVIDENCE";
    title = `Processed findings from ${d.tool || "tool"}`;
  } else if (ev.phase === "Relevant prior context retrieved") {
    phaseTag = "MEMORY RETRIEVAL";
    title = `Referenced ${d.count || 1} relevant historical investigation(s)`;
  } else if (ev.phase === "Investigation context updated") {
    phaseTag = "CONTEXT UPDATED";
    title = "Updated short-term context with Critic feedback";
  } else if (ev.phase === "Investigation saved to memory") {
    phaseTag = "MEMORY PERSISTED";
    title = "Saved completed investigation to memory store";
  } else if (ev.phase === "Reviewing evidence sufficiency") {
    phaseTag = "CRITIC REVIEW";
    title = "Evidence Critic reviewing knowledge sufficiency";
  } else if (ev.phase === "Critique returned") {
    phaseTag = d.sufficient ? "EVIDENCE SUFFICIENT" : "GAPS IDENTIFIED";
    title = d.sufficient ? "Evidence verified sufficient" : "Critic identified critical gaps";
  } else if (ev.phase === "Identifying knowledge gaps") {
    phaseTag = "GAP DETECTED";
    title = "Formulating next inquiry angle";
  } else if (ev.phase === "Composing intelligence report" || ev.phase === "Generating intelligence report") {
    phaseTag = "SYNTHESIS";
    title = "Report Synthesist composing prioritized intelligence brief";
  }

  updateFocusBanner({
    phase: phaseTag,
    title: title,
    query: query,
    reason: reason,
  });
}

function updateFocusBanner({ phase, title, query, reason }) {
  $("focus-phase-tag").textContent = phase;
  $("focus-activity-title").textContent = title;

  const now = new Date();
  $("focus-timestamp").textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

  const queryRow = $("focus-detail-row");
  const queryEl = $("focus-query");
  if (query) {
    queryEl.textContent = query;
    queryRow.hidden = false;
  } else {
    queryRow.hidden = true;
  }

  const reasonEl = $("focus-reason");
  if (reason) {
    reasonEl.textContent = reason;
    reasonEl.hidden = false;
  } else {
    reasonEl.hidden = true;
  }
}

/* ------------------------------------------------------------------ Timeline Renderer */

function getNodeClasses(ev, isLast) {
  const classes = ["timeline-node"];
  if (isLast) classes.push("is-active");
  if (ev.kind === "tool_selected") classes.push("is-tool");
  else if (ev.kind === "tool_result") classes.push("is-result");
  else if (ev.phase === "Reviewing evidence sufficiency" || ev.phase === "Critique returned") classes.push("is-critic");
  else if (ev.phase === "Composing intelligence report") classes.push("is-synthesist");
  else if (ev.phase === "Identifying knowledge gaps") classes.push("is-gap");
  else if (ev.kind === "error") classes.push("is-error");
  return classes.join(" ");
}

function buildTimelineNode(ev, isLast) {
  const li = document.createElement("li");
  li.className = getNodeClasses(ev, isLast);

  const seq = document.createElement("div");
  seq.className = "node-seq mono";
  seq.textContent = String(ev.seq).padStart(2, "0");

  const rail = document.createElement("div");
  rail.className = "node-rail";
  const dot = document.createElement("span");
  dot.className = "node-dot";
  rail.appendChild(dot);

  const content = document.createElement("div");
  content.className = "node-content";

  const titleRow = document.createElement("div");
  titleRow.className = "node-title-row";

  // Agent Role Badge
  const agentRole = (ev.agent || "investigator").toLowerCase();
  const agentBadge = document.createElement("span");
  agentBadge.className = `node-agent-badge mono agent-${agentRole}`;
  agentBadge.textContent = agentRole;
  titleRow.appendChild(agentBadge);

  const title = document.createElement("span");
  title.className = "node-title";

  const d = ev.data || {};
  if (ev.kind === "tool_selected") {
    title.textContent = "Selected ";
    const toolTag = document.createElement("span");
    toolTag.className = "node-tool-tag mono";
    toolTag.textContent = d.tool || "tool";
    title.appendChild(toolTag);
  } else if (ev.kind === "tool_result") {
    title.textContent = `Evidence received (${d.new_evidence ?? "?"} items)`;
  } else if (ev.kind === "objective") {
    title.textContent = "Investigation initiated";
  } else if (ev.phase === "Critique returned") {
    title.textContent = d.sufficient ? "Evidence Sufficiency Confirmed" : "Evidence Sufficiency Check: Gaps Found";
  } else {
    title.textContent = ev.phase;
  }

  titleRow.appendChild(title);
  content.appendChild(titleRow);

  // Machine facts & reasoning directly from telemetry
  if (ev.kind === "tool_selected") {
    const kv = document.createElement("div");
    kv.className = "node-meta-kv";

    if (d.query) {
      const qLbl = document.createElement("span");
      qLbl.className = "node-kv-label";
      qLbl.textContent = "QUERY";
      const qVal = document.createElement("span");
      qVal.className = "node-kv-query mono";
      qVal.textContent = d.query;
      kv.append(qLbl, qVal);
    }

    if (d.reason) {
      const rLbl = document.createElement("span");
      rLbl.className = "node-kv-label";
      rLbl.textContent = "WHY";
      const rVal = document.createElement("span");
      rVal.className = "node-kv-reason";
      rVal.textContent = d.reason;
      kv.append(rLbl, rVal);
    }

    content.appendChild(kv);
  } else if (ev.phase === "Critique returned") {
    const kv = document.createElement("div");
    kv.className = "node-meta-kv";

    const vLbl = document.createElement("span");
    vLbl.className = "node-kv-label";
    vLbl.textContent = "VERDICT";
    const vVal = document.createElement("span");
    vVal.className = "node-kv-reason";
    vVal.textContent = d.sufficient ? "Sufficient (Accepted)" : "Insufficient (Follow-up Required)";
    kv.append(vLbl, vVal);

    if (d.gaps && Array.isArray(d.gaps) && d.gaps.length > 0) {
      const gLbl = document.createElement("span");
      gLbl.className = "node-kv-label";
      gLbl.textContent = "GAPS";
      const gVal = document.createElement("span");
      gVal.className = "node-kv-reason";
      gVal.textContent = d.gaps.join("; ");
      kv.append(gLbl, gVal);
    }

    content.appendChild(kv);
  } else if (ev.phase === "Identifying knowledge gaps" && d.reason) {
    const kv = document.createElement("div");
    kv.className = "node-meta-kv";
    const gLbl = document.createElement("span");
    gLbl.className = "node-kv-label";
    gLbl.textContent = "GAP";
    const gVal = document.createElement("span");
    gVal.className = "node-kv-reason";
    gVal.textContent = d.reason;
    kv.append(gLbl, gVal);
    content.appendChild(kv);
  } else if (ev.detail) {
    const note = document.createElement("div");
    note.className = "node-detail-note";
    note.textContent = ev.detail;
    content.appendChild(note);
  }

  li.append(seq, rail, content);
  return li;
}

function renderTimeline() {
  const list = $("timeline");
  const toggle = $("earlier-toggle");
  const events = state.events;

  $("timeline-count").textContent = `${events.length} step${events.length === 1 ? "" : "s"}`;

  const hiddenCount = Math.max(0, events.length - VISIBLE_NODE_CAP);
  const shown = state.showEarlier || hiddenCount === 0 ? events : events.slice(hiddenCount);

  if (hiddenCount > 0) {
    toggle.hidden = false;
    toggle.textContent = state.showEarlier
      ? `Hide earlier steps (${hiddenCount})`
      : `Show earlier steps (${hiddenCount})`;
    toggle.onclick = () => {
      state.showEarlier = !state.showEarlier;
      renderTimeline();
    };
  } else {
    toggle.hidden = true;
  }

  list.innerHTML = "";
  shown.forEach((ev, i) => list.appendChild(buildTimelineNode(ev, i === shown.length - 1)));

  state.toolCalls = events.filter((e) => e.kind === "tool_selected").length;
  $("metric-calls").textContent = String(state.toolCalls);
}

/* ------------------------------------------------------------------ Evidence Fragments Board */

function wireEvidenceFilters() {
  const bar = $("evidence-filter-bar");
  if (!bar) return;

  bar.querySelectorAll(".ev-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      bar.querySelectorAll(".ev-filter").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeFilter = btn.dataset.filter;
      renderFilteredEvidence();
    });
  });
}

async function refreshEvidence(runId) {
  try {
    const res = await fetch(`/api/run/${runId}`);
    if (!res.ok) return;
    const run = await res.json();
    state.evidenceList = run.evidence || [];

    const total = state.evidenceList.length;
    $("evidence-count").textContent = `${total} item${total === 1 ? "" : "s"}`;
    $("metric-sources").textContent = String(total);
    $("evidence-placeholder").hidden = total > 0;

    renderFilteredEvidence();
  } catch (err) {
    // transient
  }
}

function renderFilteredEvidence() {
  const list = $("evidence-list");
  if (!list) return;
  list.innerHTML = "";

  const filter = state.activeFilter;
  const filtered = state.evidenceList.filter((ev) => {
    if (filter === "all") return true;
    const kind = (ev.provider_kind || ev.tool || "").toLowerCase();
    return kind.includes(filter);
  });

  filtered.slice().reverse().forEach((ev) => {
    list.appendChild(createEvidenceFragmentElement(ev));
  });
}

function createEvidenceFragmentElement(ev) {
  const card = document.createElement("li");
  card.className = "evidence-fragment";
  card.id = `live-ev-${ev.id}`;

  const header = document.createElement("div");
  header.className = "ev-header";

  const badge = document.createElement("span");
  badge.className = "ev-badge mono";
  badge.textContent = ev.id;

  const src = document.createElement("span");
  src.className = "ev-source";
  src.textContent = ev.published ? `${ev.source} · ${ev.published}` : ev.source;

  const tool = document.createElement("span");
  tool.className = "ev-tool-tag mono";
  tool.textContent = ev.tool;

  header.append(badge, src, tool);

  const titleDiv = document.createElement("div");
  titleDiv.className = "ev-title-text";

  if (ev.url) {
    const link = document.createElement("a");
    link.href = ev.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "ev-title-link";
    link.textContent = ev.title;
    titleDiv.appendChild(link);
  } else {
    titleDiv.textContent = ev.title;
  }

  card.append(header, titleDiv);

  // Expandable Snippet
  if (ev.snippet || (ev.authors && ev.authors.length)) {
    const expandBtn = document.createElement("button");
    expandBtn.type = "button";
    expandBtn.className = "ev-expand-btn";
    expandBtn.innerHTML = `<span>Inspect Snippet</span>`;

    const snippetBody = document.createElement("div");
    snippetBody.className = "ev-snippet-body";
    snippetBody.hidden = true;

    let metaInfo = "";
    if (ev.authors && ev.authors.length) {
      metaInfo += `<strong>Authors:</strong> ${ev.authors.slice(0, 4).join(", ")}<br>`;
    }
    if (ev.snippet) {
      metaInfo += `<p>${ev.snippet}</p>`;
    }
    snippetBody.innerHTML = metaInfo;

    expandBtn.addEventListener("click", () => {
      const isExpanded = !snippetBody.hidden;
      snippetBody.hidden = isExpanded;
      card.classList.toggle("expanded", !isExpanded);
      expandBtn.querySelector("span").textContent = isExpanded ? "Inspect Snippet" : "Close Snippet";
    });

    card.append(expandBtn, snippetBody);
  }

  return card;
}

/* ------------------------------------------------------------------ Report Renderer */

function renderReport(run) {
  const report = run.report;
  if (!report) {
    showError("No report produced for this investigation.", "Please enter a specific target.");
    return;
  }

  showScreen("screen-report");
  $("screen-run").hidden = true;
  $("report-target-heading").textContent = run.query;

  const elapsed = Math.max(1, Math.round((Date.now() - state.startedAt) / 1000));
  const toolsUsed = [...new Set((run.tool_calls || []).map((t) => t.name))];
  const evidenceCount = (run.evidence || []).length;
  const priorMemCount = (run.prior_memories || []).length;

  $("trace-summary-steps").textContent = `${state.events.length} steps`;
  $("trace-summary-evidence").textContent = `${evidenceCount} verified fragments`;
  $("trace-summary-tools").textContent = `${toolsUsed.length} external tools`;
  $("trace-summary-time").textContent = `${elapsed}s wall-clock`;
  const memEl = $("trace-summary-memory");
  if (memEl) {
    memEl.textContent = priorMemCount > 0 ? `${priorMemCount} prior linked` : "None";
  }

  const validIds = new Set((run.evidence || []).map((e) => e.id));

  // Executive Summary
  $("report-summary").innerHTML = formatTextWithCitations(report.summary, validIds);

  // Key Prioritized Signals
  const signalsHost = $("report-signals");
  signalsHost.innerHTML = "";
  const signals = report.signals || [];
  if (signals.length) {
    signals.forEach((sig) => signalsHost.appendChild(createSignalElement(sig, validIds)));
  } else {
    signalsHost.innerHTML = `<p class="prose">Autonomous reasoning assembled verified sources without distinct strategic signal tiers.</p>`;
  }

  // Dynamic Deep-Dive Sections
  const dynamicHost = $("report-dynamic-sections");
  dynamicHost.innerHTML = "";
  const sectionDefs = [
    ["competitor_industry", "03 / COMPETITIVE & INDUSTRY ACTIVITY"],
    ["research", "04 / KEY RESEARCH & SCIENTIFIC DEVELOPMENTS"],
    ["patents", "05 / PATENT & IP LANDSCAPE"],
    ["recent_developments", "06 / RECENT TIMELINE & STRATEGIC SHIFTS"],
    ["why_it_matters", "07 / STRATEGIC IMPLICATIONS & WHY THIS MATTERS"],
  ];

  const sections = report.sections || {};
  sectionDefs.forEach(([key, title]) => {
    const val = sections[key];
    if (!val || !String(val).trim()) return;

    const secEl = document.createElement("section");
    secEl.className = "report-section";

    const badgeRow = document.createElement("div");
    badgeRow.className = "section-badge-row";
    const tag = document.createElement("span");
    tag.className = "section-tag";
    tag.textContent = title;
    badgeRow.appendChild(tag);

    const prose = document.createElement("div");
    prose.className = "prose";
    prose.innerHTML = formatTextWithCitations(val, validIds);

    secEl.append(badgeRow, prose);
    dynamicHost.appendChild(secEl);
  });

  // Recommended Next Actions
  const actions = report.next_actions || [];
  const actionsSec = $("sec-actions");
  actionsSec.hidden = actions.length === 0;
  const actionsHost = $("report-actions");
  actionsHost.innerHTML = "";
  actions.forEach((act, idx) => {
    const li = document.createElement("li");
    li.className = "action-item";
    li.innerHTML = `<span class="action-num mono">${idx + 1}</span><span>${formatTextWithCitations(act, validIds)}</span>`;
    actionsHost.appendChild(li);
  });

  // Limitations & Gaps
  const limits = report.limitations || [];
  const limitsSec = $("sec-limitations");
  limitsSec.hidden = limits.length === 0;
  const limitsHost = $("report-limitations");
  limitsHost.innerHTML = "";
  limits.forEach((lim) => {
    const li = document.createElement("li");
    li.className = "limitation-item";
    li.textContent = lim;
    limitsHost.appendChild(li);
  });

  renderCoverageProvenance(run, toolsUsed);
  renderSourcesIndex(run);
  wireCitationInteractions();
}

function createSignalElement(sig, validIds) {
  const card = document.createElement("div");
  const tierCls = SIGNIFICANCE_CLASS[sig.tier] || "important";
  card.className = `signal-card tier-${tierCls}`;

  const header = document.createElement("div");
  header.className = "signal-header";

  const badge = document.createElement("span");
  badge.className = `signal-tier-badge ${tierCls} mono`;
  badge.textContent = SIGNIFICANCE_LABEL[sig.tier] || sig.tier;

  const headline = document.createElement("h3");
  headline.className = "signal-headline-text";
  headline.textContent = sig.headline;

  header.append(badge, headline);

  const body = document.createElement("div");
  body.className = "signal-body-text";
  body.innerHTML = formatTextWithCitations(sig.detail, validIds);

  card.append(header, body);
  return card;
}

function renderCoverageProvenance(run, toolsUsed) {
  const evidence = run.evidence || [];
  const total = evidence.length;

  // Breakdown by kind
  const counts = { news: 0, research: 0, patent: 0, web: 0 };
  evidence.forEach((ev) => {
    const k = (ev.provider_kind || ev.tool || "").toLowerCase();
    if (k.includes("news")) counts.news++;
    else if (k.includes("research")) counts.research++;
    else if (k.includes("patent")) counts.patent++;
    else counts.web++;
  });

  // Visual Distribution Bar
  const bar = $("coverage-distribution-bar");
  const legend = $("coverage-legend");
  bar.innerHTML = "";
  legend.innerHTML = "";

  if (total > 0) {
    const kinds = [
      { key: "news", label: "News", count: counts.news, cls: "seg-news" },
      { key: "research", label: "Research", count: counts.research, cls: "seg-research" },
      { key: "patent", label: "Patents", count: counts.patent, cls: "seg-patent" },
      { key: "web", label: "Web", count: counts.web, cls: "seg-web" },
    ];

    kinds.forEach((k) => {
      if (k.count > 0) {
        const pct = ((k.count / total) * 100).toFixed(1);
        const seg = document.createElement("div");
        seg.className = `coverage-segment ${k.cls}`;
        seg.style.width = `${pct}%`;
        seg.title = `${k.label}: ${k.count} (${pct}%)`;
        bar.appendChild(seg);

        const legItem = document.createElement("div");
        legItem.className = "legend-item";
        legItem.innerHTML = `<span class="legend-dot ${k.cls}"></span><span>${k.label}: <strong>${k.count}</strong></span>`;
        legend.appendChild(legItem);
      }
    });
  }

  // Summary Stat Boxes
  const statsHost = $("coverage-stats");
  statsHost.innerHTML = "";
  const statsData = [
    [total, "EVIDENCE ITEMS"],
    [toolsUsed.length, "EXTERNAL TOOLS"],
    [(run.tool_calls || []).length, "TOOL CALLS"],
  ];

  statsData.forEach(([val, lbl]) => {
    const box = document.createElement("div");
    box.className = "stat-box";
    box.innerHTML = `<div class="stat-val mono">${val}</div><div class="stat-tag">${lbl}</div>`;
    statsHost.appendChild(box);
  });

  // Per-Tool Breakdown Rows
  const provList = $("coverage-list");
  provList.innerHTML = "";
  toolsUsed.forEach((tool) => {
    const calls = (run.tool_calls || []).filter((t) => t.name === tool);
    const count = evidence.filter((e) => e.tool === tool).length;

    const row = document.createElement("li");
    row.className = "coverage-prov-row";
    row.innerHTML = `
      <span class="prov-name mono">${tool}</span>
      <span class="mono">${calls.length} call${calls.length === 1 ? "" : "s"} · ${count} fragment${count === 1 ? "" : "s"}</span>
    `;
    provList.appendChild(row);
  });
}

function renderSourcesIndex(run) {
  const host = $("report-sources");
  host.innerHTML = "";
  const evidence = run.evidence || [];

  if (!evidence.length) {
    host.innerHTML = `<li class="source-index-row"><span class="source-main-title">No verifiable sources returned.</span></li>`;
    return;
  }

  evidence.forEach((ev) => {
    const li = document.createElement("li");
    li.className = "source-index-row";
    li.id = `source-${ev.id}`;

    const idSpan = document.createElement("span");
    idSpan.className = "source-anchor-id mono";
    idSpan.textContent = `[${ev.id}]`;

    const infoCol = document.createElement("div");
    infoCol.className = "source-info-col";

    const titleDiv = document.createElement("div");
    titleDiv.className = "source-main-title";

    if (ev.url) {
      const link = document.createElement("a");
      link.href = ev.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = ev.title;
      titleDiv.appendChild(link);
    } else {
      titleDiv.textContent = ev.title;
    }

    const metaDiv = document.createElement("div");
    metaDiv.className = "source-provenance-meta mono";
    const parts = [ev.source];
    if (ev.published) parts.push(ev.published);
    if (ev.authors && ev.authors.length) parts.push(ev.authors.slice(0, 3).join(", "));
    parts.push(ev.tool);
    metaDiv.textContent = parts.join(" · ");

    infoCol.append(titleDiv, metaDiv);

    if (ev.snippet) {
      const snippetP = document.createElement("p");
      snippetP.className = "source-snippet-text";
      snippetP.textContent = ev.snippet;
      infoCol.appendChild(snippetP);
    }

    li.append(idSpan, infoCol);
    host.appendChild(li);
  });
}

/* ------------------------------------------------------------------ Citations & Interactive Anchoring */

function formatTextWithCitations(raw, validIds) {
  if (!raw) return "";
  const escaped = String(raw)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped.replace(/\[(E\d+)\]/g, (match, id) => {
    if (!validIds.has(id)) return "";
    return `<a href="#source-${id}" class="citation mono" data-target="source-${id}">[${id}]</a>`;
  });
}

function wireCitationInteractions() {
  document.querySelectorAll(".citation").forEach((chip) => {
    chip.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = chip.dataset.target;
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
      targetEl.classList.add("flash");
      setTimeout(() => targetEl.classList.remove("flash"), 1600);
    });
  });
}

/* ------------------------------------------------------------------ Error State */

function showError(message, hint) {
  stopStream();
  $("error-message").textContent = message || "An unexpected error occurred.";
  $("error-hint").textContent = hint || "";
  showScreen("screen-error");
}
