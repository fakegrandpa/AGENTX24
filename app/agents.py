from __future__ import annotations
from typing import Any
import logging
from app.llm import LLMResponse, propose_next_step
from app.models import Critique, Evidence

logger = logging.getLogger(__name__)

# Agent Roster: Defining the specialized roles and responsibilities in AGENTX24
AGENT_ROSTER: dict[str, dict[str, Any]] = {
    "investigator": {
        "id": "investigator",
        "name": "Lead Investigator",
        "responsibility": "Understand the objective and dynamically gather evidence from external sources.",
        "tools": ["news_search", "research_search", "web_search", "patent_search"],
        "category": "agent",
    },
    "critic": {
        "id": "critic",
        "name": "Evidence Critic",
        "responsibility": "Judge whether gathered evidence sufficiently answers the objective and name specific missing gaps.",
        "tools": ["submit_review"],
        "category": "agent",
    },
    "synthesist": {
        "id": "synthesist",
        "name": "Report Synthesist",
        "responsibility": "Compose the prioritized, cited intelligence report from verified evidence only.",
        "tools": [],
        "category": "agent",
    },
}

CRITIC_INSTRUCTION = """You are the Evidence Critic agent in the AGENTX24 autonomous intelligence system.
Your SOLE responsibility is to evaluate whether the evidence gathered so far sufficiently answers the user's investigation objective, or if critical knowledge gaps remain.

OPERATING PRINCIPLES:
1. NO GATHERING TOOLS: You have NO external search tools. You evaluate existing evidence only.
2. FUNCTION CALLING: You MUST call the `submit_review` function exactly once with your evaluation verdict.
3. CONCRETE GAPS: If the evidence is insufficient (`sufficient: false`), specify 1 to 3 concrete, actionable knowledge gaps. Avoid vague critiques like "more info needed". Name exact missing technical, competitor, or news angles.
4. ACTIONABLE RECOMMENDATIONS: If insufficient, recommend the best tool (`recommended_tool`) and search query (`recommended_query`) to close the most critical gap.
5. SUFFICIENCY STANDARD: If the evidence already covers the key aspects of the objective with solid facts and dates, mark `sufficient: true`. It is expected and normal to accept completion when core questions are answered.
6. NO FABRICATION: Never invent evidence IDs [E...] or URLs.
"""

SYNTHESIST_INSTRUCTION = """You are the Report Synthesist agent in the AGENTX24 autonomous intelligence system.
Your SOLE responsibility is to compose a structured, prioritized, cited intelligence report based STRICTLY on the gathered and verified evidence.

STRUCTURE REQUIREMENT — YOU MUST USE THESE EXACT HEADINGS IN YOUR OUTPUT:

# INVESTIGATION SUMMARY
Provide a clear, objective executive synthesis (2-3 paragraphs) answering the target inquiry using verified facts.

# HIGH PRIORITY SIGNALS
- Critical breakthroughs, major competitor shifts, or decisive developments.
Format each item as: * **Headline:** Explanation with exact citations [E1], [E2].

# IMPORTANT DEVELOPMENTS
- Notable technical milestones, incremental research, partnerships, or product updates.
Format each item as: * **Headline:** Explanation with citations [E1].

# EMERGING / WATCH SIGNALS
- Early-stage signals, nascent research trends, or monitoring items.
Format each item as: * **Headline:** Explanation with citations [E1].

# KEY RESEARCH DEVELOPMENTS
Detailed analysis of academic preprints, scientific methodology, or technical architectures found in research evidence.

# COMPETITOR / INDUSTRY ACTIVITY
Analysis of market positioning, commercial moves, product launches, or competitor strategies.

# RECENT DEVELOPMENTS
Chronological breakdown of recent news, announcements, and events.

# WHY THIS MATTERS
Strategic impact, operational implications, and risk assessment for stakeholders.

# RECOMMENDED NEXT ACTIONS
Concrete, actionable steps for follow-up investigation or decision-making. Format as numbered or bulleted list.

OPERATING PRINCIPLES:
1. EVIDENCE INTEGRITY: Every factual claim must be backed by an evidence ID in brackets: [E1], [E2], etc.
2. NO MODEL-AUTHORED URLS: Never write http:// or https:// URLs in your text. Source links are handled by the evidence system.
3. HONEST LIMITATIONS: If a specific angle had no evidence gathered, explicitly note it under that section. Never fabricate findings.
4. NO UNVERIFIED CITATIONS: Only cite evidence IDs that exist in the evidence record provided.
"""

