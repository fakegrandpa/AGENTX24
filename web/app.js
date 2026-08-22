// AGENTX24 Autonomous Investigation Client Application

let currentEventSource = null;
let timerInterval = null;
let investigationStartTime = 0;
let knownEvidenceIds = new Set();

document.addEventListener("DOMContentLoaded", () => {
  initHealthCheck();
  initFormListeners();
  initPresetButtons();
});

// 1. Initial Health Check
async function initHealthCheck() {
  const healthStatusEl = document.getElementById("health-status-text");
  const toolsStatusEl = document.getElementById("tools-status-text");

  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.gemini_ready) {
      healthStatusEl.textContent = `Model: ${data.gemini_model} (Active)`;
      healthStatusEl.style.color = "#10B981";
    } else {
      healthStatusEl.textContent = `Model: ${data.gemini_status_message}`;
      healthStatusEl.style.color = "#D97706";
    }

    if (data.advertised_tools && data.advertised_tools.length > 0) {
      toolsStatusEl.textContent = `Active Tools: ${data.advertised_tools.join(", ")}`;
    }
  } catch (err) {
    healthStatusEl.textContent = "Server health check failed";
    healthStatusEl.style.color = "#EF4444";
  }
}

// 2. Preset suggestions buttons
function initPresetButtons() {
  const input = document.getElementById("target-input");
  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = btn.getAttribute("data-query");
      input.focus();
    });
  });
}

// 3. Form Submit & Investigation Flow
function initFormListeners() {
  const form = document.getElementById("investigate-form");
  const input = document.getElementById("target-input");
  const btnRestart = document.getElementById("btn-restart");
  const btnNewInv = document.getElementById("btn-new-investigation");
  const btnErrorRetry = document.getElementById("btn-error-retry");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    startInvestigation(query);
  });

  const resetToArrival = () => {
    stopInvestigation();
    showScreen("screen-arrival");
    input.value = "";
    input.focus();
  };

  btnRestart.addEventListener("click", resetToArrival);
  btnNewInv.addEventListener("click", resetToArrival);
  btnErrorRetry.addEventListener("click", resetToArrival);
}

function showScreen(screenId) {
  const screens = ["screen-arrival", "screen-investigating", "screen-report", "screen-error"];
  screens.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.style.display = id === screenId ? "block" : "none";
  });
}

async function startInvestigation(query) {
  showScreen("screen-investigating");
  document.getElementById("live-target-name").textContent = query;

  // Reset live state
  knownEvidenceIds.clear();
  document.getElementById("timeline-list").innerHTML = "";
  document.getElementById("evidence-list").innerHTML = "";
  document.getElementById("evidence-count").textContent = "0";

  // Start timer
  investigationStartTime = Date.now();
  updateTimerDisplay();
  clearInterval(timerInterval);
  timerInterval = setInterval(updateTimerDisplay, 1000);

  try {
    const res = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to initiate run" }));
      throw new Error(err.detail || "Server rejected investigation request");
    }

    const data = await res.json();
    const runId = data.run_id;

    // Connect SSE telemetry stream
    connectStream(runId, query);
  } catch (err) {
    showError(err.message, "Ensure Python backend is running on 127.0.0.1:8000.");
  }
}

function updateTimerDisplay() {
  const elapsedSec = Math.floor((Date.now() - investigationStartTime) / 1000);
  const mins = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
  const secs = String(elapsedSec % 60).padStart(2, "0");
  const timerEl = document.getElementById("live-timer");
  if (timerEl) timerEl.textContent = `${mins}:${secs}`;
}

function stopInvestigation() {
  if (currentEventSource) {
    currentEventSource.close();
    currentEventSource = null;
  }
  clearInterval(timerInterval);
}

// 4. SSE Stream Listener
function connectStream(runId, targetQuery) {
  if (currentEventSource) {
    currentEventSource.close();
  }

  currentEventSource = new EventSource(`/api/stream/${runId}`);

  currentEventSource.onmessage = async (event) => {
    try {
      const rawData = event.data;
      if (rawData.includes('"stream_end"')) {
        currentEventSource.close();
        // Fetch complete run record and show report
        await finalizeRunReport(runId);
        return;
      }

      const telemetryEvent = JSON.parse(rawData);
      handleTelemetryEvent(telemetryEvent, runId);
    } catch (err) {
      console.error("Telemetry parse error:", err);
    }
  };

  currentEventSource.onerror = async () => {
    // If stream disconnected, check if run completed
    if (currentEventSource) currentEventSource.close();
    try {
      const res = await fetch(`/api/run/${runId}`);
      if (res.ok) {
        const run = await res.json();
        if (run.status === "done" && run.report) {
          renderReport(run);
          return;
        } else if (run.status === "error") {
          showError(run.limitations[0] || "Investigation failed", "Check GEMINI_API_KEY configuration.");
          return;
        }
      }
    } catch (e) {}
  };
}

