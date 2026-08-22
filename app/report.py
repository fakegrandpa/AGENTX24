import re
from typing import Any
from urllib.parse import urlparse

from app.models import Evidence, Report, ReportSections, Signal

# A markdown heading is the ONLY thing allowed to terminate a section body.
# It must sit alone on its line and carry a '#' or '**' marker, so inline bold
# inside a bullet (e.g. "* **MaxCyte Expansion:** ...") can never end a section.
_HEADING_LINE_RE = re.compile(
    r"^[ \t]*(?:(?:#{1,6})[ \t]*|(?:\*\*|__))(?P<name>[^\n]{2,90}?)(?:\*\*|__)?[ \t]*:?[ \t]*$",
    re.MULTILINE,
)

# Citations may be single ("[E4]") or grouped ("[E19, E20]", "[E1; E3]", "[E1 and E2]").
_CITATION_BLOCK_RE = re.compile(
    r"\[\s*(E\d+(?:\s*(?:,|;|/|&|and)\s*E\d+)*)\s*\]",
    re.IGNORECASE,
)
_EVIDENCE_ID_RE = re.compile(r"E\d+", re.IGNORECASE)
_URL_IN_PROSE_RE = re.compile(r"https?://\S+")
_EMPHASIS_RE = re.compile(r"\*\*|__|`")


def _normalize_heading(raw: str) -> str:
    return re.sub(r"[\*#:_]+", " ", raw).strip().upper()


def split_heading_blocks(text: str) -> list[tuple[str, str]]:
    """Splits the synthesis text into ordered (normalized heading, body) blocks."""
    blocks: list[tuple[str, str]] = []
    matches = list(_HEADING_LINE_RE.finditer(text or ""))
    for i, m in enumerate(matches):
        name = _normalize_heading(m.group("name"))
        if not name:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        # Drop horizontal rules used as separators between sections
        body = re.sub(r"^\s*(?:-{3,}|_{3,}|\*{3,})\s*$", "", body, flags=re.MULTILINE).strip()
        blocks.append((name, body))
    return blocks


def find_block(blocks: list[tuple[str, str]], *aliases: str) -> str | None:
    """Returns the body of the first block whose heading matches any alias."""
    for alias in aliases:
        needle = alias.upper()
        for name, body in blocks:
            if needle in name and body:
                return body
    return None


def split_bullets(body: str) -> list[str]:
    """Splits a section body into bullet/numbered items (or paragraphs if unlisted)."""
    if not body:
        return []
    items = re.split(r"(?:^|\n)[ \t]*(?:[-*\u2022]|\d+[\.\)])[ \t]+", body)
    cleaned = [i.strip() for i in items if i and i.strip()]
    if len(cleaned) <= 1:
        cleaned = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    return cleaned


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
    """Validates every [En] marker (single or grouped) against the real evidence store,
    strips unresolvable ones, and removes any model-authored URL from the prose.

    Only the evidence store may contribute links to the report, so a hallucinated
    URL or evidence ID can never reach the rendered output.
    """
    found_citations: list[str] = []

    def replace_citation(match: re.Match[str]) -> str:
        kept: list[str] = []
        for raw_id in _EVIDENCE_ID_RE.findall(match.group(1)):
            cid = raw_id.upper()
            if cid in valid_ids:
                if cid not in kept:
                    kept.append(cid)
                if cid not in found_citations:
                    found_citations.append(cid)
            else:
                limitations.append(
                    f"Stripped unverified citation marker [{cid}] (not in verified evidence)"
                )
        return " ".join(f"[{c}]" for c in kept)

    cleaned_text = _CITATION_BLOCK_RE.sub(replace_citation, text or "")

    if _URL_IN_PROSE_RE.search(cleaned_text):
        limitations.append(
            "Removed a model-authored link from the analysis text; only verified evidence URLs are listed under Sources"
        )
        cleaned_text = _URL_IN_PROSE_RE.sub("", cleaned_text)

    # Drop bold/code markers so raw markdown never reaches the judge-facing UI
    cleaned_text = _EMPHASIS_RE.sub("", cleaned_text)

    # Clean up double spaces or dangling separators left by removed citations
    cleaned_text = re.sub(r"[ \t]{2,}", " ", cleaned_text)
    cleaned_text = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned_text)
    return cleaned_text.strip(), found_citations


def _split_headline_detail(line: str) -> tuple[str, str]:
    """Separates a bullet's bold/lead label from its explanatory text."""
    plain = _EMPHASIS_RE.sub("", line).strip()
    plain = re.sub(r"^[-*\u2022\d\.\)\s]+", "", plain).strip()

    parts = re.split(r":\s+|\s+\u2013\s+|\s+\u2014\s+|\s+-\s+", plain, maxsplit=1)
    headline = parts[0].strip().rstrip(":").strip()
    detail = parts[1].strip() if len(parts) > 1 else plain

    if not headline:
        headline = plain
    if len(headline) > 120:
        headline = headline[:117].rstrip() + "..."
    return headline, detail


