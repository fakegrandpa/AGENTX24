/* ==========================================================================
   AGENTX24 — Autonomous Intelligence Office (web/office.js)
   Living workflow visualization driven exclusively by real SSE telemetry.
   Layering: interpretEvent (pure) -> reducer (state) -> renderOffice (DOM/CSS)
   ========================================================================== */

(function () {
  "use strict";

  // 1. Authoritative Office Geometry (BUILD3.md)
  const OFFICE_LAYOUT = {
    manager: {
      cabin: { x: 340, y: 24, w: 520, h: 208 },
      desk: { x: 520, y: 168, w: 160, h: 44 },
      figure: { x: 600, y: 150 },
      plate: { x: 360, y: 44, w: 480, h: 52 },
      phaseChip: { x: 600, y: 116 },
      tray: { x: 700, y: 150, w: 140, h: 62 },
    },
    corridor: {
      spineY: 290,
      trunkX: 600,
      trunkY1: 232,
      trunkY2: 290,
    },
    workers: {
      research_search: {
        id: "research",
        name: "Research Intelligence",
        tool: "research_search",
        category: "A",
        desk: { x: 120, y: 372, w: 160, h: 56 },
        center: { x: 200, y: 400 },
        fieldZone: { x: 200, y: 490 },
      },
      news_search: {
        id: "news",
        name: "News Intelligence",
        tool: "news_search",
        category: "A",
        desk: { x: 370, y: 372, w: 160, h: 56 },
        center: { x: 450, y: 400 },
        fieldZone: { x: 450, y: 490 },
      },
      web_search: {
        id: "web",
        name: "Web Intelligence",
        tool: "web_search",
        category: "A",
        desk: { x: 670, y: 372, w: 160, h: 56 },
        center: { x: 750, y: 400 },
        fieldZone: { x: 750, y: 490 },
      },
      patent_search: {
        id: "patent",
        name: "Patent Intelligence",
        tool: "patent_search",
        category: "A",
        desk: { x: 920, y: 372, w: 160, h: 56 },
        center: { x: 1000, y: 400 },
        fieldZone: { x: 1000, y: 490 },
      },
    },
    stages: {
      verification: {
        id: "stage_verification",
        name: "Evidence Verification",
        category: "B",
        code: "report.py::extract_and_validate_citations",
        desk: { x: 250, y: 572, w: 160, h: 56 },
        center: { x: 330, y: 600 },
      },
      prioritization: {
        id: "stage_prioritization",
        name: "Signal Prioritization",
        category: "B",
        code: "report.py::parse_signals_from_text",
        desk: { x: 520, y: 572, w: 160, h: 56 },
        center: { x: 600, y: 600 },
      },
      composition: {
        id: "stage_composition",
        name: "Report Composition",
        category: "B",
        code: "report.py::assemble_report",
        desk: { x: 790, y: 572, w: 160, h: 56 },
        center: { x: 870, y: 600 },
      },
    },
  };

  // 2. Initial State Factory
  function createInitialState() {
    return {
      hydrating: false,
      manager: {
        state: "idle",
        objective: "",
        step: 0,
        reason: "",
        totalEvidence: 0,
        phase: "Standing by",
        dispatches: [],
      },
      workers: {
        research_search: { state: "idle", visits: 0, currentQuery: "", currentReason: "", newEvidence: 0, staffed: true, error: null },
        news_search: { state: "idle", visits: 0, currentQuery: "", currentReason: "", newEvidence: 0, staffed: true, error: null },
        web_search: { state: "idle", visits: 0, currentQuery: "", currentReason: "", newEvidence: 0, staffed: true, error: null },
        patent_search: { state: "idle", visits: 0, currentQuery: "", currentReason: "", newEvidence: 0, staffed: true, error: null },
      },
      stages: {
        verification: { active: false },
        prioritization: { active: false },
        composition: { active: false },
      },
      tasks: {},
      announcement: "",
    };
  }

  let state = createInitialState();
  let domNodes = null;
  let activeTransits = new Set();

  // 3. Pure Event Interpreter (BUILD3.md event -> action mapping)
  function interpretEvent(ev) {
    if (!ev || typeof ev !== "object") return [];
    const actions = [];
    const d = ev.data || {};
    const kind = ev.kind;
    const phase = ev.phase;

    if (kind === "objective") {
      actions.push({ type: "MANAGER_RECEIVE", objective: d.objective || ev.text });
      if (Array.isArray(d.available_tools)) {
        actions.push({ type: "STAFF_DESKS", availableTools: d.available_tools });
      }
    } else if (kind === "planning" && phase === "Planning the next step") {
      actions.push({ type: "MANAGER_PLAN", step: d.step || 1 });
    } else if (kind === "planning" && phase === "Identifying knowledge gaps") {
      actions.push({ type: "MANAGER_DELEGATE", nextTool: d.next_tool, reason: d.reason || ev.detail });
    } else if (kind === "tool_selected") {
      const taskId = `${d.tool}#${d.call_index || 1}`;
      actions.push({
        type: "TASK_CREATE",
        id: taskId,
        tool: d.tool,
        query: d.query,
        reason: d.reason,
        callIndex: d.call_index || 1,
      });
      actions.push({
        type: "WORKER_ASSIGN",
        tool: d.tool,
        taskId: taskId,
        query: d.query,
        reason: d.reason,
        callIndex: d.call_index || 1,
      });
    } else if (kind === "tool_result") {
      const count = typeof d.new_evidence === "number" ? d.new_evidence : 0;
      const total = typeof d.total_evidence === "number" ? d.total_evidence : count;
      actions.push({ type: "TASK_RETURN", tool: d.tool, count: count, total: total });
      actions.push({ type: "WORKER_INBOUND", tool: d.tool, count: count, total: total });
    } else if (kind === "note" && phase === "No results for that angle") {
      actions.push({ type: "TASK_EMPTY", tool: d.tool });
      actions.push({ type: "WORKER_EMPTY", tool: d.tool });
    } else if (kind === "note" && phase === "Source unavailable") {
      actions.push({ type: "TASK_FAIL", tool: d.tool, error: d.error || ev.detail });
      actions.push({ type: "WORKER_ERROR", tool: d.tool, error: d.error || ev.detail });
    } else if (kind === "error") {
      actions.push({ type: "MANAGER_ERROR", detail: ev.detail || ev.text });
    } else if (kind === "final" && phase === "Comparing and prioritising evidence") {
      actions.push({ type: "STAGE_ACTIVATE", stage: "verification" });
      actions.push({ type: "STAGE_ACTIVATE", stage: "prioritization", delay: 400 });
      actions.push({ type: "MANAGER_SYNTHESIZE", evidenceCount: d.evidence });
    } else if (kind === "final" && phase === "Generating intelligence report") {
      actions.push({ type: "STAGE_ACTIVATE", stage: "composition" });
      actions.push({ type: "MANAGER_COMPOSE" });
    } else if (kind === "final" && phase === "Completed") {
      actions.push({
        type: "OFFICE_SETTLE",
        toolCalls: d.tool_calls,
        evidence: d.evidence,
        toolsUsed: d.tools_used,
        signals: d.signals,
      });
      actions.push({ type: "MANAGER_COMPLETE" });
    }

    return actions;
  }

  // 4. Reducer (Pure State Transition)
  function reducer(prevState, action) {
    const nextState = JSON.parse(JSON.stringify(prevState));

    switch (action.type) {
      case "MANAGER_RECEIVE":
        nextState.manager.state = "receiving";
        nextState.manager.objective = action.objective || "";
        nextState.manager.phase = "Objective Received";
        nextState.announcement = `Objective assigned: ${action.objective}`;
        break;

      case "STAFF_DESKS":
        if (Array.isArray(action.availableTools)) {
          Object.keys(nextState.workers).forEach((tool) => {
            nextState.workers[tool].staffed = action.availableTools.includes(tool);
          });
        }
        break;

      case "MANAGER_PLAN":
        nextState.manager.state = "planning";
        nextState.manager.step = action.step;
        nextState.manager.phase = `Planning Step ${action.step}`;
        nextState.announcement = `Manager analyzing gathered findings (Step ${action.step})`;
        break;

      case "MANAGER_DELEGATE":
        nextState.manager.state = "delegating";
        nextState.manager.reason = action.reason || "";
        nextState.manager.phase = "Delegating Assignment";
        nextState.announcement = `Knowledge gap identified: ${action.reason || "Dispatching follow-up query"}`;
        break;

      case "TASK_CREATE":
        nextState.tasks[action.id] = {
          id: action.id,
          tool: action.tool,
          query: action.query,
          reason: action.reason,
          state: "dispatched",
        };
        nextState.manager.dispatches.push({
          tool: action.tool,
          query: action.query,
          reason: action.reason,
          callIndex: action.callIndex,
        });
        break;

      case "WORKER_ASSIGN":
        if (nextState.workers[action.tool]) {
          const w = nextState.workers[action.tool];
          w.state = "assigned";
          w.visits = action.callIndex || (w.visits + 1);
          w.currentQuery = action.query || "";
          w.currentReason = action.reason || "";
          w.error = null;
          nextState.manager.state = "awaiting";
          nextState.announcement = `${OFFICE_LAYOUT.workers[action.tool]?.name || action.tool} dispatched for ${action.query || "investigation"}`;
        }
        break;

      case "WORKER_INBOUND":
        if (nextState.workers[action.tool]) {
          const w = nextState.workers[action.tool];
          w.state = "inbound";
          w.newEvidence = action.count;
          if (typeof action.total === "number") nextState.manager.totalEvidence = action.total;
          nextState.announcement = `${OFFICE_LAYOUT.workers[action.tool]?.name || action.tool} gathered ${action.count} evidence sources`;
        }
        break;

      case "WORKER_EMPTY":
        if (nextState.workers[action.tool]) {
          nextState.workers[action.tool].state = "empty";
          nextState.announcement = `${OFFICE_LAYOUT.workers[action.tool]?.name || action.tool} returned 0 results for query`;
        }
        break;

      case "WORKER_ERROR":
        if (nextState.workers[action.tool]) {
          nextState.workers[action.tool].state = "error";
          nextState.workers[action.tool].error = action.error;
          nextState.announcement = `Source unavailable for ${OFFICE_LAYOUT.workers[action.tool]?.name || action.tool}`;
        }
        break;

      case "MANAGER_SYNTHESIZE":
        nextState.manager.state = "synthesizing";
        nextState.manager.phase = "Synthesizing Evidence";
        nextState.announcement = `Synthesizing ${action.evidenceCount || nextState.manager.totalEvidence} verified evidence items`;
        break;

      case "STAGE_ACTIVATE":
        if (nextState.stages[action.stage]) {
          nextState.stages[action.stage].active = true;
        }
        break;

      case "MANAGER_COMPOSE":
        nextState.manager.state = "composing";
        nextState.manager.phase = "Composing Intelligence Brief";
        if (nextState.stages.composition) nextState.stages.composition.active = true;
        break;

      case "MANAGER_COMPLETE":
      case "OFFICE_SETTLE":
        nextState.manager.state = "completed";
        nextState.manager.phase = "Investigation Completed";
        Object.keys(nextState.workers).forEach((t) => {
          if (nextState.workers[t].state !== "error") nextState.workers[t].state = "idle";
        });
        nextState.announcement = "Intelligence brief assembled and verified.";
        break;

      case "MANAGER_ERROR":
        nextState.manager.state = "error";
        nextState.manager.phase = "Investigation Error";
        nextState.announcement = `Investigation error: ${action.detail || ""}`;
        break;

      default:
        break;
    }

    return nextState;
  }

  // 5. DOM Builder (Creates SVG and HTML Shell Once)
  function buildScene(container) {
    container.innerHTML = `
      <section class="office-section" id="office-root" aria-label="Autonomous Intelligence Office Floor Plan">
        <div class="office-header">
          <div class="office-title-group">
            <span class="office-title">Autonomous Intelligence Office</span>
            <span class="office-badge" id="office-status-pill">STANDING BY</span>
          </div>
          <div class="office-legend">
            <span><span class="legend-field-dot"></span> Field Sources (Real APIs)</span>
            <span><span class="legend-stage-dot"></span> Pipeline Stages</span>
          </div>
        </div>

        <div class="office-scene-wrapper">
          <svg class="office-svg" viewBox="0 0 1200 700" role="img" aria-label="Interactive AI office floor plan">
            <defs>
              <!-- Drop shadows -->
              <filter id="soft-shadow" x="-8%" y="-8%" width="120%" height="120%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.06"/>
              </filter>
            </defs>

            <!-- Corridors & Spine -->
            <g class="corridors-layer">
              <!-- Horizontal Spine -->
              <line x1="160" y1="290" x2="1040" y2="290" class="corridor-line" />
              <line x1="160" y1="290" x2="1040" y2="290" class="corridor-guide" />
              <!-- Trunk to Manager -->
              <line x1="600" y1="232" x2="600" y2="290" class="corridor-line" />
              <line x1="600" y1="232" x2="600" y2="290" class="corridor-guide" />
              <!-- Vertical Desk Drop lines -->
              <line x1="200" y1="290" x2="200" y2="370" class="corridor-line" />
              <line x1="450" y1="290" x2="450" y2="370" class="corridor-line" />
              <line x1="750" y1="290" x2="750" y2="370" class="corridor-line" />
              <line x1="1000" y1="290" x2="1000" y2="370" class="corridor-line" />
            </g>

            <!-- Manager Cabin -->
            <g class="manager-cabin desk-group" id="node-manager" data-state="idle" tabindex="0" role="button" aria-label="Manager Cabin: Autonomous Reasoning Loop">
              <rect x="340" y="24" width="520" height="208" rx="10" class="manager-cabin-shell" filter="url(#soft-shadow)" />
              
              <!-- Assignment Plate -->
              <rect x="360" y="40" width="480" height="48" class="assignment-plate" />
              <text x="376" y="56" class="assignment-label">CURRENT OBJECTIVE</text>
              <text x="376" y="74" class="assignment-text" id="svg-manager-obj">Standing by for investigation target…</text>

              <!-- Phase Chip -->
              <rect x="480" y="102" width="240" height="24" class="manager-phase-chip" />
              <text x="600" y="118" class="manager-phase-text" id="svg-manager-phase">STANDING BY</text>

              <!-- Manager Desk & Figure -->
              <rect x="530" y="152" width="140" height="40" class="desk-base" />
              <rect x="575" y="162" width="50" height="10" class="monitor-screen" id="svg-manager-monitor" />
              
              <!-- Manager Figure -->
              <g id="figure-manager" transform="translate(600, 142)">
                <circle cx="0" cy="0" r="16" class="figure-accent-ring" />
                <rect x="-10" y="-6" width="20" height="12" rx="6" class="figure-body" />
                <circle cx="0" cy="-14" r="8" class="figure-head" />
              </g>

              <!-- Evidence Tray -->
              <rect x="710" y="146" width="130" height="52" class="evidence-tray-bg" />
              <text x="775" y="166" class="assignment-label" style="text-anchor: middle;">EVIDENCE TRAY</text>
              <text x="775" y="186" class="tray-count-text" id="svg-manager-tray">0 items</text>
            </g>

            <!-- Category A Field Workers (Desks + Field Zones + Figures) -->
            <g class="field-workers-layer">
              
              <!-- Desk 1: Research -->
              <g class="desk-group" id="node-worker-research_search" data-tool="research_search" data-state="idle" tabindex="0" role="button" aria-label="Research Intelligence Desk">
                <rect x="120" y="372" width="160" height="56" class="desk-base" />
                <text x="200" y="394" class="desk-label">Research Intelligence</text>
                <text x="200" y="412" class="desk-tool-name">research_search</text>
                <rect x="180" y="380" width="40" height="8" class="monitor-screen" />
                <!-- Visit Badge -->
                <rect x="250" y="364" width="26" height="16" class="visit-badge-bg" id="vbadge-bg-research_search" display="none" />
                <text x="263" y="376" class="visit-badge-text" id="vbadge-txt-research_search">×1</text>
                <!-- Field Zone -->
                <rect x="135" y="475" width="130" height="32" class="field-zone-marker" />
                <text x="200" y="495" class="field-zone-label">ARXIV / OPENALEX</text>
                <!-- Moving Figure -->
                <g class="worker-figure" id="fig-research_search" transform="translate(200, 356)">
                  <circle cx="0" cy="0" r="14" class="figure-accent-ring" />
                  <rect x="-8" y="-5" width="16" height="10" rx="5" class="figure-body" />
                  <circle cx="0" cy="-12" r="7" class="figure-head" />
                </g>
              </g>

              <!-- Desk 2: News -->
              <g class="desk-group" id="node-worker-news_search" data-tool="news_search" data-state="idle" tabindex="0" role="button" aria-label="News Intelligence Desk">
                <rect x="370" y="372" width="160" height="56" class="desk-base" />
                <text x="450" y="394" class="desk-label">News Intelligence</text>
                <text x="450" y="412" class="desk-tool-name">news_search</text>
                <rect x="430" y="380" width="40" height="8" class="monitor-screen" />
                <!-- Visit Badge -->
                <rect x="500" y="364" width="26" height="16" class="visit-badge-bg" id="vbadge-bg-news_search" display="none" />
                <text x="513" y="376" class="visit-badge-text" id="vbadge-txt-news_search">×1</text>
                <!-- Field Zone -->
                <rect x="385" y="475" width="130" height="32" class="field-zone-marker" />
                <text x="450" y="495" class="field-zone-label">GOOGLE NEWS RSS</text>
                <!-- Moving Figure -->
                <g class="worker-figure" id="fig-news_search" transform="translate(450, 356)">
                  <circle cx="0" cy="0" r="14" class="figure-accent-ring" />
                  <rect x="-8" y="-5" width="16" height="10" rx="5" class="figure-body" />
                  <circle cx="0" cy="-12" r="7" class="figure-head" />
                </g>
              </g>

              <!-- Desk 3: Web -->
              <g class="desk-group" id="node-worker-web_search" data-tool="web_search" data-state="idle" tabindex="0" role="button" aria-label="Web Intelligence Desk">
                <rect x="670" y="372" width="160" height="56" class="desk-base" />
                <text x="750" y="394" class="desk-label">Web Intelligence</text>
                <text x="750" y="412" class="desk-tool-name">web_search</text>
                <rect x="730" y="380" width="40" height="8" class="monitor-screen" />
                <!-- Visit Badge -->
                <rect x="800" y="364" width="26" height="16" class="visit-badge-bg" id="vbadge-bg-web_search" display="none" />
                <text x="813" y="376" class="visit-badge-text" id="vbadge-txt-web_search">×1</text>
                <!-- Field Zone -->
                <rect x="685" y="475" width="130" height="32" class="field-zone-marker" />
                <text x="750" y="495" class="field-zone-label">DUCKDUCKGO / WIKI</text>
                <!-- Moving Figure -->
                <g class="worker-figure" id="fig-web_search" transform="translate(750, 356)">
                  <circle cx="0" cy="0" r="14" class="figure-accent-ring" />
                  <rect x="-8" y="-5" width="16" height="10" rx="5" class="figure-body" />
                  <circle cx="0" cy="-12" r="7" class="figure-head" />
                </g>
              </g>

              <!-- Desk 4: Patents -->
              <g class="desk-group" id="node-worker-patent_search" data-tool="patent_search" data-state="idle" tabindex="0" role="button" aria-label="Patent Intelligence Desk">
                <rect x="920" y="372" width="160" height="56" class="desk-base" />
                <text x="1000" y="394" class="desk-label">Patent Intelligence</text>
                <text x="1000" y="412" class="desk-tool-name">patent_search</text>
                <rect x="980" y="380" width="40" height="8" class="monitor-screen" />
                <!-- Visit Badge -->
                <rect x="1050" y="364" width="26" height="16" class="visit-badge-bg" id="vbadge-bg-patent_search" display="none" />
                <text x="1063" y="376" class="visit-badge-text" id="vbadge-txt-patent_search">×1</text>
                <!-- Field Zone -->
                <rect x="935" y="475" width="130" height="32" class="field-zone-marker" />
                <text x="1000" y="495" class="field-zone-label">GOOGLE PATENTS</text>
                <!-- Moving Figure -->
                <g class="worker-figure" id="fig-patent_search" transform="translate(1000, 356)">
                  <circle cx="0" cy="0" r="14" class="figure-accent-ring" />
                  <rect x="-8" y="-5" width="16" height="10" rx="5" class="figure-body" />
                  <circle cx="0" cy="-12" r="7" class="figure-head" />
                </g>
              </g>

            </g>

            <!-- Category B Back Office Stages (Dashed, Post-Loop Report Pipeline) -->
            <g class="back-office-layer">
              
              <!-- Stage 5: Verification -->
              <g class="desk-group stage-desk" id="node-stage-verification" data-stage="verification" tabindex="0" role="button" aria-label="Evidence Verification Pipeline Stage">
                <rect x="250" y="572" width="160" height="56" class="desk-base" />
                <text x="330" y="594" class="desk-label">Evidence Verification</text>
                <text x="330" y="612" class="desk-tool-name">citation_validator</text>
                <rect x="360" y="560" width="42" height="16" class="stage-badge-bg" />
                <text x="381" y="572" class="stage-badge-text">STAGE</text>
              </g>

              <!-- Stage 6: Prioritization -->
              <g class="desk-group stage-desk" id="node-stage-prioritization" data-stage="prioritization" tabindex="0" role="button" aria-label="Signal Prioritization Pipeline Stage">
                <rect x="520" y="572" width="160" height="56" class="desk-base" />
                <text x="600" y="594" class="desk-label">Signal Prioritization</text>
                <text x="600" y="612" class="desk-tool-name">tier_categorizer</text>
                <rect x="630" y="560" width="42" height="16" class="stage-badge-bg" />
                <text x="651" y="572" class="stage-badge-text">STAGE</text>
              </g>

              <!-- Stage 7: Composition -->
              <g class="desk-group stage-desk" id="node-stage-composition" data-stage="composition" tabindex="0" role="button" aria-label="Report Composition Pipeline Stage">
                <rect x="790" y="572" width="160" height="56" class="desk-base" />
                <text x="870" y="594" class="desk-label">Report Composition</text>
                <text x="870" y="612" class="desk-tool-name">report_assembler</text>
                <rect x="900" y="560" width="42" height="16" class="stage-badge-bg" />
                <text x="921" y="572" class="stage-badge-text">STAGE</text>
              </g>

            </g>
          </svg>

          <!-- Responsive Office Roster for screens < 768px -->
          <ul class="office-roster-list" id="office-roster"></ul>
        </div>

        <!-- Accessible Live Announcer -->
        <div class="sr-only" aria-live="polite" id="office-live-announcer"></div>

        <!-- Interactive Drawer -->
        <div class="office-drawer" id="office-drawer" aria-hidden="true">
          <div class="drawer-header">
            <div class="drawer-title" id="drawer-title">Entity Detail</div>
            <button type="button" class="drawer-close-btn" id="btn-close-drawer" aria-label="Close detail drawer">&times;</button>
          </div>
          <div class="drawer-body" id="drawer-content"></div>
        </div>
      </section>
    `;

    domNodes = {
      root: document.getElementById("office-root"),
      statusPill: document.getElementById("office-status-pill"),
      manager: document.getElementById("node-manager"),
      managerObj: document.getElementById("svg-manager-obj"),
      managerPhase: document.getElementById("svg-manager-phase"),
      managerTray: document.getElementById("svg-manager-tray"),
      drawer: document.getElementById("office-drawer"),
      drawerTitle: document.getElementById("drawer-title"),
      drawerContent: document.getElementById("drawer-content"),
      drawerClose: document.getElementById("btn-close-drawer"),
      announcer: document.getElementById("office-live-announcer"),
      roster: document.getElementById("office-roster"),
    };

    wireDrawerEvents();
  }

  // 6. Polyline Travel Engine (rAF interpolated, halts on idle)
  function travel(figureEl, polyline, durationMs, onComplete) {
    if (!figureEl || !Array.isArray(polyline) || polyline.length < 2) {
      if (typeof onComplete === "function") onComplete();
      return;
    }

    // Check reduced motion preference
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const endPoint = polyline[polyline.length - 1];
      figureEl.setAttribute("transform", `translate(${endPoint.x}, ${endPoint.y})`);
      if (typeof onComplete === "function") onComplete();
      return;
    }

    // Calculate segment lengths
    const segLengths = [];
    let totalLen = 0;
    for (let i = 0; i < polyline.length - 1; i++) {
      const dx = polyline[i + 1].x - polyline[i].x;
      const dy = polyline[i + 1].y - polyline[i].y;
      const len = Math.hypot(dx, dy);
      segLengths.push(len);
      totalLen += len;
    }

    const startTime = performance.now();
    const transitId = Symbol();
    activeTransits.add(transitId);

    function frame(now) {
      const elapsed = now - startTime;
      const rawP = Math.min(1, elapsed / durationMs);
      // Easing: cubic-bezier(.4,0,.2,1) approximate easeInOut
      const t = rawP < 0.5 ? 2 * rawP * rawP : 1 - Math.pow(-2 * rawP + 2, 2) / 2;

      const targetDist = t * totalLen;
      let currDist = 0;
      let curPoint = polyline[0];

      for (let i = 0; i < segLengths.length; i++) {
        if (currDist + segLengths[i] >= targetDist || i === segLengths.length - 1) {
          const segT = segLengths[i] > 0 ? (targetDist - currDist) / segLengths[i] : 1;
          curPoint = {
            x: polyline[i].x + (polyline[i + 1].x - polyline[i].x) * segT,
            y: polyline[i].y + (polyline[i + 1].y - polyline[i].y) * segT,
          };
          break;
        }
        currDist += segLengths[i];
      }

      figureEl.setAttribute("transform", `translate(${curPoint.x.toFixed(1)}, ${curPoint.y.toFixed(1)})`);

      if (rawP < 1) {
        requestAnimationFrame(frame);
      } else {
        activeTransits.delete(transitId);
        if (typeof onComplete === "function") onComplete();
      }
    }

    requestAnimationFrame(frame);
  }

  // 7. Render Office (Sets data-state attributes & text nodes)
  function renderOffice(st) {
    if (!domNodes) return;

    // Manager
    const m = st.manager;
    domNodes.manager.setAttribute("data-state", m.state);
    domNodes.managerObj.textContent = m.objective ? (m.objective.length > 52 ? m.objective.slice(0, 50) + "…" : m.objective) : "Standing by for target…";
    domNodes.managerPhase.textContent = m.phase.toUpperCase();
    domNodes.managerTray.textContent = `${m.totalEvidence} item${m.totalEvidence === 1 ? "" : "s"}`;
    domNodes.statusPill.textContent = m.phase.toUpperCase();

    // Field Workers
    Object.entries(st.workers).forEach(([tool, w]) => {
      const node = document.getElementById(`node-worker-${tool}`);
      const fig = document.getElementById(`fig-${tool}`);
      const vbg = document.getElementById(`vbadge-bg-${tool}`);
      const vtxt = document.getElementById(`vbadge-txt-${tool}`);

      if (node) {
        node.setAttribute("data-state", w.state);
        node.classList.toggle("is-unstaffed", !w.staffed);
      }

      if (vbg && vtxt) {
        if (w.visits > 1) {
          vbg.setAttribute("display", "inline");
          vtxt.textContent = `×${w.visits}`;
        } else {
          vbg.setAttribute("display", "none");
        }
      }

      // Handle transit motions if triggered
      if (fig && !st.hydrating) {
        const layout = OFFICE_LAYOUT.workers[tool];
        if (layout) {
          if (w.state === "assigned") {
            // Outbound dispatch: desk -> field zone
            travel(fig, [
              { x: layout.center.x, y: layout.center.y - 44 },
              { x: layout.center.x, y: layout.fieldZone.y - 12 },
            ], 600, () => {
              w.state = "working";
              if (node) node.setAttribute("data-state", "working");
            });
          } else if (w.state === "inbound") {
            // Inbound return: field zone -> corridor -> manager cabin -> desk
            travel(fig, [
              { x: layout.center.x, y: layout.fieldZone.y - 12 },
              { x: layout.center.x, y: OFFICE_LAYOUT.corridor.spineY },
              { x: OFFICE_LAYOUT.corridor.trunkX, y: OFFICE_LAYOUT.corridor.spineY },
              { x: OFFICE_LAYOUT.corridor.trunkX, y: 245 },
            ], 750, () => {
              // Settle at desk
              travel(fig, [
                { x: OFFICE_LAYOUT.corridor.trunkX, y: OFFICE_LAYOUT.corridor.spineY },
                { x: layout.center.x, y: OFFICE_LAYOUT.corridor.spineY },
                { x: layout.center.x, y: layout.center.y - 44 },
              ], 500);
            });
          }
        }
      }
    });

    // Pipeline Stages
    Object.entries(st.stages).forEach(([stageKey, s]) => {
      const node = document.getElementById(`node-stage-${stageKey}`);
      if (node) {
        node.setAttribute("data-state", s.active ? "active" : "idle");
      }
    });

    // Accessibility Live Announcer
    if (st.announcement && domNodes.announcer) {
      domNodes.announcer.textContent = st.announcement;
    }

    // Responsive Roster List Update
    renderRoster(st);
  }

  function renderRoster(st) {
    if (!domNodes || !domNodes.roster) return;
    domNodes.roster.innerHTML = "";

    // Manager row
    const mRow = document.createElement("li");
    mRow.className = "roster-row";
    mRow.innerHTML = `
      <span><strong>Manager:</strong> ${st.manager.objective ? st.manager.objective.slice(0, 30) + '…' : 'Idle'}</span>
      <span class="mono office-badge">${st.manager.phase}</span>
    `;
    domNodes.roster.appendChild(mRow);

    // Worker rows
    Object.entries(st.workers).forEach(([tool, w]) => {
      const info = OFFICE_LAYOUT.workers[tool];
      const row = document.createElement("li");
      row.className = "roster-row";
      row.innerHTML = `
        <span><strong>${info?.name || tool}:</strong> ${w.visits > 0 ? `Called ×${w.visits}` : 'Standby'}</span>
        <span class="mono">${w.state.toUpperCase()}</span>
      `;
      domNodes.roster.appendChild(row);
    });
  }

  // 8. Interactive Drawers (Progressive Disclosure)
  function wireDrawerEvents() {
    if (!domNodes) return;

    domNodes.drawerClose.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeDrawer();
    });

    // Manager Click
    domNodes.manager.addEventListener("click", openManagerDrawer);
    domNodes.manager.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openManagerDrawer(); }
    });

    // Category A Worker Clicks
    Object.keys(OFFICE_LAYOUT.workers).forEach((tool) => {
      const el = document.getElementById(`node-worker-${tool}`);
      if (el) {
        el.addEventListener("click", () => openWorkerDrawer(tool));
        el.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openWorkerDrawer(tool); }
        });
      }
    });

    // Category B Stage Clicks
    Object.keys(OFFICE_LAYOUT.stages).forEach((stageKey) => {
      const el = document.getElementById(`node-stage-${stageKey}`);
      if (el) {
        el.addEventListener("click", () => openStageDrawer(stageKey));
        el.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openStageDrawer(stageKey); }
        });
      }
    });
  }

  function openDrawer(title, htmlContent) {
    if (!domNodes || !domNodes.drawer) return;
    domNodes.drawerTitle.textContent = title;
    domNodes.drawerContent.innerHTML = htmlContent;
    domNodes.drawer.classList.add("is-open");
    domNodes.drawer.setAttribute("aria-hidden", "false");
  }

  function closeDrawer() {
    if (!domNodes || !domNodes.drawer) return;
    domNodes.drawer.classList.remove("is-open");
    domNodes.drawer.setAttribute("aria-hidden", "true");
  }

  function openManagerDrawer() {
    const m = state.manager;
    let dispatchesHtml = "";
    if (m.dispatches.length) {
      dispatchesHtml = `
        <div class="drawer-meta-item">
          <div class="drawer-meta-label">DISPATCH HISTORY (${m.dispatches.length})</div>
          <ul class="drawer-list">
            ${m.dispatches.map((d, i) => `
              <li class="drawer-list-item">
                <strong>#${i + 1} ${d.tool}</strong>
                <div><em>Query:</em> ${d.query || "—"}</div>
                ${d.reason ? `<div><em>Reason:</em> ${d.reason}</div>` : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      `;
    }

    const html = `
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">CURRENT OBJECTIVE</div>
        <div class="drawer-meta-val">${m.objective || "No active objective"}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">REASONING STATUS</div>
        <div class="drawer-meta-val">${m.phase}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">ACCUMULATED EVIDENCE</div>
        <div class="drawer-meta-val">${m.totalEvidence} verified items in tray</div>
      </div>
      ${dispatchesHtml}
    `;
    openDrawer("Manager Reasoning Dossier", html);
  }

  function openWorkerDrawer(tool) {
    const w = state.workers[tool];
    const info = OFFICE_LAYOUT.workers[tool];
    if (!info) return;

    let dispatchesHtml = "";
    const relevantDispatches = state.manager.dispatches.filter((d) => d.tool === tool);
    if (relevantDispatches.length) {
      dispatchesHtml = `
        <div class="drawer-meta-item">
          <div class="drawer-meta-label">TOOL INVOCATIONS (${relevantDispatches.length})</div>
          <ul class="drawer-list">
            ${relevantDispatches.map((d, i) => `
              <li class="drawer-list-item">
                <div><strong>Dispatch #${i + 1}:</strong> "${d.query || ""}"</div>
                ${d.reason ? `<div><small>${d.reason}</small></div>` : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      `;
    }

    const html = `
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">TOOL PROVIDER</div>
        <div class="drawer-meta-val"><code>${tool}</code></div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">CURRENT STATE</div>
        <div class="drawer-meta-val">${w ? w.state.toUpperCase() : "IDLE"}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">TOTAL VISITS</div>
        <div class="drawer-meta-val">${w ? w.visits : 0} times dispatched</div>
      </div>
      ${w && w.error ? `
        <div class="drawer-meta-item">
          <div class="drawer-meta-label" style="color:var(--danger)">LAST ERROR</div>
          <div class="drawer-meta-val" style="color:var(--danger)">${w.error}</div>
        </div>
      ` : ""}
      ${dispatchesHtml}
    `;
    openDrawer(`${info.name} Details`, html);
  }

  function openStageDrawer(stageKey) {
    const info = OFFICE_LAYOUT.stages[stageKey];
    if (!info) return;

    const descriptions = {
      verification: "Validates all citation markers [E1] against real evidence items, scrubs unresolvable IDs, and removes any hallucinated model URLs.",
      prioritization: "Extracts strategic signals into HIGH, IMPORTANT, and EMERGING tiers based on evidence weight and model analysis.",
      composition: "Assembles adaptive deep-dive sections, strategic next actions, honest limitations, and final source coverage.",
    };

    const html = `
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">PIPELINE STAGE</div>
        <div class="drawer-meta-val"><code>${info.code}</code></div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">FUNCTION</div>
        <div class="drawer-meta-val">${descriptions[stageKey] || "Post-loop pipeline stage."}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">NATURE</div>
        <div class="drawer-meta-val">Back-office stage (part of report assembly, not an autonomous agent).</div>
      </div>
    `;
    openDrawer(`${info.name} (Pipeline Stage)`, html);
  }

  // 9. Public API exposed on window.Office
  window.Office = {
    mount: function (containerEl) {
      buildScene(containerEl);
      renderOffice(state);
    },

    handleEvent: function (ev) {
      try {
        const actions = interpretEvent(ev);
        actions.forEach((act) => {
          state = reducer(state, act);
        });
        renderOffice(state);
      } catch (err) {
        console.error("Office.handleEvent error caught safely:", err);
      }
    },

    hydrate: function (eventsArray) {
      if (!Array.isArray(eventsArray)) return;
      state = createInitialState();
      state.hydrating = true;

      eventsArray.forEach((ev) => {
        const actions = interpretEvent(ev);
        actions.forEach((act) => {
          state = reducer(state, act);
        });
      });

      state.hydrating = false;
      renderOffice(state);
    },

    reset: function () {
      state = createInitialState();
      activeTransits.clear();
      closeDrawer();
      renderOffice(state);
    },

    getState: function () {
      return state;
    },
  };
})();