function handleTelemetryEvent(ev, runId) {
  const timeline = document.getElementById("timeline-list");

  // Mark previous items as done
  document.querySelectorAll(".timeline-item.active").forEach((el) => {
    el.classList.remove("active");
    el.classList.add("done");
  });

  const isProblem = ev.kind === "error" || ev.phase === "Error encountered" || ev.phase === "Source unavailable";

  // Create new timeline item
  const item = document.createElement("div");
  item.className = isProblem ? "timeline-item active warn" : "timeline-item active";

  const dot = document.createElement("div");
  dot.className = "phase-dot";

  const content = document.createElement("div");
  content.className = "timeline-content";

  const label = document.createElement("div");
  label.className = "phase-label";
  label.textContent = ev.phase || ev.text;

  content.appendChild(label);

  if (ev.detail) {
    const detail = document.createElement("div");
    detail.className = "phase-detail";
    detail.textContent = ev.detail;
    content.appendChild(detail);
  }

  item.appendChild(dot);
  item.appendChild(content);
  timeline.appendChild(item);

  // Cap timeline list to ~12 entries with auto-scroll
  while (timeline.children.length > 12) {
    timeline.removeChild(timeline.firstChild);
  }

  // Check for newly gathered evidence
  if (ev.kind === "tool_result") {
    fetchEvidenceUpdates(runId);
  }

  // A recoverable problem stays in the timeline. Whether the run actually failed
  // is decided from the final run status, so partial evidence is never discarded.
}

async function fetchEvidenceUpdates(runId) {
  try {
    const res = await fetch(`/api/run/${runId}`);
    if (!res.ok) return;
    const run = await res.json();

    const evidenceList = document.getElementById("evidence-list");
    const countBadge = document.getElementById("evidence-count");

    if (run.evidence) {
      countBadge.textContent = String(run.evidence.length);
      run.evidence.forEach((ev) => {
        if (!knownEvidenceIds.has(ev.id)) {
          knownEvidenceIds.add(ev.id);
          const card = createEvidenceCard(ev);
          evidenceList.prepend(card);
        }
      });
    }
  } catch (err) {
    console.error("Evidence update error:", err);
  }
}

function createEvidenceCard(ev) {
  const card = document.createElement("div");
  card.className = "evidence-card";

  const header = document.createElement("div");
  header.className = "evidence-header";

  const chip = document.createElement("span");
  chip.className = "evidence-chip";
  chip.textContent = ev.id;

  const source = document.createElement("span");
  source.className = "evidence-source";
  source.textContent = `${ev.source}${ev.published ? " · " + ev.published : ""}`;

  header.appendChild(chip);
  header.appendChild(source);

  const title = document.createElement("div");
  title.className = "evidence-title";
  title.textContent = ev.title;

  card.appendChild(header);
  card.appendChild(title);
  return card;
}

// 5. Final Report Rendering
async function finalizeRunReport(runId) {
  stopInvestigation();
  try {
    const res = await fetch(`/api/run/${runId}`);
    if (!res.ok) throw new Error("Failed to load completed run record.");
    const run = await res.json();

    if (run.status === "error") {
      showError(run.limitations[0] || "Investigation failed", "Check server logs.");
      return;
    }

    renderReport(run);
  } catch (err) {
    showError(err.message, "Could not fetch report details.");
  }
}

