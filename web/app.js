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
  renderedNodeSeqs: new Set(),
  toolCalls: 0,
  showEarlier: false,
  activeFilter: "all",
  activeFocus: null,
  hasMemoryEnabled: true,
  lastCallsVal: 0,
  lastSourcesVal: 0,
};

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  loadHealth();
  wireForm();
  wireExamples();
  wireNavigation();
  wireEvidenceFilters();
  wireCitationPeekDismiss();
});

/* ------------------------------------------------------------------ Health Check */

async function loadHealth() {
  const dot = $("status-dot");
  const model = $("status-model");
  const sources = $("status-sources");
  const memStatus = $("status-memory");
  const arrivalTools = $("arrival-tools");
  const arrivalAgents = $("arrival-agents");
  const arrivalMemNote = $("arrival-memory-note");

  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const tools = data.advertised_tools || [];
    const providersMap = data.providers || {};
    state.hasMemoryEnabled = data.memory_enabled !== false;

    if (dot) dot.className = `status-dot ${data.gemini_ready ? "ok" : "warn"}`;
    if (model) model.textContent = data.gemini_ready ? data.gemini_model : "model unconfigured";
    if (sources) {
      sources.textContent = `${tools.length} tools online`;
      sources.title = tools.join(", ");
    }

    if (memStatus) {
      if (data.memory_enabled !== false) {
        memStatus.textContent = `memory ${data.memory_records_count || 0}`;
      } else {
        memStatus.textContent = "memory off";
      }
    }

    // Render Specialized Agent Roster from real health API
    if (data.agents && arrivalAgents) {
      arrivalAgents.innerHTML = data.agents.map((a) => `
        <li class="ledger-row">
          <span class="ledger-code mono">${escapeHtml(a.id)}</span>
          <div class="ledger-desc">
            <span class="ledger-name">${escapeHtml(a.name)}</span>
            <span class="ledger-detail">${escapeHtml(a.responsibility || "")}</span>
          </div>
        </li>
      `).join("");
    }

    // Render Dispatchable Providers from real health API (no hardcoded map)
    if (arrivalTools) {
      const toolKeys = Object.keys(providersMap).length ? Object.keys(providersMap) : tools;
      arrivalTools.innerHTML = toolKeys.map((t) => {
        const provs = providersMap[t] || [];
        const isInactive = provs.length === 0;
        const provText = isInactive ? '<span style="color: var(--text-muted);">inactive</span>' : escapeHtml(provs.join(" · "));
        return `
          <li class="ledger-row">
            <span class="ledger-code mono">${escapeHtml(t)}</span>
            <div class="ledger-desc">
              <span class="ledger-name">${provText}</span>
            </div>
          </li>
        `;
      }).join("");
    }

    // Memory Note beneath providers
    if (arrivalMemNote) {
      if (data.memory_enabled !== false) {
        arrivalMemNote.textContent = `Persistent investigation memory: ${data.memory_records_count || 0} records`;
      } else {
        arrivalMemNote.textContent = "Persistent investigation memory: disabled";
      }
    }

    if (!data.gemini_ready) {
      showFieldError(data.gemini_status_message || "The reasoning model is not configured.");
    }
  } catch (err) {
    if (dot) dot.className = "status-dot down";
    if (model) model.textContent = "backend unreachable";
    if (sources) sources.textContent = "";
    if (memStatus) memStatus.textContent = "memory unavailable";
  }
}

/* ------------------------------------------------------------------ Deterministic State Derivation */