SUBMIT_REVIEW_SCHEMA: dict[str, Any] = {
    "name": "submit_review",
    "description": "Submit a structured review evaluating whether the gathered evidence sufficiently answers the investigation objective.",
    "parameters": {
        "type": "object",
        "properties": {
            "sufficient": {
                "type": "boolean",
                "description": "True if the gathered evidence sufficiently covers the core aspects of the objective, False if critical knowledge gaps remain.",
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific, concrete missing pieces of information needed to complete the investigation.",
            },
            "recommended_tool": {
                "type": "string",
                "description": "Specific tool recommendation to fill the primary gap: 'research_search', 'news_search', 'web_search', or 'patent_search'.",
            },
            "recommended_query": {
                "type": "string",
                "description": "Recommended search query for the follow-up investigation step.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0.0 and 1.0 in this sufficiency evaluation.",
            },
            "note": {
                "type": "string",
                "description": "Brief summary explanation of the review verdict.",
            },
        },
        "required": ["sufficient"],
    },
}


def build_evidence_digest(evidence: list[Evidence], tool_calls: list[dict[str, Any]]) -> str:
    """Builds a compact digest of evidence items and tool queries for the Critic.
    DELIBERATELY EXCLUDES URLs to prevent any model URL leakage.
    """
    lines: list[str] = ["=== GATHERED EVIDENCE DIGEST ==="]
    if not evidence:
        lines.append("(No evidence gathered yet)")
    else:
        for ev in evidence:
            date_str = f" ({ev.published})" if ev.published else ""
            lines.append(f"[{ev.id}] [{ev.tool}] [{ev.source}]{date_str}: {ev.title}")
            if ev.snippet:
                lines.append(f"    Snippet: {ev.snippet[:200]}")

    lines.append("\n=== EXECUTED TOOL CALLS ===")
    if not tool_calls:
        lines.append("(No tool calls executed yet)")
    else:
        for i, tc in enumerate(tool_calls, start=1):
            name = tc.get("name", "unknown")
            query = tc.get("args", {}).get("query", "")
            reason = tc.get("reason", "")
            reason_str = f" | Reason: {reason}" if reason else ""
            lines.append(f"{i}. {name}(\"{query}\"){reason_str}")

    return "\n".join(lines)


def critique_evidence(
    objective: str,
    evidence: list[Evidence],
    tool_calls: list[dict[str, Any]],
    seq: int = 1,
) -> Critique:
    """Invokes the Evidence Critic agent to evaluate evidence sufficiency.
    Fails open to Critique(sufficient=True, note='...') on any error to ensure
    critic issues never block the investigation report.
    """
    try:
        digest = build_evidence_digest(evidence, tool_calls)
        prompt = (
            f"Investigation Objective: \"{objective}\"\n\n"
            f"{digest}\n\n"
            "Evaluate whether this evidence pool sufficiently answers the objective. "
            "Call `submit_review` with your evaluation."
        )

        response: LLMResponse = propose_next_step(
            contents=[prompt],
            tools_schema=[SUBMIT_REVIEW_SCHEMA],
            system_instruction=CRITIC_INSTRUCTION,
        )

        if response.tool_calls:
            call = response.tool_calls[0]
            if call.name == "submit_review":
                args = call.args or {}
                sufficient = bool(args.get("sufficient", True))
                gaps = [str(g) for g in args.get("gaps", []) if g]
                recommended_tool = args.get("recommended_tool")
                recommended_query = args.get("recommended_query")
                confidence = float(args["confidence"]) if "confidence" in args and args["confidence"] is not None else None
                note = str(args.get("note", "")) if args.get("note") else None

                return Critique(
                    seq=seq,
                    sufficient=sufficient,
                    gaps=gaps,
                    recommended_tool=recommended_tool,
                    recommended_query=recommended_query,
                    confidence=confidence,
                    note=note,
                )

        # Fallback if model answered in text without tool call
        logger.warning("Critic did not invoke submit_review; failing open.")
        return Critique(
            seq=seq,
            sufficient=True,
            note="Critic returned textual assessment without function call; accepted as sufficient.",
        )

    except Exception as e:
        logger.warning("Critic execution failed: %s; failing open.", e)
        return Critique(
            seq=seq,
            sufficient=True,
            note=f"Critic unavailable: {e}",
        )
