/* ==========================================================================
   AGENTX24 — The Intelligence Studio (web/office.js)
   Living intelligence workspace driven strictly by real SSE telemetry.
   Spatial composition: Central Analysis Table + Specialist Workstations + Synthesis Bench.
   Layering: interpretEvent (pure) -> reducer (pure) -> renderStudio (DOM/CSS)
   ========================================================================== */

(function () {
  "use strict";

  // 1. Spatial Geometry & Station Positions
  const STUDIO_LAYOUT = {
    manager: {
      center: { x: 550, y: 270 },
      card: { x: 340, y: 190, w: 420, h: 160 },
      objectivePlate: { x: 360, y: 205, w: 380, h: 48 },
      stateChip: { x: 440, y: 265, w: 220, h: 24 },
      evidenceTray: { x: 600, y: 300, w: 140, h: 38 },
    },
    specialists: {
      research_search: {
        id: "research",
        name: "Research Intelligence",
        tool: "research_search",
        provider: "OPENALEX · ARXIV",
        center: { x: 250, y: 95 },
        card: { x: 160, y: 40, w: 180, h: 110 },
        packetPath: [
          { x: 480, y: 210 },
          { x: 380, y: 160 },
          { x: 250, y: 130 },
        ],
      },
      news_search: {
        id: "news",
        name: "News Intelligence",
        tool: "news_search",
        provider: "GOOGLE NEWS RSS",
        center: { x: 850, y: 95 },
        card: { x: 760, y: 40, w: 180, h: 110 },
        packetPath: [
          { x: 620, y: 210 },
          { x: 720, y: 160 },
          { x: 850, y: 130 },
        ],
      },
      web_search: {
        id: "web",
        name: "Web Intelligence",
        tool: "web_search",
        provider: "DUCKDUCKGO · WIKI",
        center: { x: 170, y: 350 },
        card: { x: 80, y: 295, w: 180, h: 110 },
        packetPath: [
          { x: 360, y: 270 },
          { x: 270, y: 310 },
          { x: 170, y: 350 },
        ],
      },
      patent_search: {
        id: "patent",
        name: "Patent Intelligence",
        tool: "patent_search",
        provider: "GOOGLE PATENTS",
        center: { x: 930, y: 350 },
        card: { x: 840, y: 295, w: 180, h: 110 },
        packetPath: [
          { x: 740, y: 270 },
          { x: 830, y: 310 },
          { x: 930, y: 350 },
        ],
      },
    },
    stages: {
      verification: {
        id: "stage_verification",
        name: "Evidence Verification",
        code: "report.py::extract_and_validate_citations",
        card: { x: 340, y: 500, w: 130, h: 65 },
      },
      prioritization: {
        id: "stage_prioritization",
        name: "Signal Prioritization",
        code: "report.py::parse_signals_from_text",
        card: { x: 485, y: 500, w: 130, h: 65 },
      },
      composition: {
        id: "stage_composition",
        name: "Dossier Composition",
        code: "report.py::assemble_report",
        card: { x: 630, y: 500, w: 130, h: 65 },
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
      specialists: {
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

  // 3. Pure Event Interpreter (SSE Telemetry -> Studio Action)
  function interpretEvent(ev) {
    if (!ev || typeof ev !== "object") return [];
    const actions = [];
    const d = ev.data || {};
    const kind = ev.kind;
    const phase = ev.phase;

    if (kind === "objective") {
      actions.push({ type: "MANAGER_RECEIVE", objective: d.objective || ev.text });
      if (Array.isArray(d.available_tools)) {
        actions.push({ type: "STAFF_STATIONS", availableTools: d.available_tools });
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
        type: "SPECIALIST_ASSIGN",
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
      actions.push({ type: "SPECIALIST_INBOUND", tool: d.tool, count: count, total: total });
    } else if (kind === "note" && phase === "No results for that angle") {
      actions.push({ type: "TASK_EMPTY", tool: d.tool });
      actions.push({ type: "SPECIALIST_EMPTY", tool: d.tool });
    } else if (kind === "note" && phase === "Source unavailable") {
      actions.push({ type: "TASK_FAIL", tool: d.tool, error: d.error || ev.detail });
      actions.push({ type: "SPECIALIST_ERROR", tool: d.tool, error: d.error || ev.detail });
    } else if (kind === "error") {
      actions.push({ type: "MANAGER_ERROR", detail: ev.detail || ev.text });
    } else if (kind === "final" && phase === "Comparing and prioritising evidence") {
      actions.push({ type: "STAGE_ACTIVATE", stage: "verification" });
      actions.push({ type: "STAGE_ACTIVATE", stage: "prioritization" });
      actions.push({ type: "MANAGER_SYNTHESIZE", evidenceCount: d.evidence });
    } else if (kind === "final" && phase === "Generating intelligence report") {
      actions.push({ type: "STAGE_ACTIVATE", stage: "composition" });
      actions.push({ type: "MANAGER_COMPOSE" });
    } else if (kind === "final" && phase === "Completed") {
      actions.push({
        type: "STUDIO_SETTLE",
        toolCalls: d.tool_calls,
        evidence: d.evidence,
        toolsUsed: d.tools_used,
        signals: d.signals,
      });
      actions.push({ type: "MANAGER_COMPLETE" });
    }

    return actions;
  }

  // 4. Pure Reducer
  function reducer(prevState, action) {
    const nextState = JSON.parse(JSON.stringify(prevState));

    switch (action.type) {
      case "MANAGER_RECEIVE":
        nextState.manager.state = "receiving";
        nextState.manager.objective = action.objective || "";
        nextState.manager.phase = "Objective Received";
        nextState.announcement = `Objective assigned: ${action.objective}`;
        break;

      case "STAFF_STATIONS":
        if (Array.isArray(action.availableTools)) {
          Object.keys(nextState.specialists).forEach((tool) => {
            nextState.specialists[tool].staffed = action.availableTools.includes(tool);
          });
        }
        break;

      case "MANAGER_PLAN":
        nextState.manager.state = "planning";
        nextState.manager.step = action.step;
        nextState.manager.phase = `Reviewing Findings (Step ${action.step})`;
        nextState.announcement = `Manager analyzing gathered evidence (Step ${action.step})`;
        break;

      case "MANAGER_DELEGATE":
        nextState.manager.state = "delegating";
        nextState.manager.reason = action.reason || "";
        nextState.manager.phase = "Delegating Follow-Up";
        nextState.announcement = `Knowledge gap identified: ${action.reason || "Dispatching specialist inquiry"}`;
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

      case "SPECIALIST_ASSIGN":
        if (nextState.specialists[action.tool]) {
          const s = nextState.specialists[action.tool];
          s.state = "assigned";
          s.visits = action.callIndex || (s.visits + 1);
          s.currentQuery = action.query || "";
          s.currentReason = action.reason || "";
          s.error = null;
          nextState.manager.state = "awaiting";
          nextState.announcement = `${STUDIO_LAYOUT.specialists[action.tool]?.name || action.tool} dispatched for ${action.query || "investigation"}`;
        }
        break;

      case "SPECIALIST_INBOUND":
        if (nextState.specialists[action.tool]) {
          const s = nextState.specialists[action.tool];
          s.state = "inbound";
          s.newEvidence = action.count;
          if (typeof action.total === "number") nextState.manager.totalEvidence = action.total;
          nextState.announcement = `${STUDIO_LAYOUT.specialists[action.tool]?.name || action.tool} returned ${action.count} evidence items`;
        }
        break;

      case "SPECIALIST_EMPTY":
        if (nextState.specialists[action.tool]) {
          nextState.specialists[action.tool].state = "empty";
          nextState.announcement = `${STUDIO_LAYOUT.specialists[action.tool]?.name || action.tool} found 0 matching records`;
        }
        break;

      case "SPECIALIST_ERROR":
        if (nextState.specialists[action.tool]) {
          nextState.specialists[action.tool].state = "error";
          nextState.specialists[action.tool].error = action.error;
          nextState.announcement = `Source unavailable for ${STUDIO_LAYOUT.specialists[action.tool]?.name || action.tool}`;
        }
        break;

      case "MANAGER_SYNTHESIZE":
        nextState.manager.state = "synthesizing";
        nextState.manager.phase = "Synthesizing Dossier";
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
      case "STUDIO_SETTLE":
        nextState.manager.state = "completed";
        nextState.manager.phase = "Investigation Complete";
        Object.keys(nextState.specialists).forEach((t) => {
          if (nextState.specialists[t].state !== "error") nextState.specialists[t].state = "idle";
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

  // 5. SVG DOM Builder
  function buildScene(container) {
    container.innerHTML = `
      <section class="office-section" id="studio-root" aria-label="The Intelligence Studio Workspace">
        <div class="studio-header">
          <div class="studio-header-left">
            <span class="studio-title">The Intelligence Studio</span>
            <span class="studio-badge" id="studio-status-pill">STANDING BY</span>
          </div>
          <div class="studio-legend">
            <span class="legend-item"><span class="legend-dot-specialist"></span> Real Specialist Stations</span>
            <span class="legend-item"><span class="legend-dot-stage"></span> Post-Loop Synthesis Bench</span>
          </div>
        </div>

        <div class="studio-scene-wrapper">
          <svg class="studio-svg" viewBox="0 0 1100 640" role="img" aria-label="Spatial Intelligence Studio Canvas">
            <defs>
              <filter id="studio-card-shadow" x="-8%" y="-8%" width="120%" height="120%">
                <feDropShadow dx="0" dy="2" stdDeviation="4" flood-opacity="0.05"/>
              </filter>
            </defs>

            <!-- Subtle Flow Trajectories connecting Manager to Specialists -->
            <g class="studio-trajectories-layer">
              <!-- Research Path -->
              <path d="M 480 210 Q 380 150 250 130" class="studio-flow-path" id="flow-research_search" />
              <!-- News Path -->
              <path d="M 620 210 Q 720 150 850 130" class="studio-flow-path" id="flow-news_search" />
              <!-- Web Path -->
              <path d="M 360 270 Q 270 310 170 350" class="studio-flow-path" id="flow-web_search" />
              <!-- Patent Path -->
              <path d="M 740 270 Q 830 310 930 350" class="studio-flow-path" id="flow-patent_search" />
              <!-- Bench Drop Trunk -->
              <line x1="550" y1="350" x2="550" y2="470" class="studio-grid-line" />
            </g>

            <!-- Specialist Workstation 1: Research Intelligence (Top West) -->
            <g class="specialist-group" id="node-specialist-research_search" data-tool="research_search" data-state="idle" tabindex="0" role="button" aria-label="Research Intelligence Workstation">
              <rect x="160" y="40" width="180" height="110" class="specialist-card" />
              <!-- Document Sheet Motif -->
              <rect x="175" y="55" width="40" height="24" class="specialist-sheet-item" />
              <rect x="180" y="60" width="40" height="24" class="specialist-sheet-item" />
              <text x="230" y="68" class="specialist-title">Research</text>
              <text x="230" y="82" class="specialist-meta">OpenAlex · arXiv</text>
              <!-- State Tag -->
              <rect x="175" y="112" width="70" height="18" class="specialist-status-tag-bg" />
              <text x="210" y="124" class="specialist-status-tag-text" id="tag-txt-research_search">STANDBY</text>
              <!-- Visit Pill -->
              <rect x="295" y="48" width="28" height="16" class="counter-pill-bg" id="vpill-bg-research_search" display="none" />
              <text x="309" y="60" class="counter-pill-text" id="vpill-txt-research_search">×1</text>
            </g>

            <!-- Specialist Workstation 2: News Intelligence (Top East) -->
            <g class="specialist-group" id="node-specialist-news_search" data-tool="news_search" data-state="idle" tabindex="0" role="button" aria-label="News Intelligence Workstation">
              <rect x="760" y="40" width="180" height="110" class="specialist-card" />
              <!-- News Strip Motif -->
              <rect x="775" y="55" width="42" height="12" class="specialist-sheet-item" />
              <rect x="775" y="70" width="36" height="12" class="specialist-sheet-item" />
              <text x="830" y="68" class="specialist-title">News Intelligence</text>
              <text x="830" y="82" class="specialist-meta">Google News RSS</text>
              <!-- State Tag -->
              <rect x="775" y="112" width="70" height="18" class="specialist-status-tag-bg" />
              <text x="810" y="124" class="specialist-status-tag-text" id="tag-txt-news_search">STANDBY</text>
              <!-- Visit Pill -->
              <rect x="895" y="48" width="28" height="16" class="counter-pill-bg" id="vpill-bg-news_search" display="none" />
              <text x="909" y="60" class="counter-pill-text" id="vpill-txt-news_search">×1</text>
            </g>

            <!-- Specialist Workstation 3: Web Intelligence (Mid West) -->
            <g class="specialist-group" id="node-specialist-web_search" data-tool="web_search" data-state="idle" tabindex="0" role="button" aria-label="Web Intelligence Workstation">
              <rect x="80" y="295" width="180" height="110" class="specialist-card" />
              <!-- Web Window Motif -->
              <rect x="95" y="310" width="44" height="26" class="specialist-sheet-item" />
              <text x="150" y="323" class="specialist-title">Web Intelligence</text>
              <text x="150" y="337" class="specialist-meta">DDGS · Wikipedia</text>
              <!-- State Tag -->
              <rect x="95" y="367" width="70" height="18" class="specialist-status-tag-bg" />
              <text x="130" y="379" class="specialist-status-tag-text" id="tag-txt-web_search">STANDBY</text>
              <!-- Visit Pill -->
              <rect x="215" y="303" width="28" height="16" class="counter-pill-bg" id="vpill-bg-web_search" display="none" />
              <text x="229" y="315" class="counter-pill-text" id="vpill-txt-web_search">×1</text>
            </g>

            <!-- Specialist Workstation 4: Patent Intelligence (Mid East) -->
            <g class="specialist-group" id="node-specialist-patent_search" data-tool="patent_search" data-state="idle" tabindex="0" role="button" aria-label="Patent Intelligence Workstation">
              <rect x="840" y="295" width="180" height="110" class="specialist-card" />
              <!-- Patent Blueprint Motif -->
              <rect x="855" y="310" width="44" height="26" class="specialist-sheet-item" />
              <text x="910" y="323" class="specialist-title">Patent Intelligence</text>
              <text x="910" y="337" class="specialist-meta">Google Patents</text>
              <!-- State Tag -->
              <rect x="855" y="367" width="70" height="18" class="specialist-status-tag-bg" />
              <text x="890" y="379" class="specialist-status-tag-text" id="tag-txt-patent_search">STANDBY</text>
              <!-- Visit Pill -->
              <rect x="975" y="303" width="28" height="16" class="counter-pill-bg" id="vpill-bg-patent_search" display="none" />
              <text x="989" y="315" class="counter-pill-text" id="vpill-txt-patent_search">×1</text>
            </g>

            <!-- Central Analysis Table (Manager Coordination Surface) -->
            <g class="command-table-group" id="node-manager-table" tabindex="0" role="button" aria-label="Central Analysis Table: Autonomous AI Reasoning Loop">
              <rect x="340" y="190" width="420" height="160" class="command-table-card" />
              
              <!-- Objective Docket Sheet -->
              <rect x="360" y="205" width="380" height="46" class="objective-docket" />
              <text x="375" y="221" class="docket-label">ACTIVE INVESTIGATION TARGET</text>
              <text x="375" y="238" class="docket-objective-text" id="svg-manager-obj">Standing by for investigation target…</text>

              <!-- State Badge -->
              <rect x="440" y="262" width="220" height="24" class="manager-state-chip-bg" />
              <text x="550" y="278" class="manager-state-chip-text" id="svg-manager-phase">READY FOR TARGET</text>

              <!-- Evidence Tray -->
              <rect x="580" y="298" width="160" height="38" class="manager-evidence-tray-bg" />
              <text x="660" y="312" class="docket-label" style="text-anchor: middle;">EVIDENCE TRAY</text>
              <text x="660" y="327" class="tray-count-label" id="svg-manager-tray">0 items</text>
            </g>

            <!-- Post-Loop Synthesis Bench (Category B Code Stages) -->
            <g class="synthesis-bench-layer">
              <rect x="320" y="470" width="460" height="115" class="bench-card" />
              <text x="336" y="490" class="docket-label">POST-LOOP SYNTHESIS BENCH (REPORT PIPELINE STAGES)</text>
              
              <!-- Stage 1: Verification -->
              <g class="stage-group" id="node-stage-verification" data-stage="verification" tabindex="0" role="button" aria-label="Evidence Verification Stage">
                <rect x="340" y="502" width="130" height="65" class="stage-card-box" id="sbox-verification" />
                <text x="405" y="526" class="stage-name">Verification</text>
                <rect x="382" y="538" width="46" height="14" class="stage-pill-bg" />
                <text x="405" y="549" class="stage-pill-text">STAGE</text>
              </g>

              <!-- Stage 2: Prioritization -->
              <g class="stage-group" id="node-stage-prioritization" data-stage="prioritization" tabindex="0" role="button" aria-label="Signal Prioritization Stage">
                <rect x="485" y="502" width="130" height="65" class="stage-card-box" id="sbox-prioritization" />
                <text x="550" y="526" class="stage-name">Prioritization</text>
                <rect x="527" y="538" width="46" height="14" class="stage-pill-bg" />
                <text x="550" y="549" class="stage-pill-text">STAGE</text>
              </g>

              <!-- Stage 3: Composition -->
              <g class="stage-group" id="node-stage-composition" data-stage="composition" tabindex="0" role="button" aria-label="Dossier Composition Stage">
                <rect x="630" y="502" width="130" height="65" class="stage-card-box" id="sbox-composition" />
                <text x="695" y="526" class="stage-name">Composition</text>
                <rect x="672" y="538" width="46" height="14" class="stage-pill-bg" />
                <text x="695" y="549" class="stage-pill-text">STAGE</text>
              </g>
            </g>

            <!-- Dynamic Information Packets Layer -->
            <g class="packets-layer" id="packets-host"></g>
          </svg>

          <!-- Responsive Studio Roster for mobile < 768px -->
          <ul class="studio-roster-list" id="studio-roster"></ul>
        </div>

        <!-- Accessible Live Announcer -->
        <div class="sr-only" aria-live="polite" id="studio-live-announcer"></div>

        <!-- Slide-Out Details Drawer -->
        <div class="studio-drawer" id="studio-drawer" aria-hidden="true">
          <div class="drawer-header">
            <div class="drawer-title" id="drawer-title">Station Dossier</div>
            <button type="button" class="drawer-close-btn" id="btn-close-drawer" aria-label="Close station dossier">&times;</button>
          </div>
          <div class="drawer-body" id="drawer-content"></div>
        </div>
      </section>
    `;

    domNodes = {
      root: document.getElementById("studio-root"),
      statusPill: document.getElementById("studio-status-pill"),
      managerTable: document.getElementById("node-manager-table"),
      managerObj: document.getElementById("svg-manager-obj"),
      managerPhase: document.getElementById("svg-manager-phase"),
      managerTray: document.getElementById("svg-manager-tray"),
      packetsHost: document.getElementById("packets-host"),
      drawer: document.getElementById("studio-drawer"),
      drawerTitle: document.getElementById("drawer-title"),
      drawerContent: document.getElementById("drawer-content"),
      drawerClose: document.getElementById("btn-close-drawer"),
      announcer: document.getElementById("studio-live-announcer"),
      roster: document.getElementById("studio-roster"),
    };

    wireDrawerEvents();
  }

  // 6. Tactile Information Packet Animation Engine
  function dispatchInformationPacket(tool, queryText, isReturn, evidenceCount) {
    if (!domNodes || !domNodes.packetsHost) return;
    const layout = STUDIO_LAYOUT.specialists[tool];
    if (!layout || !layout.packetPath) return;

    // Check reduced motion preference
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    const pathPoints = isReturn ? layout.packetPath.slice().reverse() : layout.packetPath.slice();
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "packet-card-group");

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", "-35");
    rect.setAttribute("y", "-14");
    rect.setAttribute("width", "70");
    rect.setAttribute("height", "28");
    rect.setAttribute("class", "packet-card");

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", "0");
    text.setAttribute("y", "3");
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("class", "packet-title");
    text.textContent = isReturn ? `+${evidenceCount || 1} items` : (tool.split("_")[0] || "tool").toUpperCase();

    g.appendChild(rect);
    g.appendChild(text);
    domNodes.packetsHost.appendChild(g);

    // Light up flow path
    const flowPath = document.getElementById(`flow-${tool}`);
    if (flowPath) flowPath.classList.add("active");

    const durationMs = 650;
    const startTime = performance.now();
    const transitId = Symbol();
    activeTransits.add(transitId);

    function frame(now) {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / durationMs);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

      // Interpolate along path
      const p1 = pathPoints[0];
      const p2 = pathPoints[pathPoints.length - 1];
      const cx = p1.x + (p2.x - p1.x) * ease;
      const cy = p1.y + (p2.y - p1.y) * ease;

      g.setAttribute("transform", `translate(${cx.toFixed(1)}, ${cy.toFixed(1)})`);

      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        activeTransits.delete(transitId);
        if (flowPath) flowPath.classList.remove("active");
        if (g.parentNode) g.parentNode.removeChild(g);
      }
    }

    requestAnimationFrame(frame);
  }

  // 7. Render Studio State (Sets data-state attributes & text)
  function renderStudio(st) {
    if (!domNodes) return;

    // Manager Surface
    const m = st.manager;
    domNodes.managerObj.textContent = m.objective ? (m.objective.length > 48 ? m.objective.slice(0, 46) + "…" : m.objective) : "Standing by for target…";
    domNodes.managerPhase.textContent = m.phase.toUpperCase();
    domNodes.managerTray.textContent = `${m.totalEvidence} item${m.totalEvidence === 1 ? "" : "s"}`;
    domNodes.statusPill.textContent = m.phase.toUpperCase();

    // Specialist Workstations
    Object.entries(st.specialists).forEach(([tool, s]) => {
      const node = document.getElementById(`node-specialist-${tool}`);
      const tagTxt = document.getElementById(`tag-txt-${tool}`);
      const vbg = document.getElementById(`vpill-bg-${tool}`);
      const vtxt = document.getElementById(`vpill-txt-${tool}`);

      if (node) {
        node.setAttribute("data-state", s.state);
        node.classList.toggle("is-unstaffed", !s.staffed);
      }

      if (tagTxt) {
        if (s.state === "assigned") tagTxt.textContent = "ASSIGNED";
        else if (s.state === "working") tagTxt.textContent = "INVESTIGATING";
        else if (s.state === "inbound") tagTxt.textContent = "RETURNING";
        else if (s.state === "empty") tagTxt.textContent = "0 RECORDS";
        else if (s.state === "error") tagTxt.textContent = "UNAVAILABLE";
        else tagTxt.textContent = s.visits > 0 ? "COMPLETED" : "STANDBY";
      }

      if (vbg && vtxt) {
        if (s.visits > 1) {
          vbg.setAttribute("display", "inline");
          vtxt.textContent = `×${s.visits}`;
        } else {
          vbg.setAttribute("display", "none");
        }
      }

      // Trigger packet animation on new events
      if (s.state === "assigned" && !st.hydrating) {
        dispatchInformationPacket(tool, s.currentQuery, false);
        s.state = "working";
      } else if (s.state === "inbound" && !st.hydrating) {
        dispatchInformationPacket(tool, s.currentQuery, true, s.newEvidence);
      }
    });

    // Synthesis Bench Stages
    Object.entries(st.stages).forEach(([stageKey, sg]) => {
      const sbox = document.getElementById(`sbox-${stageKey}`);
      if (sbox) {
        sbox.classList.toggle("active", Boolean(sg.active));
      }
    });

    // Live Announcer
    if (st.announcement && domNodes.announcer) {
      domNodes.announcer.textContent = st.announcement;
    }

    // Responsive Roster List
    renderRoster(st);
  }

  function renderRoster(st) {
    if (!domNodes || !domNodes.roster) return;
    domNodes.roster.innerHTML = "";

    // Manager row
    const mRow = document.createElement("li");
    mRow.className = "roster-row";
    mRow.innerHTML = `
      <span><strong>Analysis Lead:</strong> ${st.manager.objective ? st.manager.objective.slice(0, 32) + '…' : 'Standing by'}</span>
      <span class="mono studio-badge">${st.manager.phase}</span>
    `;
    domNodes.roster.appendChild(mRow);

    // Specialist rows
    Object.entries(st.specialists).forEach(([tool, s]) => {
      const info = STUDIO_LAYOUT.specialists[tool];
      const row = document.createElement("li");
      row.className = "roster-row";
      row.innerHTML = `
        <span><strong>${info?.name || tool}:</strong> ${s.visits > 0 ? `Invoked ×${s.visits}` : 'Standby'}</span>
        <span class="mono">${s.state.toUpperCase()}</span>
      `;
      domNodes.roster.appendChild(row);
    });
  }

  // 8. Slide-Out Dossier Drawer (Progressive Disclosure)
  function wireDrawerEvents() {
    if (!domNodes) return;

    domNodes.drawerClose.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeDrawer();
    });

    // Manager Table Click
    domNodes.managerTable.addEventListener("click", openManagerDrawer);
    domNodes.managerTable.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openManagerDrawer(); }
    });

    // Specialist Clicks
    Object.keys(STUDIO_LAYOUT.specialists).forEach((tool) => {
      const el = document.getElementById(`node-specialist-${tool}`);
      if (el) {
        el.addEventListener("click", () => openSpecialistDrawer(tool));
        el.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openSpecialistDrawer(tool); }
        });
      }
    });

    // Synthesis Bench Stage Clicks
    Object.keys(STUDIO_LAYOUT.stages).forEach((stageKey) => {
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
          <div class="drawer-meta-label">INVESTIGATION DISPATCH TRAIL (${m.dispatches.length})</div>
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
        <div class="drawer-meta-label">CENTRAL OBJECTIVE</div>
        <div class="drawer-meta-val">${m.objective || "No active objective"}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">REASONING STATUS</div>
        <div class="drawer-meta-val">${m.phase}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">COLLECTED EVIDENCE POOL</div>
        <div class="drawer-meta-val">${m.totalEvidence} verified items in tray</div>
      </div>
      ${dispatchesHtml}
    `;
    openDrawer("Analysis Lead Dossier", html);
  }

  function openSpecialistDrawer(tool) {
    const s = state.specialists[tool];
    const info = STUDIO_LAYOUT.specialists[tool];
    if (!info) return;

    let dispatchesHtml = "";
    const relevantDispatches = state.manager.dispatches.filter((d) => d.tool === tool);
    if (relevantDispatches.length) {
      dispatchesHtml = `
        <div class="drawer-meta-item">
          <div class="drawer-meta-label">DISPATCH HISTORY (${relevantDispatches.length})</div>
          <ul class="drawer-list">
            ${relevantDispatches.map((d, i) => `
              <li class="drawer-list-item">
                <div><strong>Query #${i + 1}:</strong> "${d.query || ""}"</div>
                ${d.reason ? `<div><small>${d.reason}</small></div>` : ""}
              </li>
            `).join("")}
          </ul>
        </div>
      `;
    }

    const html = `
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">SPECIALIST WORKSTATION</div>
        <div class="drawer-meta-val"><code>${tool}</code></div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">INTEGRATED PROVIDERS</div>
        <div class="drawer-meta-val">${info.provider}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">TOTAL DISPATCHES</div>
        <div class="drawer-meta-val">${s ? s.visits : 0} invocations</div>
      </div>
      ${s && s.error ? `
        <div class="drawer-meta-item">
          <div class="drawer-meta-label" style="color:var(--danger)">LAST ERROR</div>
          <div class="drawer-meta-val" style="color:var(--danger)">${s.error}</div>
        </div>
      ` : ""}
      ${dispatchesHtml}
    `;
    openDrawer(`${info.name} Details`, html);
  }

  function openStageDrawer(stageKey) {
    const info = STUDIO_LAYOUT.stages[stageKey];
    if (!info) return;

    const descriptions = {
      verification: "Validates all citation markers [E1] against real evidence items, scrubs unresolvable IDs, and removes any hallucinated model URLs.",
      prioritization: "Extracts strategic signals into HIGH, IMPORTANT, and EMERGING tiers based on evidence weight and model analysis.",
      composition: "Assembles adaptive deep-dive sections, strategic next actions, honest limitations, and final source coverage.",
    };

    const html = `
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">SYNTHESIS BENCH STAGE</div>
        <div class="drawer-meta-val"><code>${info.code}</code></div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">FUNCTION</div>
        <div class="drawer-meta-val">${descriptions[stageKey] || "Post-loop pipeline stage."}</div>
      </div>
      <div class="drawer-meta-item">
        <div class="drawer-meta-label">NATURE</div>
        <div class="drawer-meta-val">Report synthesis stage (not an autonomous agent).</div>
      </div>
    `;
    openDrawer(`${info.name} (Pipeline Stage)`, html);
  }

  // 9. Public API exposed on window.Office
  window.Office = {
    mount: function (containerEl) {
      buildScene(containerEl);
      renderStudio(state);
    },

    handleEvent: function (ev) {
      try {
        const actions = interpretEvent(ev);
        actions.forEach((act) => {
          state = reducer(state, act);
        });
        renderStudio(state);
      } catch (err) {
        console.error("Studio.handleEvent error caught safely:", err);
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
      renderStudio(state);
    },

    reset: function () {
      state = createInitialState();
      activeTransits.clear();
      closeDrawer();
      renderStudio(state);
    },

    getState: function () {
      return state;
    },
  };
})();