function deriveRunState(events) {
  let latestAgent = "investigator";
  const agentsSeen = new Set(["investigator"]);
  let isCompleted = false;
  const priorMemories = [];
  let openGaps = [];
  let contextUpdates = 0;
  let memoryWriteId = null;

  // Track merged tool runs
  const toolRuns = [];
  const activeToolMap = new Map(); // tool_name -> index in toolRuns

  events.forEach((ev) => {
    if (ev.agent) {
      const role = ev.agent.toLowerCase();
      latestAgent = role;
      agentsSeen.add(role);
    }

    const d = ev.data || {};

    if (ev.phase === "Relevant prior context retrieved") {
      if (Array.isArray(d.memories)) {
        d.memories.forEach((m) => priorMemories.push(m));
      }
    } else if (ev.phase === "Investigation context updated") {
      contextUpdates++;
    } else if (ev.phase === "Critique returned") {
      if (d.sufficient === false && Array.isArray(d.gaps)) {
        openGaps = [...d.gaps];
      } else if (d.sufficient === true) {
        openGaps = [];
      }
    } else if (ev.phase === "Investigation saved to memory") {
      memoryWriteId = d.memory_id || "persisted";
    } else if (ev.phase === "Completed") {
      isCompleted = true;
    }

    // Tool call lifecycle pairing
    if (ev.kind === "tool_selected") {
      const toolName = d.tool || "tool";
      const runItem = {
        seq: ev.seq,
        kind: "tool_selected",
        agent: ev.agent || "investigator",
        tool: toolName,
        query: d.query || "",
        reason: d.reason || "",
        status: "dispatching",
        newEvidence: 0,
        detail: null,
      };
      toolRuns.push(runItem);
      activeToolMap.set(toolName, toolRuns.length - 1);
    } else if (ev.kind === "tool_result") {
      const toolName = d.tool || "";
      if (activeToolMap.has(toolName)) {
        const idx = activeToolMap.get(toolName);
        toolRuns[idx].status = "returned";
        toolRuns[idx].newEvidence = d.new_evidence ?? 0;
        activeToolMap.delete(toolName);
      }
    } else if (ev.kind === "note" && (ev.phase === "No results for that angle" || ev.phase === "Source unavailable")) {
      const toolName = d.tool || "";
      if (activeToolMap.has(toolName)) {
        const idx = activeToolMap.get(toolName);
        if (ev.phase === "No results for that angle") {
          toolRuns[idx].status = "empty";
        } else {
          toolRuns[idx].status = "failed";
          toolRuns[idx].detail = d.error || ev.detail || "Source unavailable";
        }
        activeToolMap.delete(toolName);
      }
    }
  });

  const inFlightTool = activeToolMap.size > 0;

  return {
    latestAgent,
    agentsSeen,
    isCompleted,
    priorMemories,
    openGaps,
    contextUpdates,
    memoryWriteId,
    toolRuns,
    inFlightTool,
  };
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
    hideCitationPeek();
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
  state.renderedNodeSeqs = new Set();
  state.toolCalls = 0;
  state.lastCallsVal = 0;
  state.lastSourcesVal = 0;
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

  resetRelayStations();
  resetContextLedger();

  updateFocusBanner({
    agent: "investigator",
    phase: "INVESTIGATION STARTED",
    title: `Target: ${query}`,
    query: null,
    reason: null,
    inFlight: false,
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
      const derived = deriveRunState(state.events);

      processTelemetryEvent(ev, derived);
      renderAgentRelay(derived);
      renderContextLedger(derived);
      renderTimeline(derived);

      if (ev.kind === "tool_result" || ev.kind === "note") {
        refreshEvidence(runId);
      }
    } catch (err) {
      // transient parse
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
        showError(run.limitations && run.limitations[0] ? run.limitations[0] : "Investigation failed.", "See server logs for details.");
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
      showError(run.limitations && run.limitations[0] ? run.limitations[0] : "The investigation encountered an error.", "No verifiable evidence produced.");
      return;
    }
    renderReport(run);
  } catch (err) {
    showError(err.message, "Reload and try again.");
  }
}

/* ------------------------------------------------------------------ Agent Relay Strip */

function resetRelayStations() {
  ["relay-investigator", "relay-critic", "relay-synthesist"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.className = "relay-station is-standby";
    const stateEl = el.querySelector('[data-role="state"]');
    if (stateEl) stateEl.textContent = "STANDBY";
  });
}