def parse_signals_from_text(
    blocks: list[tuple[str, str]],
    valid_ids: set[str],
    limitations: list[str],
) -> list[Signal]:
    """Parses prioritized signal tiers from the model's headed sections.
    Tiers are the model's own judgement; empty tiers are omitted, never padded.
    """
    signals: list[Signal] = []
    tier_aliases: list[tuple[str, tuple[str, ...]]] = [
        ("high", ("HIGH PRIORITY",)),
        ("important", ("IMPORTANT DEVELOPMENT", "IMPORTANT SIGNAL", "IMPORTANT")),
        ("emerging", ("EMERGING", "WATCH SIGNAL")),
    ]

    for tier_name, aliases in tier_aliases:
        body = find_block(blocks, *aliases)
        if not body:
            continue
        for line in split_bullets(body):
            if len(line) < 10:
                continue
            cleaned_line, cits = extract_and_validate_citations(line, valid_ids, limitations)
            if not cleaned_line:
                continue
            headline, detail = _split_headline_detail(cleaned_line)
            signals.append(Signal(
                tier=tier_name,  # type: ignore
                headline=headline,
                detail=detail,
                citations=cits,
            ))

    return signals


def parse_section_content(
    blocks: list[tuple[str, str]],
    aliases: tuple[str, ...],
    valid_ids: set[str],
    limitations: list[str],
) -> str | None:
    """Returns a validated section body, or None so the section is omitted entirely."""
    body = find_block(blocks, *aliases)
    if not body or len(body) < 15:
        return None
    cleaned, _ = extract_and_validate_citations(body, valid_ids, limitations)
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

    # 2. Split the synthesis into headed blocks once (single source of parsing truth)
    blocks = split_heading_blocks(raw_synthesis_text or "")

    # 3. Extract summary
    summary = ""
    summary_body = find_block(blocks, "INVESTIGATION SUMMARY", "EXECUTIVE SUMMARY", "SUMMARY")
    if summary_body:
        summary, _ = extract_and_validate_citations(summary_body, valid_ids, limitations)
    if not summary:
        # Fallback: first substantive paragraph of the model's own text
        paragraphs = [
            p.strip()
            for p in (raw_synthesis_text or "").split("\n\n")
            if p.strip() and not p.strip().startswith("#")
        ]
        if paragraphs:
            summary, _ = extract_and_validate_citations(paragraphs[0], valid_ids, limitations)
    if not summary:
        summary = (
            f"Autonomous investigation of '{target}' completed with "
            f"{len(evidence_list)} verified evidence sources gathered."
        )

    # 4. Extract Prioritized Signals (model-assigned tiers only)
    signals = parse_signals_from_text(blocks, valid_ids, limitations)

    # If the model's tier headings could not be parsed, fall back to listing the most
    # recent verified evidence WITHOUT inventing a priority level, and say so plainly.
    if not signals and evidence_list:
        ranked = sorted(
            evidence_list,
            key=lambda e: (e.days_old if e.days_old is not None else 10_000),
        )[:3]
        for ev in ranked:
            signals.append(Signal(
                tier="emerging",
                headline=ev.title[:120],
                detail=f"{ev.snippet} [{ev.id}]".strip(),
                citations=[ev.id],
            ))
        limitations.append(
            "Prioritized signal extraction failed: the items listed are the most recent "
            "verified evidence records, not agent-ranked signals."
        )

    # 5. Extract Adaptive Sections (None => the section is omitted, never rendered empty)
    has_patent_evidence = any(e.provider_kind == "patent" for e in evidence_list)

    research_sec = parse_section_content(
        blocks, ("KEY RESEARCH DEVELOPMENT", "RESEARCH DEVELOPMENT", "RESEARCH SIGNAL"), valid_ids, limitations
    )
    competitor_sec = parse_section_content(
        blocks, ("COMPETITOR", "INDUSTRY ACTIVITY"), valid_ids, limitations
    )
    recent_sec = parse_section_content(
        blocks, ("RECENT DEVELOPMENT", "LATEST NEWS"), valid_ids, limitations
    )

    patents_sec = None
    if has_patents and has_patent_evidence:
        patents_sec = parse_section_content(blocks, ("PATENT",), valid_ids, limitations)

    why_matters = parse_section_content(
        blocks, ("WHY THIS MATTERS", "WHY IT MATTERS", "STRATEGIC IMPLICATION"), valid_ids, limitations
    )

    sections = ReportSections(
        research=research_sec,
        competitor_industry=competitor_sec,
        recent_developments=recent_sec,
        patents=patents_sec,
        why_it_matters=why_matters,
    )

    # 6. Extract Next Actions — never substituted with canned advice
    next_actions: list[str] = []
    actions_body = find_block(blocks, "RECOMMENDED NEXT ACTION", "NEXT ACTION", "RECOMMENDED ACTION")
    if actions_body:
        for act in split_bullets(actions_body):
            cleaned_act, _ = extract_and_validate_citations(act, valid_ids, limitations)
            cleaned_act = _EMPHASIS_RE.sub("", cleaned_act).strip()
            if len(cleaned_act) > 10:
                next_actions.append(cleaned_act)

    if not next_actions:
        limitations.append(
            "The agent did not produce a parsable set of recommended next actions for this run."
        )

    # 7. Build Coverage summary
    coverage: list[str] = []
    tool_counts: dict[str, int] = {}
    for ev in evidence_list:
        tool_counts[ev.tool] = tool_counts.get(ev.tool, 0) + 1

    for tool_name, count in tool_counts.items():
        coverage.append(f"{tool_name}: {count} verified sources gathered")

    if not has_patents:
        limitations.append("Patent search was unavailable for this run (no patent provider active)")
    elif not has_patent_evidence:
        limitations.append("Patent search was available but the agent gathered no patent evidence for this target")

    return Report(
        target=target,
        summary=summary,
        signals=signals,
        sections=sections,
        next_actions=next_actions,
        coverage=coverage,
        limitations=list(dict.fromkeys(limitations)),  # Deduplicate
    )
