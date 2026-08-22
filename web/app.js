/* ==========================================================================
   AGENTX24 — Autonomous Research Intelligence · client
   Renders ONLY what the backend reports. No progress, reason, evidence or URL
   is ever invented here: every value comes from a TelemetryEvent or the Run JSON.
   ========================================================================== */

const VISIBLE_NODE_CAP = 14;
const SIGNIFICANCE = { high: "High", important: "Medium", emerging: "Low" };
const SIGNIFICANCE_CLASS = { high: "high", important: "medium", emerging: "low" };

const state = {
  runId: null,
  source: null,
  clock: null,
  startedAt: 0,
  events: [],
  seenEvidence: new Set(),
  toolCalls: 0,
  evidence: 0,
  showEarlier: false,
};

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  loadHealth();
  wireForm();
  wireExamples();
  wireNavigation();
});

/* ------------------------------------------------------------------ health */

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
    dot.classList.add(data.gemini_ready ? "ok" : "warn");
    model.textContent = data.gemini_ready ? data.gemini_model : "model unconfigured";
    sources.textContent = `${tools.length} sources online`;
    sources.title = tools.join(", ");
    arrivalTools.textContent = tools.join("  ·  ") || "none";

    if (!data.gemini_ready) {
      showFieldError(data.gemini_status_message || "The reasoning model is not configured.");
    }
  } catch (err) {
    dot.classList.add("down");
    model.textContent = "backend unreachable";
    sources.textContent = "";
    arrivalTools.textContent = "unavailable";
  }
}

/* -------------------------------------------------------------- navigation */

function showScreen(id) {
  ["screen-arrival", "screen-run", "screen-report", "screen-error"].forEach((s) => {
    $(s).hidden = s !== id;
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

  $("trace-toggle").addEventListener("click", () => {
    const runScreen = $("screen-run");
    const opening = runScreen.hidden;
    runScreen.hidden = !opening;
    $("trace-toggle").setAttribute("aria-expanded", String(opening));
    $("trace-toggle").lastElementChild.textContent = opening ? "Hide decision trace" : "Show decision trace";
    if (opening) runScreen.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

/* -------------------------------------------------------------- input form */

function wireExamples() {
  $("examples").querySelectorAll(".example-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const input = $("target-input");
      input.value = chip.dataset.q;
      clearFieldError();
      input.focus();
    });
  });
}

function showFieldError(message) {
  $("input-error").textContent = message;
  $("input-row").classList.add("invalid");
}

function clearFieldError() {
  $("input-error").textContent = "";
  $("input-row").classList.remove("invalid");
}

function wireForm() {
  const form = $("investigate-form");
  const input = $("target-input");

  input.addEventListener("input", clearFieldError);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (query.length < 3) {
      showFieldError("Enter at least 3 characters describing what to investigate.");
      input.focus();
      return;
    }
    clearFieldError();
    startInvestigation(query);
  });
}

/* ---------------------------------------------------------------- run flow */