function renderAgentRelay(derived) {
  const roles = [
    { id: "relay-investigator", key: "investigator" },
    { id: "relay-critic", key: "critic" },
    { id: "relay-synthesist", key: "synthesist" },
  ];

  roles.forEach(({ id, key }) => {
    const el = $(id);
    if (!el) return;
    const stateEl = el.querySelector('[data-role="state"]');

    if (derived.isCompleted) {
      el.className = "relay-station is-complete";
      if (stateEl) stateEl.textContent = "COMPLETE";
    } else if (derived.latestAgent === key) {
      el.className = "relay-station is-active";
      if (stateEl) stateEl.textContent = "ACTIVE";
    } else if (derived.agentsSeen.has(key)) {
      el.className = "relay-station is-handed-off";
      if (stateEl) stateEl.textContent = "HANDED OFF";
    } else {
      el.className = "relay-station is-standby";
      if (stateEl) stateEl.textContent = "STANDBY";
    }
  });
}

/* ------------------------------------------------------------------ Context & Memory Ledger */

function resetContextLedger() {
  const ledger = $("context-ledger");
  if (ledger) ledger.className = "context-ledger";
  if ($("ctx-prior")) $("ctx-prior").textContent = "0";
  if ($("ctx-evidence")) $("ctx-evidence").textContent = "0";
  if ($("ctx-updates")) $("ctx-updates").textContent = "0";
  if ($("ctx-gaps")) $("ctx-gaps").textContent = "0";
  if ($("ctx-memory")) $("ctx-memory").textContent = "—";
  if ($("ctx-status")) $("ctx-status").textContent = "Context is carried forward into every reasoning step";
  if ($("ctx-gap-line")) $("ctx-gap-line").hidden = true;
  if ($("ctx-prior-section")) $("ctx-prior-section").hidden = true;
  if ($("ctx-prior-rows")) $("ctx-prior-rows").innerHTML = "";
}

function renderContextLedger(derived) {
  const ledger = $("context-ledger");
  if (!ledger) return;

  const priorCount = derived.priorMemories.length;
  if ($("ctx-prior")) $("ctx-prior").textContent = String(priorCount);
  if ($("ctx-evidence")) $("ctx-evidence").textContent = String(state.evidenceList.length);
  if ($("ctx-updates")) $("ctx-updates").textContent = String(derived.contextUpdates);
  const gapCount = derived.openGaps.length;
  if ($("ctx-gaps")) $("ctx-gaps").textContent = String(gapCount);
  if ($("ctx-memory")) $("ctx-memory").textContent = derived.memoryWriteId ? `saved · ${derived.memoryWriteId}` : "—";

  if ($("ctx-status")) {
    $("ctx-status").textContent = priorCount > 0
      ? `Continuing from ${priorCount} prior investigation${priorCount === 1 ? "" : "s"}`
      : "Context is carried forward into every reasoning step";
  }

  if (priorCount > 0) {
    ledger.classList.add("has-prior");
    const priorSec = $("ctx-prior-section");
    const priorList = $("ctx-prior-rows");
    if (priorSec && priorList) {
      priorSec.hidden = false;
      priorList.innerHTML = derived.priorMemories.slice(0, 3).map((m) => `
        <li class="context-prior-row">
          <span class="prior-bullet">▸</span>
          <span><strong>${escapeHtml(m.objective || "Prior Target")}</strong> <span class="prior-date mono">(${escapeHtml((m.created_at || "").slice(0, 10))})</span></span>
        </li>
      `).join("");
    }
  }

  const gapLine = $("ctx-gap-line");
  const gapText = $("ctx-gap-text");
  if (gapLine && gapText) {
    if (gapCount > 0) {
      gapLine.hidden = false;
      gapText.textContent = derived.openGaps.join(" · ");
    } else {
      gapLine.hidden = true;
    }
  }
}

