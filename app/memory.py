from __future__ import annotations
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import MEMORY_RETRIEVAL_LIMIT, MEMORY_STORAGE_PATH
from app.models import MemoryRecord, Run

logger = logging.getLogger(__name__)

# Common English stopwords to ensure high-signal keyword extraction
_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves", "investigate", "target", "research",
    "latest", "recent", "overview", "status", "analysis"
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_keywords(text: str) -> set[str]:
    """Extracts meaningful lowercased terms and alphanumeric acronyms from text."""
    if not text:
        return set()
    tokens = re.findall(r"[a-zA-Z0-9_\-\+]{2,}", text.lower())
    keywords = {t for t in tokens if t not in _STOPWORDS and len(t) > 2}
    return keywords


def load_all_memories(storage_path: Path | None = None) -> list[MemoryRecord]:
    """Loads all persisted memory records. Fails gracefully to empty list on any IO/parse error."""
    path = storage_path or MEMORY_STORAGE_PATH
    if not path.exists():
        return []

    try:
        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []
        data = json.loads(raw_text)
        if not isinstance(data, list):
            return []
        records = []
        for item in data:
            try:
                records.append(MemoryRecord(**item))
            except Exception as parse_err:
                logger.warning("Skipping malformed memory record: %s", parse_err)
        return records
    except Exception as e:
        logger.warning("Failed to load investigation memory from %s: %s", path, e)
        return []


def save_memory(record: MemoryRecord, storage_path: Path | None = None, max_records: int = 100) -> bool:
    """Appends a new memory record and saves to disk atomically."""
    path = storage_path or MEMORY_STORAGE_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = load_all_memories(path)

        # Filter out existing record if same memory_id
        filtered = [m for m in existing if m.memory_id != record.memory_id]
        filtered.append(record)

        # Retain only the most recent max_records
        if len(filtered) > max_records:
            filtered = filtered[-max_records:]

        serialized = [m.model_dump() for m in filtered]
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(serialized, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(path)
        return True
    except Exception as e:
        logger.warning("Failed to save memory record to %s: %s", path, e)
        return False


def clear_memory_store(storage_path: Path | None = None) -> None:
    """Clears the memory store (primarily for test harnesses)."""
    path = storage_path or MEMORY_STORAGE_PATH
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        logger.warning("Failed to clear memory file %s: %s", path, e)


def calculate_relevance(query: str, record: MemoryRecord) -> float:
    """Calculates a semantic/keyword relevance score between query and a memory record."""
    q_words = extract_keywords(query)
    if not q_words:
        return 0.0

    target_text = f"{record.objective} {' '.join(record.entities_or_keywords)} {record.summary}"
    target_words = extract_keywords(target_text)
    if not target_words:
        return 0.0

    # 1. Jaccard token overlap
    intersection = q_words.intersection(target_words)
    jaccard = len(intersection) / len(q_words)

    # 2. Exact phrase / entity match bonus
    bonus = 0.0
    clean_q = query.strip().lower()
    clean_obj = record.objective.strip().lower()
    if clean_q in clean_obj or clean_obj in clean_q:
        bonus += 0.5
    for ent in record.entities_or_keywords:
        if ent.lower() in clean_q:
            bonus += 0.3

    return jaccard + bonus


def find_relevant_memories(
    objective: str,
    limit: int = MEMORY_RETRIEVAL_LIMIT,
    min_score: float = 0.25,
    storage_path: Path | None = None,
) -> list[MemoryRecord]:
    """Retrieves the top-K relevant past memories matching the target objective above min_score."""
    records = load_all_memories(storage_path)
    if not records:
        return []

    scored_records: list[tuple[float, MemoryRecord]] = []
    for r in records:
        score = calculate_relevance(objective, r)
        if score >= min_score:
            scored_records.append((score, r))

    # Sort descending by relevance score, then recency
    scored_records.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
    return [r for _, r in scored_records[:limit]]


def create_memory_from_run(run: Run) -> MemoryRecord | None:
    """Constructs a compact MemoryRecord from a completed Run."""
    if not run.report and not run.evidence:
        return None

    # Key findings from top signals
    key_findings: list[str] = []
    if run.report and run.report.signals:
        for s in run.report.signals[:4]:
            key_findings.append(f"[{s.tier.upper()}] {s.headline}: {s.detail[:160]}")
    elif run.evidence:
        for ev in run.evidence[:3]:
            key_findings.append(f"{ev.title} ({ev.source})")

    # Keywords from objective, tools, signals
    entities_or_keywords = sorted(list(extract_keywords(f"{run.query} {' '.join(key_findings)}")))[:15]
    tools_used = sorted(list({tc.get("name", "") for tc in run.tool_calls if tc.get("name")}))
    evidence_refs = [e.id for e in run.evidence[:10]]

    summary_text = run.report.summary if (run.report and run.report.summary) else f"Autonomous investigation of '{run.query}'"
    # Bound summary to 350 chars for compact memory footprint
    if len(summary_text) > 350:
        summary_text = summary_text[:347].rstrip() + "..."

    return MemoryRecord(
        memory_id=f"mem_{uuid.uuid4().hex[:8]}",
        created_at=run.finished_at or _iso_now(),
        objective=run.query,
        summary=summary_text,
        key_findings=key_findings,
        entities_or_keywords=entities_or_keywords,
        tools_used=tools_used,
        evidence_refs=evidence_refs,
        signal_count=len(run.report.signals) if run.report else 0,
    )


def format_prior_context_prompt(memories: list[MemoryRecord]) -> str:
    """Formats retrieved memories into an actionable prior context injection for the Investigator."""
    if not memories:
        return ""

    lines = ["=== RELEVANT PRIOR INVESTIGATION MEMORY ==="]
    lines.append(f"Found {len(memories)} relevant prior investigation record(s) in system memory:")
    for i, m in enumerate(memories, start=1):
        date_str = m.created_at[:10] if m.created_at else "recent"
        lines.append(f"\n[Prior Memory #{i} | {date_str}] Objective: \"{m.objective}\"")
        lines.append(f"Summary: {m.summary}")
        if m.key_findings:
            lines.append("Key Historical Findings:")
            for kf in m.key_findings[:3]:
                lines.append(f"  • {kf}")
        if m.tools_used:
            lines.append(f"Tools previously effective: {', '.join(m.tools_used)}")

    lines.append(
        "\n(CRITICAL OPERATING RULE: Prior memory provides historical continuity and hypotheses. "
        "Do NOT cite prior memory as current verified evidence. You must gather fresh evidence using tools for all claims in this run.)\n"
    )
    return "\n".join(lines)