async function startInvestigation(query) {
  state.events = [];
  state.seenEvidence = new Set();
  state.toolCalls = 0;
  state.evidence = 0;
  state.showEarlier = false;
  state.startedAt = Date.now();

  $("run-target").textContent = query;
  $("timeline").innerHTML = "";
  $("evidence-list").innerHTML = "";
  $("evidence-count").textContent = "0";
  $("evidence-placeholder").hidden = false;
  $("timeline-count").textContent = "0 steps";
  $("metric-calls").textContent = "0 tool calls";
  $("metric-sources").textContent = "0 sources";
  $("earlier-toggle").hidden = true;
  $("trace-toggle").setAttribute("aria-expanded", "false");
  $("trace-toggle").lastElementChild.textContent = "Show decision trace";

  showScreen("screen-run");
  startClock();

  try {
    const res = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Server rejected the request (HTTP ${res.status}).`);
    }
    const data = await res.json();
    state.runId = data.run_id;
    openStream(data.run_id);
  } catch (err) {
    stopClock();
    showError(err.message, "Confirm the backend is running on 127.0.0.1:8000.");
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
  $("metric-clock").textContent = `${mm}:${ss}`;
}

function stopClock() { clearInterval(state.clock); }

function stopStream() {
  if (state.source) {
    state.source.close();
    state.source = null;
  }
  stopClock();
}

function openStream(runId) {
  if (state.source) state.source.close();
  state.source = new EventSource(`/api/stream/${runId}`);

  state.source.onmessage = async (msg) => {
    if (msg.data.includes('"stream_end"')) {
      stopStream();
      await finalize(runId);
      return;
    }
    try {
      const ev = JSON.parse(msg.data);
      state.events.push(ev);
      renderTimeline();
      if (ev.data && typeof ev.data.total_evidence === "number") {
        // fall through to the authoritative refresh below
      }
      if (ev.kind === "tool_result" || ev.kind === "note") refreshEvidence(runId);
    } catch (err) {
      console.error("telemetry parse failed", err);
    }
  };

  // A dropped stream is not automatically a failure: ask the server what happened.
  state.source.onerror = async () => {
    stopStream();
    try {
      const res = await fetch(`/api/run/${runId}`);
      if (!res.ok) throw new Error("run unavailable");
      const run = await res.json();
      if (run.status === "done") renderReport(run);
      else if (run.status === "error") showError(run.limitations[0] || "The investigation failed.", "See the server log for detail.");
    } catch (err) {
      showError("Lost connection to the investigation stream.", "The backend may have stopped.");
    }
  };
}

async function finalize(runId) {
  try {
    const res = await fetch(`/api/run/${runId}`);
    if (!res.ok) throw new Error("Could not load the completed run.");
    const run = await res.json();
    if (run.status === "error") {
      showError(run.limitations[0] || "The investigation failed.", "No verifiable evidence was produced.");
      return;
    }
    renderReport(run);
  } catch (err) {
    showError(err.message, "Reload the page and try again.");
  }
}

/* ------------------------------------------------------- timeline renderer */

function nodeVariant(ev) {
  if (ev.kind === "error") return "is-error";
  if (ev.kind === "tool_selected") return "is-tool";
  if (ev.kind === "tool_result") return "is-result";
  if (ev.phase === "Identifying knowledge gaps") return "is-gap";
  if (ev.phase === "Source unavailable" || ev.phase === "No results for that angle") return "is-warn";
  return "";
}

function nodeTitle(ev) {
  switch (ev.kind) {
    case "objective": return "Investigation defined";
    case "tool_selected": return null;           // rendered with a tool chip
    case "tool_result": return "Analyzed returned evidence";
    default: return ev.phase;
  }
}

function buildNode(ev, isLast) {
  const li = document.createElement("li");
  li.className = `node ${nodeVariant(ev)}`.trim();
  if (isLast) li.classList.add("is-active");

  const step = document.createElement("div");
  step.className = "node-step";
  step.textContent = String(ev.seq).padStart(2, "0");

  const rail = document.createElement("div");
  rail.className = "node-rail";
  const dot = document.createElement("span");
  dot.className = "node-dot";
  rail.appendChild(dot);

  const body = document.createElement("div");

  const title = document.createElement("div");
  title.className = "node-title";
  const d = ev.data || {};

  if (ev.kind === "tool_selected") {
    title.append(document.createTextNode("Selected "));
    const tool = document.createElement("span");
    tool.className = "node-tool";
    tool.textContent = d.tool || "tool";
    title.appendChild(tool);
  } else {
    title.textContent = nodeTitle(ev);
  }
  body.appendChild(title);

  // Machine facts, straight from telemetry
  if (ev.kind === "tool_selected") {
    const kv = document.createElement("div");
    kv.className = "kv";
    if (d.query) kv.append(kvKey("Query"), kvValue(d.query, "kv-query"));
    if (d.reason) kv.append(kvKey("Reason"), kvValue(d.reason, "kv-reason"));
    if (kv.childElementCount) body.appendChild(kv);
  } else if (ev.phase === "Identifying knowledge gaps" && d.reason) {
    const kv = document.createElement("div");
    kv.className = "kv";
    kv.append(kvKey("Gap"), kvValue(d.reason, "kv-reason"));
    body.appendChild(kv);
  } else if (ev.detail) {
    const note = document.createElement("div");
    note.className = "node-note";
    note.textContent = ev.detail;
    body.appendChild(note);
  }

  if (ev.kind === "tool_result" && typeof d.new_evidence === "number") {
    const note = document.createElement("div");
    note.className = "node-note";
    note.textContent = `${d.new_evidence} new · ${d.total_evidence ?? "?"} total sources`;
    body.appendChild(note);
  }

  li.append(step, rail, body);
  return li;
}

function kvKey(label) {
  const el = document.createElement("div");
  el.className = "kv-key";
  el.textContent = label;
  return el;
}

function kvValue(text, cls) {
  const el = document.createElement("div");
  el.className = cls;
  el.textContent = text;
  return el;
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
    toggle.onclick = () => { state.showEarlier = !state.showEarlier; renderTimeline(); };
  } else {
    toggle.hidden = true;
  }

  list.innerHTML = "";
  shown.forEach((ev, i) => list.appendChild(buildNode(ev, i === shown.length - 1)));

  // Live counters, derived from real events only
  state.toolCalls = events.filter((e) => e.kind === "tool_selected").length;
  $("metric-calls").textContent = `${state.toolCalls} tool call${state.toolCalls === 1 ? "" : "s"}`;
}

/* ------------------------------------------------------- evidence renderer */

async function refreshEvidence(runId) {
  try {
    const res = await fetch(`/api/run/${runId}`);
    if (!res.ok) return;
    const run = await res.json();
    const list = $("evidence-list");

    (run.evidence || []).forEach((ev) => {
      if (state.seenEvidence.has(ev.id)) return;
      state.seenEvidence.add(ev.id);
      list.prepend(evidenceItem(ev));
    });

    state.evidence = (run.evidence || []).length;
    $("evidence-count").textContent = String(state.evidence);
    $("metric-sources").textContent = `${state.evidence} source${state.evidence === 1 ? "" : "s"}`;
    $("evidence-placeholder").hidden = state.evidence > 0;
  } catch (err) {
    /* transient; the authoritative fetch happens again at completion */
  }
}

function evidenceItem(ev) {
  const li = document.createElement("li");
  li.className = "evidence-item";

  const top = document.createElement("div");
  top.className = "evidence-top";

  const id = document.createElement("span");
  id.className = "ev-id";
  id.textContent = ev.id;

  const src = document.createElement("span");
  src.className = "ev-src";
  src.textContent = ev.published ? `${ev.source} · ${ev.published}` : ev.source;

  const tool = document.createElement("span");
  tool.className = "ev-tool";
  tool.textContent = ev.tool;

  top.append(id, src, tool);

  const title = document.createElement("div");
  title.className = "ev-title";
  title.textContent = ev.title;

  li.append(top, title);
  return li;
}

/* --------------------------------------------------------- report renderer */

function renderReport(run) {
  const report = run.report;
  if (!report) {
    showError("No report was produced for this investigation.", "Try a different objective.");
    return;
  }

  showScreen("screen-report");
  $("screen-run").hidden = true;
  $("report-target").textContent = run.query;

  const elapsed = Math.max(1, Math.round((Date.now() - state.startedAt) / 1000));
  const toolsUsed = [...new Set((run.tool_calls || []).map((t) => t.name))];
  $("trace-summary").textContent =
    `${state.events.length} steps · ${(run.tool_calls || []).length} tool calls · ` +
    `${toolsUsed.length} sources · ${(run.evidence || []).length} evidence · ${elapsed}s`;

  const validIds = new Set((run.evidence || []).map((e) => e.id));

  // Executive intelligence
  $("report-summary").innerHTML = withCitations(report.summary, validIds);

  // Key signals
  const signalsHost = $("report-signals");
  signalsHost.innerHTML = "";
  const signals = report.signals || [];
  if (signals.length) {
    signals.forEach((sig) => signalsHost.appendChild(signalCard(sig, validIds)));
  } else {
    signalsHost.innerHTML = `<p class="placeholder">The agent did not extract distinct prioritized signals for this investigation.</p>`;
  }

  // Adaptive sections — rendered only when the backend supplied content
  const sectionsHost = $("report-sections");
  sectionsHost.innerHTML = "";
  const sectionMap = [
    ["competitor_industry", "Competitive implications"],
    ["research", "Research signals"],
    ["patents", "Patent signals"],
    ["recent_developments", "Recent developments"],
    ["why_it_matters", "Why this matters"],
  ];
  const sections = report.sections || {};
  sectionMap.forEach(([key, label]) => {
    const value = sections[key];
    if (!value || !String(value).trim()) return;
    const block = document.createElement("div");
    block.className = "block";
    const head = document.createElement("h2");
    head.className = "block-head";
    head.textContent = label;
    const prose = document.createElement("div");
    prose.className = "prose";
    prose.innerHTML = withCitations(value, validIds);
    block.append(head, prose);
    sectionsHost.appendChild(block);
  });

  // Recommended next actions
  const actions = report.next_actions || [];
  $("block-actions").hidden = actions.length === 0;
  const actionsHost = $("report-actions");
  actionsHost.innerHTML = "";
  actions.forEach((a) => {
    const li = document.createElement("li");
    li.innerHTML = withCitations(a, validIds);
    actionsHost.appendChild(li);
  });

  // Knowledge gaps & limitations
  const limits = report.limitations || [];
  $("block-limitations").hidden = limits.length === 0;
  const limitsHost = $("report-limitations");
  limitsHost.innerHTML = "";
  limits.forEach((l) => {
    const li = document.createElement("li");
    li.textContent = l;
    limitsHost.appendChild(li);
  });

  renderCoverage(run, toolsUsed);
  renderSources(run);
  wireCitations();
}

function signalCard(sig, validIds) {
  const card = document.createElement("article");
  card.className = "signal";

  const top = document.createElement("div");
  top.className = "signal-top";

  const badge = document.createElement("span");
  badge.className = `sig-badge ${SIGNIFICANCE_CLASS[sig.tier] || "low"}`;
  badge.textContent = SIGNIFICANCE[sig.tier] || sig.tier;

  const headline = document.createElement("h3");
  headline.className = "signal-headline";
  headline.textContent = sig.headline;

  top.append(badge, headline);

  const detail = document.createElement("div");
  detail.className = "signal-detail prose";
  detail.innerHTML = withCitations(sig.detail, validIds);

  card.append(top, detail);
  return card;
}

function renderCoverage(run, toolsUsed) {
  const stats = [
    [(run.evidence || []).length, "Evidence items"],
    [toolsUsed.length, "Sources used"],
    [(run.tool_calls || []).length, "Tool calls"],
  ];
  const host = $("coverage-stats");
  host.innerHTML = "";
  stats.forEach(([value, label]) => {
    const box = document.createElement("div");
    box.className = "stat";
    const v = document.createElement("div");
    v.className = "stat-value";
    v.textContent = String(value);
    const l = document.createElement("div");
    l.className = "stat-label";
    l.textContent = label;
    box.append(v, l);
    host.appendChild(box);
  });

  // Per-tool breakdown, computed from the real run record
  const list = $("coverage-list");
  list.innerHTML = "";
  toolsUsed.forEach((tool) => {
    const calls = (run.tool_calls || []).filter((t) => t.name === tool);
    const items = (run.evidence || []).filter((e) => e.tool === tool).length;
    const failed = calls.filter((c) => !c.ok).length;

    const row = document.createElement("li");
    row.className = "coverage-row";

    const name = document.createElement("span");
    name.className = "mono";
    name.textContent = tool;

    const detail = document.createElement("span");
    detail.textContent = `${calls.length} call${calls.length === 1 ? "" : "s"} · ${items} evidence item${items === 1 ? "" : "s"}`;

    const status = document.createElement("span");
    status.className = "spacer";
    status.textContent = failed ? `${failed} failed` : "ok";

    row.append(name, detail, status);
    list.appendChild(row);
  });
}

function renderSources(run) {
  const host = $("report-sources");
  host.innerHTML = "";
  const evidence = run.evidence || [];

  if (!evidence.length) {
    host.innerHTML = `<p class="placeholder">No verifiable sources were returned by the tools the agent selected.</p>`;
    return;
  }

  evidence.forEach((ev) => {
    const li = document.createElement("li");
    li.className = "source-row";
    li.id = `source-${ev.id}`;

    const id = document.createElement("span");
    id.className = "source-id";
    id.textContent = `[${ev.id}]`;

    const body = document.createElement("div");

    const title = document.createElement("div");
    title.className = "source-title";
    if (ev.url) {
      const link = document.createElement("a");
      link.href = ev.url;                    // only ever an evidence-store URL
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = ev.title;
      title.appendChild(link);
    } else {
      title.textContent = ev.title;
    }

    const meta = document.createElement("div");
    meta.className = "source-meta";
    const parts = [ev.source];
    if (ev.published) parts.push(ev.published);
    if (ev.authors && ev.authors.length) parts.push(ev.authors.slice(0, 3).join(", "));
    parts.push(ev.tool);
    meta.textContent = parts.join(" · ");

    body.append(title, meta);
    li.append(id, body);
    host.appendChild(li);
  });
}

/* ------------------------------------------------- citations & escaping */

function withCitations(raw, validIds) {
  if (!raw) return "";
  const escaped = String(raw)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Only markers that resolve to a real evidence record become links.
  return escaped.replace(/\[(E\d+)\]/g, (match, id) => {
    if (!validIds.has(id)) return "";
    return `<a href="#source-${id}" class="citation" data-target="source-${id}">[${id}]</a>`;
  });
}

function wireCitations() {
  document.querySelectorAll(".citation").forEach((chip) => {
    chip.addEventListener("click", (e) => {
      e.preventDefault();
      const target = document.getElementById(chip.dataset.target);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.classList.add("flash");
      setTimeout(() => target.classList.remove("flash"), 1400);
    });
  });
}

/* ---------------------------------------------------------------- errors */

function showError(message, hint) {
  stopStream();
  $("error-message").textContent = message || "An unexpected error occurred.";
  $("error-hint").textContent = hint || "";
  showScreen("screen-error");
}