/* ------------------------------------------------------------------ Agent Focus Banner */

function processTelemetryEvent(ev, derived) {
  const d = ev.data || {};
  let agentRole = (ev.agent || "investigator").toLowerCase();
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
    agent: agentRole,
    phase: phaseTag,
    title: title,
    query: query,
    reason: reason,
    inFlight: derived ? derived.inFlightTool : false,
  });
}

function updateFocusBanner({ agent, phase, title, query, reason, inFlight }) {
  const agentEl = $("focus-agent");
  if (agentEl) {
    agentEl.textContent = agent.toUpperCase();
    agentEl.className = `focus-agent mono agent-${agent}`;
  }

  const phaseEl = $("focus-phase-tag");
  if (phaseEl) phaseEl.textContent = phase;

  const titleEl = $("focus-activity-title");
  if (titleEl) titleEl.textContent = title;

  const pulseLine = $("focus-pulse-line");
  if (pulseLine) {
    pulseLine.className = inFlight ? "focus-pulse-line is-dispatching" : "focus-pulse-line";
  }

  const now = new Date();
  const timeEl = $("focus-timestamp");
  if (timeEl) {
    timeEl.textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
  }

  const queryRow = $("focus-detail-row");
  const queryEl = $("focus-query");
  if (query && queryRow && queryEl) {
    queryEl.textContent = query;
    queryRow.hidden = false;
  } else if (queryRow) {
    queryRow.hidden = true;
  }

  const reasonEl = $("focus-reason");
  if (reason && reasonEl) {
    reasonEl.textContent = reason;
    reasonEl.hidden = false;
  } else if (reasonEl) {
    reasonEl.hidden = true;
  }
}

/* ------------------------------------------------------------------ Timeline Renderer */

function getNodeClasses(item, isLast) {
  const classes = ["timeline-node"];
  if (isLast) classes.push("is-active");
  if (item.kind === "tool_selected") classes.push("is-tool");
  else if (item.phase === "Reviewing evidence sufficiency" || item.phase === "Critique returned") classes.push("is-critic");
  else if (item.phase === "Composing intelligence report") classes.push("is-synthesist");
  else if (item.phase === "Identifying knowledge gaps") classes.push("is-gap");
  else if (item.kind === "error") classes.push("is-error");
  return classes.join(" ");
}