function renderReport(run) {
  showScreen("screen-report");

  const report = run.report;
  if (!report) {
    showError("No report generated for this run.", "Please try again.");
    return;
  }

  document.getElementById("report-target-name").textContent = run.query;
  const elapsedSec = Math.floor((Date.now() - investigationStartTime) / 1000);
  document.getElementById("report-metrics-badge").textContent = 
    `${run.tool_calls.length} tool calls · ${run.evidence.length} sources · ${elapsedSec}s`;

  // Summary
  document.getElementById("report-summary").innerHTML = formatTextWithCitations(report.summary);

  // Signals
  const signalsContainer = document.getElementById("report-signals");
  signalsContainer.innerHTML = "";

  if (report.signals && report.signals.length > 0) {
    report.signals.forEach((sig) => {
      const item = document.createElement("div");
      item.className = "signal-item";

      const header = document.createElement("div");
      header.className = "signal-header";

      const badge = document.createElement("span");
      badge.className = `tier-badge ${sig.tier}`;
      badge.textContent = `${sig.tier} Priority`;

      const headline = document.createElement("span");
      headline.className = "signal-headline";
      headline.textContent = sig.headline;

      header.appendChild(badge);
      header.appendChild(headline);

      const detail = document.createElement("div");
      detail.className = "signal-detail";
      detail.innerHTML = formatTextWithCitations(sig.detail);

      item.appendChild(header);
      item.appendChild(detail);
      signalsContainer.appendChild(item);
    });
  } else {
    signalsContainer.innerHTML = "<p class='signal-detail'>No distinct prioritized signals extracted.</p>";
  }

  // Adaptive Sections
  const adaptiveContainer = document.getElementById("report-adaptive-sections");
  adaptiveContainer.innerHTML = "";

  const sectionConfig = [
    { key: "research", title: "Key Research Developments" },
    { key: "competitor_industry", title: "Competitor & Industry Activity" },
    { key: "recent_developments", title: "Recent Developments" },
    { key: "patents", title: "Patent Signals" },
  ];

  if (report.sections) {
    sectionConfig.forEach((sec) => {
      const content = report.sections[sec.key];
      if (content && content.trim()) {
        const secDiv = document.createElement("div");
        secDiv.className = "report-section";

        const h3 = document.createElement("h3");
        h3.className = "section-heading";
        h3.textContent = sec.title;

        const body = document.createElement("div");
        body.className = "signal-detail";
        body.innerHTML = formatTextWithCitations(content);

        secDiv.appendChild(h3);
        secDiv.appendChild(body);
        adaptiveContainer.appendChild(secDiv);
      }
    });
  }

  // Why This Matters
  const whyMattersEl = document.getElementById("section-why-it-matters");
  if (report.sections && report.sections.why_it_matters) {
    whyMattersEl.style.display = "block";
    document.getElementById("report-why-it-matters-content").innerHTML = formatTextWithCitations(report.sections.why_it_matters);
  } else {
    whyMattersEl.style.display = "none";
  }

  // Next Actions
  const actionsEl = document.getElementById("section-next-actions");
  const actionsList = document.getElementById("report-next-actions-list");
  actionsList.innerHTML = "";
  if (report.next_actions && report.next_actions.length > 0) {
    actionsEl.style.display = "block";
    report.next_actions.forEach((act) => {
      const li = document.createElement("li");
      li.innerHTML = formatTextWithCitations(act);
      actionsList.appendChild(li);
    });
  } else {
    actionsEl.style.display = "none";
  }

  // Coverage & Limitations
  const limBox = document.getElementById("report-limitations-box");
  const limList = document.getElementById("report-limitations-list");
  limList.innerHTML = "";
  const allNotes = [...(report.coverage || []), ...(report.limitations || [])];

  if (allNotes.length > 0) {
    limBox.style.display = "block";
    allNotes.forEach((note) => {
      const li = document.createElement("li");
      li.textContent = note;
      limList.appendChild(li);
    });
  } else {
    limBox.style.display = "none";
  }

  // Verified Sources
  const sourcesContainer = document.getElementById("report-sources-list");
  sourcesContainer.innerHTML = "";

  if (run.evidence && run.evidence.length > 0) {
    run.evidence.forEach((ev) => {
      const sItem = document.createElement("div");
      sItem.className = "source-item";
      sItem.id = `source-${ev.id}`;

      const sId = document.createElement("span");
      sId.className = "source-id";
      sId.textContent = `[${ev.id}]`;

      const sBody = document.createElement("div");
      sBody.style.flex = "1";

      const sLink = document.createElement("a");
      sLink.className = "source-link";
      sLink.href = ev.url || "#";
      sLink.target = "_blank";
      sLink.rel = "noopener noreferrer";
      sLink.textContent = ev.title;

      const sMeta = document.createElement("div");
      sMeta.className = "source-meta";
      const metaParts = [ev.source];
      if (ev.published) metaParts.push(ev.published);
      if (ev.authors && ev.authors.length > 0) metaParts.push(ev.authors.join(", "));
      sMeta.textContent = metaParts.join(" · ");

      sBody.appendChild(sLink);
      sBody.appendChild(sMeta);

      sItem.appendChild(sId);
      sItem.appendChild(sBody);
      sourcesContainer.appendChild(sItem);
    });
  } else {
    sourcesContainer.innerHTML = "<p class='signal-detail'>No external sources recorded.</p>";
  }

  // Wire citation chips click events
  document.querySelectorAll(".citation-chip").forEach((chip) => {
    chip.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = chip.getAttribute("data-target");
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
        targetEl.style.backgroundColor = "#EFF6FF";
        setTimeout(() => {
          targetEl.style.backgroundColor = "";
        }, 1500);
      }
    });
  });
}

function formatTextWithCitations(rawText) {
  if (!rawText) return "";
  const escaped = rawText
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Transform [En] markers to interactive chips
  return escaped.replace(/\[(E\d+)\]/g, (match, cid) => {
    return `<a href="#source-${cid}" class="citation-chip" data-target="source-${cid}">[${cid}]</a>`;
  });
}

// 6. Error State Renderer
function showError(message, troubleshooting) {
  showScreen("screen-error");
  document.getElementById("error-message").textContent = message;
  document.getElementById("error-troubleshooting").textContent = 
    troubleshooting || "Please verify environment settings and try again.";
}
