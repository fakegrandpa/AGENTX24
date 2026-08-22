import re
from typing import Any
from urllib.parse import urlparse

from app.models import Evidence, Report, ReportSections, Signal


def compute_corroboration(evidence_list: list[Evidence]) -> None:
    """Computes corroboration count for each evidence item based on shared domain or title keywords."""
    domains: dict[str, int] = {}
    for ev in evidence_list:
        if ev.url:
            try:
                host = urlparse(ev.url).netloc.lower()
                if host:
                    domains[host] = domains.get(host, 0) + 1
            except Exception:
                pass

    for ev in evidence_list:
        score = 0
        if ev.url:
            try:
                host = urlparse(ev.url).netloc.lower()
                if host and domains.get(host, 0) > 1:
                    score += domains[host] - 1
            except Exception:
                pass
        ev.corroboration = score


def extract_and_validate_citations(
    text: str,
    valid_ids: set[str],
    limitations: list[str],
) -> tuple[str, list[str]]:
    """Extracts all [En] citations, validates them against valid_ids, and strips unresolvable ones."""
    found_citations: list[str] = []
    
    def replace_citation(match: re.Match[str]) -> str:
        cid = match.group(1).upper()
        if cid in valid_ids:
            if cid not in found_citations:
                found_citations.append(cid)
            return f"[{cid}]"
        else:
            limitations.append(f"Stripped unverified citation marker [{cid}] (not in verified evidence)")
            return ""

    cleaned_text = re.sub(r"\[(E\d+)\]", replace_citation, text, flags=re.IGNORECASE)
    # Clean up double spaces or dangling punctuation from removed citations
    cleaned_text = re.sub(r"\s{2,}", " ", cleaned_text)
    return cleaned_text, found_citations


def parse_signals_from_text(
    text: str,
    valid_ids: set[str],
    limitations: list[str],
) -> list[Signal]:
    """Parses prioritized signal blocks from LLM synthesis text."""
    signals: list[Signal] = []

    tier_patterns = [
        ("high", r"(?:###\s*|\*\*|#+\s*)HIGH PRIORITY(?:\s*SIGNALS)?[:\*#\s]*\n(.*?)(?=(?:###\s*|\*\*|#+\s*)(?:HIGH PRIORITY|IMPORTANT|EMERGING|KEY RESEARCH|COMPETITOR|RECENT|PATENT|WHY THIS MATTERS|RECOMMENDED)|\Z)"),
        ("important", r"(?:###\s*|\*\*|#+\s*)IMPORTANT(?:\s*SIGNALS)?[:\*#\s]*\n(.*?)(?=(?:###\s*|\*\*|#+\s*)(?:HIGH PRIORITY|IMPORTANT|EMERGING|KEY RESEARCH|COMPETITOR|RECENT|PATENT|WHY THIS MATTERS|RECOMMENDED)|\Z)"),
        ("emerging", r"(?:###\s*|\*\*|#+\s*)EMERGING(?:\s*(?:/|AND)?\s*WATCH)?(?:\s*SIGNALS)?[:\*#\s]*\n(.*?)(?=(?:###\s*|\*\*|#+\s*)(?:HIGH PRIORITY|IMPORTANT|EMERGING|KEY RESEARCH|COMPETITOR|RECENT|PATENT|WHY THIS MATTERS|RECOMMENDED)|\Z)"),
    ]

    for tier_name, pattern in tier_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        tier_content = match.group(1).strip()
        
        # Split by bullet points or numbered items
        lines = [l.strip() for l in re.split(r"\n+(?:[-*•]|\d+\.)\s+", tier_content) if l.strip()]
        for line in lines:
            if len(line) < 10 or line.lower().startswith("signals"):
                continue
            cleaned_line, cits = extract_and_validate_citations(line, valid_ids, limitations)
            if not cleaned_line:
                continue

            # Split headline and detail
            parts = re.split(r":\s+|\s+–\s+|\s+-\s+", cleaned_line, maxsplit=1)
            raw_h = parts[0].replace("**", "").replace("#", "").strip()
            headline = re.sub(r"^[-*•\d\.\s]+", "", raw_h).strip() or raw_h
            detail = parts[1].strip() if len(parts) > 1 else cleaned_line
            detail = re.sub(r"^[-*•\d\.\s]+", "", detail).strip() or detail

            if len(headline) > 120:
                headline = headline[:117] + "..."

            # Only include signal if it has genuine content
            signals.append(Signal(
                tier=tier_name,  # type: ignore
                headline=headline,
                detail=detail,
                citations=cits,
            ))

    return signals


def parse_section_content(
    section_name: str,
    text: str,
    valid_ids: set[str],
    limitations: list[str],
) -> str | None:
    """Extracts a named section from the LLM response text."""
    pattern = rf"(?:###\s*|\*\*|#+\s*){re.escape(section_name)}[:\*#\s]*\n(.*?)(?=(?:###\s*|\*\*|#+\s*)[A-Z]|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    content = match.group(1).strip()
    if not content or len(content) < 15:
        return None
    cleaned, _ = extract_and_validate_citations(content, valid_ids, limitations)
    return cleaned if cleaned.strip() else None