function buildMergedTimelineNode(item, isLast) {
  const li = document.createElement("li");
  li.className = getNodeClasses(item, isLast);

  const seq = document.createElement("div");
  seq.className = "node-seq mono";
  seq.textContent = String(item.seq).padStart(2, "0");

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
  const agentRole = (item.agent || "investigator").toLowerCase();
  const agentBadge = document.createElement("span");
  agentBadge.className = `node-agent-badge mono agent-${agentRole}`;
  agentBadge.textContent = agentRole;
  titleRow.appendChild(agentBadge);

  const title = document.createElement("span");
  title.className = "node-title";

  const d = item.data || {};

  if (item.kind === "tool_selected") {
    title.textContent = "Selected ";
    const toolTag = document.createElement("span");
    toolTag.className = "node-tool-tag mono";
    toolTag.textContent = item.tool || "tool";
    title.appendChild(toolTag);
  } else if (item.kind === "objective") {
    title.textContent = "Investigation initiated";
  } else if (item.phase === "Critique returned") {
    title.textContent = d.sufficient ? "Evidence Sufficiency Confirmed" : "Evidence Sufficiency Check: Gaps Found";
  } else {
    title.textContent = item.phase || "Reasoning Step";
  }

  titleRow.appendChild(title);
  content.appendChild(titleRow);

  // Metadata rows
  if (item.kind === "tool_selected") {
    const kv = document.createElement("div");
    kv.className = "node-meta-kv";

    if (item.query) {
      const row = document.createElement("div");
      row.className = "node-kv-row";
      row.innerHTML = `<span class="node-kv-label">QUERY</span><span class="node-kv-query mono">${escapeHtml(item.query)}</span>`;
      kv.appendChild(row);
    }

    if (item.reason) {
      const row = document.createElement("div");
      row.className = "node-kv-row";
      row.innerHTML = `<span class="node-kv-label">WHY</span><span class="node-kv-reason">${escapeHtml(item.reason)}</span>`;
      kv.appendChild(row);
    }

    // Status line: dispatching / returned / empty / failed
    const statusLine = document.createElement("div");
    statusLine.className = "node-status-line";
    if (item.status === "dispatching") {
      statusLine.innerHTML = `<span class="status-dispatching mono"><span class="status-dispatch-dot"></span>DISPATCHING…</span>`;
    } else if (item.status === "returned") {
      statusLine.innerHTML = `<span class="status-returned mono">RETURNED · ${item.newEvidence} fragments</span>`;
    } else if (item.status === "empty") {
      statusLine.innerHTML = `<span class="status-empty mono">NO RESULTS</span>`;
    } else if (item.status === "failed") {
      statusLine.innerHTML = `<span class="status-failed mono">UNAVAILABLE · ${escapeHtml(item.detail || "")}</span>`;
    }
    kv.appendChild(statusLine);

    content.appendChild(kv);
  } else if (item.phase === "Critique returned") {
    const kv = document.createElement("div");
    kv.className = "node-meta-kv";

    const vRow = document.createElement("div");
    vRow.className = "node-kv-row";
    vRow.innerHTML = `<span class="node-kv-label">VERDICT</span><span class="node-kv-reason">${d.sufficient ? "Sufficient (Approved)" : "Insufficient (Follow-up Required)"}</span>`;
    kv.appendChild(vRow);

    if (d.gaps && Array.isArray(d.gaps) && d.gaps.length > 0) {
      const gapBlock = document.createElement("div");
      gapBlock.className = "node-gaps-block";
      d.gaps.forEach((g) => {
        const gItem = document.createElement("div");
        gItem.className = "node-gap-item";
        gItem.textContent = `▸ ${g}`;
        gapBlock.appendChild(gItem);
      });
      kv.appendChild(gapBlock);
    }

    content.appendChild(kv);
  } else if (item.phase === "Identifying knowledge gaps" && (d.reason || item.detail)) {
    const kv = document.createElement("div");
    kv.className = "node-meta-kv";
    const gRow = document.createElement("div");
    gRow.className = "node-kv-row";
    gRow.innerHTML = `<span class="node-kv-label">GAP</span><span class="node-kv-reason">${escapeHtml(d.reason || item.detail || "")}</span>`;
    kv.appendChild(gRow);
    content.appendChild(kv);
  } else if (item.detail) {
    const note = document.createElement("div");
    note.className = "node-detail-note";
    note.textContent = item.detail;
    content.appendChild(note);
  }

  li.append(seq, rail, content);
  return li;
}

function renderTimeline(derived) {
  const list = $("timeline");
  const toggle = $("earlier-toggle");
  if (!list) return;

  // Build timeline items: non-tool events + merged tool runs
  const nonToolEvents = state.events.filter((e) => e.kind !== "tool_selected" && e.kind !== "tool_result" && !(e.kind === "note" && (e.phase === "No results for that angle" || e.phase === "Source unavailable")));
  const allTimelineItems = [...nonToolEvents, ...(derived ? derived.toolRuns : [])].sort((a, b) => a.seq - b.seq);

  $("timeline-count").textContent = `${allTimelineItems.length} step${allTimelineItems.length === 1 ? "" : "s"}`;

  const hiddenCount = Math.max(0, allTimelineItems.length - VISIBLE_NODE_CAP);
  const shown = state.showEarlier || hiddenCount === 0 ? allTimelineItems : allTimelineItems.slice(hiddenCount);

  if (toggle) {
    if (hiddenCount > 0) {
      toggle.hidden = false;
      toggle.textContent = state.showEarlier
        ? `Hide earlier steps (${hiddenCount})`
        : `Show earlier steps (${hiddenCount})`;
      toggle.onclick = () => {
        state.showEarlier = !state.showEarlier;
        renderTimeline(derived);
      };
    } else {
      toggle.hidden = true;
    }
  }

  list.innerHTML = "";
  shown.forEach((item, i) => list.appendChild(buildMergedTimelineNode(item, i === shown.length - 1)));

  // Metric updates with valueBump
  const toolCallsCount = (derived ? derived.toolRuns : []).length;
  const callsEl = $("metric-calls");
  if (callsEl) {
    callsEl.textContent = String(toolCallsCount);
    if (toolCallsCount !== state.lastCallsVal) {
      callsEl.classList.remove("bump");
      void callsEl.offsetWidth; // trigger reflow
      callsEl.classList.add("bump");
      state.lastCallsVal = toolCallsCount;
    }
  }
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
    const sourcesEl = $("metric-sources");
    if (sourcesEl) {
      sourcesEl.textContent = String(total);
      if (total !== state.lastSourcesVal) {
        sourcesEl.classList.remove("bump");
        void sourcesEl.offsetWidth;
        sourcesEl.classList.add("bump");
        state.lastSourcesVal = total;
      }
    }
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

  filtered.slice().reverse().forEach((ev, idx) => {
    const isNew = !state.seenEvidence.has(ev.id);
    state.seenEvidence.add(ev.id);
    list.appendChild(createEvidenceFragmentElement(ev, isNew ? Math.min(idx, 8) * 40 : 0));
  });
}