def assemble_report(
    target: str,
    raw_synthesis_text: str,
    evidence_list: list[Evidence],
    tool_calls: list[dict[str, Any]],
    runtime_limitations: list[str],
    has_patents: bool = False,
) -> Report:
    """Assembles a prioritized, adaptive Report model with strict evidence integrity."""
    limitations = list(runtime_limitations)
    valid_ids = {ev.id for ev in evidence_list}

    # 1. Compute corroboration facts
    compute_corroboration(evidence_list)

    # 2. Extract summary
    summary = ""
    summary_match = re.search(
        r"(?:###\s*|\*\*|#+\s*)?(?:INVESTIGATION SUMMARY|EXECUTIVE SUMMARY)[:\*#\s]*\n(.*?)(?=(?:###\s*|\*\*|#+\s*)[A-Z]|\Z)",
        raw_synthesis_text,
        re.IGNORECASE | re.DOTALL,
    )
    if summary_match and summary_match.group(1).strip():
        cleaned_sum, _ = extract_and_validate_citations(summary_match.group(1).strip(), valid_ids, limitations)
        summary = cleaned_sum
    else:
        # Fallback: take first 2 paragraphs
        paragraphs = [p.strip() for p in raw_synthesis_text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        if paragraphs:
            cleaned_p, _ = extract_and_validate_citations(paragraphs[0], valid_ids, limitations)
            summary = cleaned_p
        else:
            summary = f"Autonomous investigation of '{target}' completed with {len(evidence_list)} evidence sources gathered."

    # 3. Extract Prioritized Signals
    signals = parse_signals_from_text(raw_synthesis_text, valid_ids, limitations)
    
    # If no structured signals matched, generate fallback signals from top evidence
    if not signals and evidence_list:
        for ev in evidence_list[:3]:
            signals.append(Signal(
                tier="high" if ev.provider_kind == "research" else "important",
                headline=ev.title[:90],
                detail=f"{ev.snippet} [{ev.id}]",
                citations=[ev.id],
            ))

    # 4. Extract Adaptive Sections (None if no evidence or unpopulated)
    has_research_evidence = any(e.provider_kind == "research" for e in evidence_list)
    has_news_evidence = any(e.provider_kind == "news" for e in evidence_list)
    has_patent_evidence = any(e.provider_kind == "patent" for e in evidence_list)

    research_sec = parse_section_content("KEY RESEARCH DEVELOPMENTS", raw_synthesis_text, valid_ids, limitations)
    if not research_sec and has_research_evidence:
        research_sec = parse_section_content("RESEARCH DEVELOPMENTS", raw_synthesis_text, valid_ids, limitations)

    competitor_sec = parse_section_content("COMPETITOR / INDUSTRY ACTIVITY", raw_synthesis_text, valid_ids, limitations)
    if not competitor_sec:
        competitor_sec = parse_section_content("COMPETITOR ACTIVITY", raw_synthesis_text, valid_ids, limitations)

    recent_sec = parse_section_content("RECENT DEVELOPMENTS", raw_synthesis_text, valid_ids, limitations)
    if not recent_sec and has_news_evidence:
        recent_sec = parse_section_content("LATEST NEWS", raw_synthesis_text, valid_ids, limitations)

    patents_sec = None
    if has_patents and has_patent_evidence:
        patents_sec = parse_section_content("PATENT SIGNALS", raw_synthesis_text, valid_ids, limitations)

    why_matters = parse_section_content("WHY THIS MATTERS", raw_synthesis_text, valid_ids, limitations)
    if not why_matters:
        why_matters = parse_section_content("STRATEGIC IMPLICATIONS", raw_synthesis_text, valid_ids, limitations)

    sections = ReportSections(
        research=research_sec,
        competitor_industry=competitor_sec,
        recent_developments=recent_sec,
        patents=patents_sec,
        why_it_matters=why_matters,
    )

    # 5. Extract Next Actions
    next_actions: list[str] = []
    actions_match = re.search(
        r"(?:###\s*|\*\*|#\s*)?(?:RECOMMENDED NEXT ACTIONS|NEXT ACTIONS)[:\s]*\n(.*?)(?=(?:###\s*|\*\*|#\s*[A-Z]|\Z))",
        raw_synthesis_text,
        re.IGNORECASE | re.DOTALL,
    )
    if actions_match:
        raw_actions = [a.strip() for a in re.split(r"\n+(?:[-*•]|\d+\.)\s+", actions_match.group(1).strip()) if a.strip()]
        for act in raw_actions:
            cleaned_act, _ = extract_and_validate_citations(act, valid_ids, limitations)
            if cleaned_act and len(cleaned_act) > 10:
                next_actions.append(cleaned_act)

    if not next_actions:
        next_actions = [
            f"Track upcoming announcements and patent filings for {target}",
            f"Deep-dive into verified scientific literature regarding key technical capabilities",
        ]

    # 6. Build Coverage summary
    coverage: list[str] = []
    tool_counts: dict[str, int] = {}
    for ev in evidence_list:
        tool_counts[ev.tool] = tool_counts.get(ev.tool, 0) + 1

    for tool_name, count in tool_counts.items():
        coverage.append(f"{tool_name}: {count} verified sources gathered")

    if not has_patents:
        limitations.append("Patent search was unconfigured (EPO OPS credentials not provided)")

    return Report(
        target=target,
        summary=summary,
        signals=signals,
        sections=sections,
        next_actions=next_actions,
        coverage=coverage,
        limitations=list(dict.fromkeys(limitations)),  # Deduplicate
    )