function createEvidenceFragmentElement(ev, staggerMs) {
  const card = document.createElement("li");
  card.className = "evidence-fragment";
  card.id = `live-ev-${ev.id}`;
  if (staggerMs) {
    card.style.animationDelay = `${staggerMs}ms`;
  }

  const header = document.createElement("div");
  header.className = "ev-header";

  const badge = document.createElement("span");
  badge.className = "ev-badge mono";
  badge.textContent = `[${ev.id}]`;

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
      metaInfo += `<strong>Authors:</strong> ${escapeHtml(ev.authors.slice(0, 4).join(", "))}<br>`;
    }
    if (ev.snippet) {
      metaInfo += `<p>${escapeHtml(ev.snippet)}</p>`;
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

  // Masthead byline
  const runIdEl = $("report-run-id");
  if (runIdEl) runIdEl.textContent = state.runId || run.id || "run_complete";

  const genEl = $("report-generated");
  if (genEl) {
    const ts = run.finished_at ? new Date(run.finished_at) : new Date();
    genEl.textContent = isNaN(ts.getTime()) ? new Date().toLocaleTimeString() : ts.toLocaleTimeString();
  }

  // Calculate speed / time
  let elapsed = Math.max(1, Math.round((Date.now() - state.startedAt) / 1000));
  if (run.started_at && run.finished_at) {
    const s = new Date(run.started_at).getTime();
    const f = new Date(run.finished_at).getTime();
    if (!isNaN(s) && !isNaN(f) && f > s) {
      elapsed = Math.round((f - s) / 1000);
    }
  }

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
    ["competitor_industry", "03", "COMPETITIVE & INDUSTRY ACTIVITY"],
    ["research", "04", "KEY RESEARCH & SCIENTIFIC DEVELOPMENTS"],
    ["patents", "05", "PATENT & IP LANDSCAPE"],
    ["recent_developments", "06", "RECENT TIMELINE & STRATEGIC SHIFTS"],
    ["why_it_matters", "07", "STRATEGIC IMPLICATIONS & WHY THIS MATTERS"],
  ];

  const sections = report.sections || {};
  sectionDefs.forEach(([key, idxStr, title]) => {
    const val = sections[key];
    if (!val || !String(val).trim()) return;

    const secEl = document.createElement("section");
    secEl.className = "report-section";

    const badgeRow = document.createElement("div");
    badgeRow.className = "section-badge-row";
    const idxSpan = document.createElement("span");
    idxSpan.className = "section-idx mono";
    idxSpan.textContent = idxStr;
    const tag = document.createElement("span");
    tag.className = "section-tag";
    tag.textContent = title;
    badgeRow.append(idxSpan, tag);

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

  const counts = { news: 0, research: 0, patent: 0, web: 0 };
  evidence.forEach((ev) => {
    const k = (ev.provider_kind || ev.tool || "").toLowerCase();
    if (k.includes("news")) counts.news++;
    else if (k.includes("research")) counts.research++;
    else if (k.includes("patent")) counts.patent++;
    else counts.web++;
  });

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
        seg.style.width = "0%";
        seg.title = `${k.label}: ${k.count} (${pct}%)`;
        bar.appendChild(seg);

        // Animate width from 0
        setTimeout(() => { seg.style.width = `${pct}%`; }, 60);

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
      <span class="prov-name mono">${escapeHtml(tool)}</span>
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

/* ------------------------------------------------------------------ Citations & Inspector */

function formatTextWithCitations(raw, validIds) {
  if (!raw) return "";
  const escaped = String(raw)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped.replace(/\[(E\d+)\]/g, (match, id) => {
    if (!validIds.has(id)) return "";
    return `<a href="#source-${id}" class="citation mono" data-id="${id}" data-target="source-${id}">[${id}]</a>`;
  });
}

function wireCitationInteractions() {
  const peek = $("citation-peek");

  document.querySelectorAll(".citation").forEach((chip) => {
    const id = chip.dataset.id;

    // Hover / Focus Inspector
    const showPeek = () => {
      if (!peek) return;
      const ev = state.evidenceList.find((e) => e.id === id);
      if (!ev) return;

      $("peek-id").textContent = `[${ev.id}]`;
      $("peek-tool").textContent = ev.tool || "tool";
      $("peek-title").textContent = ev.title || "—";

      const metaParts = [ev.source];
      if (ev.published) metaParts.push(ev.published);
      if (ev.authors && ev.authors.length) metaParts.push(ev.authors.slice(0, 2).join(", "));
      $("peek-meta").textContent = metaParts.join(" · ");
      $("peek-snippet").textContent = ev.snippet || "";

      peek.hidden = false;

      const rect = chip.getBoundingClientRect();
      const peekRect = peek.getBoundingClientRect();
      let top = rect.bottom + 8;
      let left = rect.left;

      if (left + 340 > window.innerWidth) {
        left = window.innerWidth - 350;
      }
      if (top + 160 > window.innerHeight) {
        top = rect.top - peekRect.height - 8;
      }

      peek.style.top = `${Math.max(10, top)}px`;
      peek.style.left = `${Math.max(10, left)}px`;
    };

    chip.addEventListener("mouseenter", showPeek);
    chip.addEventListener("focus", showPeek);
    chip.addEventListener("mouseleave", hideCitationPeek);
    chip.addEventListener("blur", hideCitationPeek);

    // Click: Smooth scroll & flash highlight
    chip.addEventListener("click", (e) => {
      e.preventDefault();
      hideCitationPeek();
      const targetId = chip.dataset.target;
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
      targetEl.classList.add("flash");
      setTimeout(() => targetEl.classList.remove("flash"), 1600);
    });
  });
}

function hideCitationPeek() {
  const peek = $("citation-peek");
  if (peek) peek.hidden = true;
}

function wireCitationPeekDismiss() {
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideCitationPeek();
  });
  window.addEventListener("scroll", hideCitationPeek, { passive: true });
}

/* ------------------------------------------------------------------ Error State */

function showError(message, hint) {
  stopStream();
  $("error-message").textContent = message || "An unexpected error occurred.";
  $("error-hint").textContent = hint || "";
  showScreen("screen-error");
}

/* ------------------------------------------------------------------ Helpers */

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
