"""Pure evaluation metric functions for AGENTX24.

Operates purely on serialized Run dictionaries. Zero network calls, zero subprocesses,
zero imports from `app`. Fully auditable and reproducible offline.
"""

from __future__ import annotations
import math
import re
import statistics
from datetime import datetime
from typing import Any


def _parse_iso(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        # Handle ISO strings with Z or timezone offsets
        clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def compute(run: dict[str, Any]) -> dict[str, Any]:
    """Computes all 19 evaluation metrics for a single serialized Run dictionary.
    
    Tolerates missing fields and empty inputs gracefully without throwing exceptions.
    """
    if not isinstance(run, dict):
        run = {}

    status = run.get("status", "error")
    report = run.get("report") or {}
    evidence = run.get("evidence") or []
    tool_calls = run.get("tool_calls") or []
    telemetry = run.get("telemetry") or []
    limitations = run.get("limitations") or []
    graph_trace = run.get("graph_trace") or []
    conflicts = run.get("conflicts") or []
    uncertainty = run.get("uncertainty", "low")
    resource_ledger = run.get("resource_ledger") or {}

    # --- 1. Task Completion ---
    signals = report.get("signals") if isinstance(report, dict) else []
    if not isinstance(signals, list):
        signals = []

    sections = report.get("sections") if isinstance(report, dict) else {}
    if not isinstance(sections, dict):
        sections = {}

    summary_text = str(report.get("summary", "")) if isinstance(report, dict) else ""
    has_populated_section = any(bool(str(v).strip()) for v in sections.values() if v is not None)

    completion_components = [
        1.0 if status == "done" else 0.0,
        1.0 if bool(report) else 0.0,
        1.0 if len(signals) > 0 else 0.0,
        1.0 if len(summary_text.strip()) > 0 else 0.0,
        1.0 if has_populated_section else 0.0,
    ]
    task_completion = round(statistics.mean(completion_components), 4)

    # --- 2. Groundedness & Citations ---
    valid_ev_ids = {str(e.get("id")) for e in evidence if isinstance(e, dict) and "id" in e}
    
    # Extract all [En] citations across the entire synthesized report
    report_text_corpus = [summary_text]
    for s in signals:
        if isinstance(s, dict):
            report_text_corpus.append(str(s.get("headline", "")))
            report_text_corpus.append(str(s.get("detail", "")))
            for c in s.get("citations", []):
                report_text_corpus.append(f"[{c}]")
    for sec_val in sections.values():
        if sec_val:
            report_text_corpus.append(str(sec_val))
    if isinstance(report, dict):
        for act in report.get("next_actions", []):
            report_text_corpus.append(str(act))

    full_report_text = " ".join(report_text_corpus)
    citation_matches = re.findall(r"\[(E\d+)\]", full_report_text)
    total_citations = len(citation_matches)
    
    resolved_citations = [c for c in citation_matches if c in valid_ev_ids]
    unresolved_citations = [c for c in citation_matches if c not in valid_ev_ids]
    
    if total_citations > 0:
        groundedness = round(1.0 - (len(unresolved_citations) / total_citations), 4)
    else:
        # If no citations were present and no signals generated, groundedness is 1.0;
        # If signals were generated with zero grounding, groundedness is 0.0
        groundedness = 1.0 if len(signals) == 0 else 0.0

    citation_density = round(len(resolved_citations) / max(1, len(signals)), 4) if signals else 0.0
    
    cited_ids = set(resolved_citations)
    evidence_utilisation = round(len(cited_ids) / max(1, len(evidence)), 4) if evidence else 0.0

    # Blocked fabrication attempts (counted from deterministic report enforcement)
    report_limits = [str(l) for l in limitations]
    if isinstance(report, dict) and "limitations" in report:
        report_limits.extend([str(l) for l in report.get("limitations", [])])

    fabrication_attempts_blocked = sum(
        1 for l in report_limits
        if l.startswith("Stripped unverified citation marker") or l.startswith("Removed a model-authored link")
    )

    unsupported_signals = sum(
        1 for s in signals
        if isinstance(s, dict) and not s.get("citations")
    )
    unsupported_claim_rate = round(unsupported_signals / max(1, len(signals)), 4) if signals else 0.0

    # --- 3. Evidence Quality ---
    provider_names = {str(e.get("provider", e.get("source", "unknown"))) for e in evidence if isinstance(e, dict)}
    provider_kinds = {str(e.get("provider_kind", "web")) for e in evidence if isinstance(e, dict)}
    source_diversity = len(provider_names)
    provider_kinds_covered = len(provider_kinds)

    published_count = sum(1 for e in evidence if isinstance(e, dict) and e.get("published"))
    share_published = (published_count / len(evidence)) if evidence else 0.0

    days_old_vals = [e.get("days_old") for e in evidence if isinstance(e, dict) and isinstance(e.get("days_old"), (int, float))]
    median_days_old = statistics.median(days_old_vals) if days_old_vals else 365.0
    recency_subscore = 1.0 if median_days_old <= 730 else max(0.0, 1.0 - (median_days_old - 730) / 2000.0)

    corrob_vals = [e.get("corroboration", 0) for e in evidence if isinstance(e, dict) and isinstance(e.get("corroboration"), (int, float))]
    mean_corrob = statistics.mean(corrob_vals) if corrob_vals else 0.0
    corrob_subscore = min(1.0, mean_corrob / 2.0)

    evidence_subscores = [
        min(1.0, len(evidence) / 8.0),
        min(1.0, len(provider_kinds) / 4.0),
        share_published,
        recency_subscore,
        corrob_subscore,
    ]
    evidence_quality = round(statistics.mean(evidence_subscores), 4)

    # --- 4. Robustness & Recovery ---
    failed_tools = [t for t in tool_calls if isinstance(t, dict) and t.get("ok") is False]
    had_tool_failures = len(failed_tools) > 0
    
    # Check if a successful tool call happened after a failed tool call
    recovery_subscores = [1.0 if status == "done" else 0.0]
    if had_tool_failures:
        first_fail_idx = next(i for i, t in enumerate(tool_calls) if t.get("ok") is False)
        later_success = any(t.get("ok") is True for t in tool_calls[first_fail_idx + 1:])
        recovery_subscores.append(1.0 if later_success else 0.0)
    else:
        recovery_subscores.append(1.0)

    trace_str = " ".join([str(x).lower() for x in graph_trace] + [str(t.get("phase", "")).lower() for t in telemetry if isinstance(t, dict)])
    had_replan_or_eval = any(k in trace_str for k in ("replan", "fallback", "self_eval", "evaluat", "loop"))
    recovery_subscores.append(1.0 if had_replan_or_eval or not had_tool_failures else 0.5)
    recovery = round(statistics.mean(recovery_subscores), 4)

    # Conflict handling
    had_conflicts = len(conflicts) > 0 or any("conflict" in str(e.get("meta", {})) for e in evidence if isinstance(e, dict))
    conflict_resolved = "conflict" in trace_str or any("conflict" in l.lower() for l in report_limits)
    conflict_handling = 1.0 if (had_conflicts and conflict_resolved) or (not had_conflicts) else 0.0

    # Uncertainty awareness
    has_calibrated_uncertainty = uncertainty in ("low", "medium", "high")
    acknowledges_uncertainty = any(
        any(k in l.lower() for k in ("uncertain", "gap", "insufficient", "nonexistent", "unverified", "boundary"))
        for l in report_limits
    )
    uncertainty_awareness = 1.0 if has_calibrated_uncertainty or acknowledges_uncertainty else 0.0

    # Refusal honesty (specifically for unanswerable / incomplete queries)
    refusal_honesty = 1.0 if (unsupported_claim_rate == 0.0 and len(report_limits) > 0) or len(evidence) >= 4 else 0.0

    # --- 5. Efficiency ---
    started_dt = _parse_iso(run.get("started_at"))
    finished_dt = _parse_iso(run.get("finished_at"))
    if started_dt and finished_dt and finished_dt >= started_dt:
        latency_wall_s = round((finished_dt - started_dt).total_seconds(), 2)
    else:
        latency_wall_s = round(float(run.get("wall_s", 0.0)), 2)

    tool_latencies = [t.get("ms", 0) for t in tool_calls if isinstance(t, dict) and isinstance(t.get("ms"), (int, float))]
    tool_latency_ms = int(sum(tool_latencies))

    # LLM calls used
    if "llm_remaining" in resource_ledger and isinstance(resource_ledger["llm_remaining"], (int, float)):
        llm_calls_used = int(14 - resource_ledger["llm_remaining"])
    else:
        # Fallback: Count planning/final/critic telemetry events
        llm_calls_used = sum(
            1 for t in telemetry
            if isinstance(t, dict) and t.get("kind") in ("planning", "final") or "reasoning" in str(t.get("phase", "")).lower()
        )
        llm_calls_used = max(1, llm_calls_used)

    resource_efficiency = round(len(evidence) / max(1, llm_calls_used), 4)
    steps = len(telemetry)

    return {
        "status": status,
        "task_completion": task_completion,
        "groundedness": groundedness,
        "citation_density": citation_density,
        "evidence_utilisation": evidence_utilisation,
        "fabrication_attempts_blocked": fabrication_attempts_blocked,
        "unsupported_claim_rate": unsupported_claim_rate,
        "evidence_quality": evidence_quality,
        "source_diversity": source_diversity,
        "provider_kinds_covered": provider_kinds_covered,
        "recovery": recovery,
        "conflict_handling": conflict_handling,
        "uncertainty_awareness": uncertainty_awareness,
        "refusal_honesty": refusal_honesty,
        "latency_wall_s": latency_wall_s,
        "tool_latency_ms": tool_latency_ms,
        "llm_calls_used": llm_calls_used,
        "resource_efficiency": resource_efficiency,
        "steps": steps,
        "evidence_count": len(evidence),
        "signals_count": len(signals),
        "tool_calls_count": len(tool_calls),
    }


def consistency(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Computes variance, stability, and consistency across repeated runs of an objective."""
    if not runs:
        return {"consistency": 1.0, "repeats": 0, "status_agreement": 1.0}
    if len(runs) == 1:
        return {"consistency": 1.0, "repeats": 1, "status_agreement": 1.0}

    # 1. Status agreement
    statuses = [r.get("status", "error") for r in runs]
    status_agreement = 1.0 if len(set(statuses)) == 1 else (statuses.count("done") / len(statuses))

    # 2. Evidence count stability
    ev_counts = [len(r.get("evidence", [])) for r in runs]
    mean_ev = statistics.mean(ev_counts)
    stdev_ev = statistics.stdev(ev_counts) if len(ev_counts) > 1 else 0.0
    ev_stability = max(0.0, 1.0 - (stdev_ev / max(1.0, mean_ev)))

    # 3. Signals count stability
    sig_counts = [len((r.get("report") or {}).get("signals", [])) for r in runs]
    mean_sig = statistics.mean(sig_counts)
    stdev_sig = statistics.stdev(sig_counts) if len(sig_counts) > 1 else 0.0
    sig_stability = max(0.0, 1.0 - (stdev_sig / max(1.0, mean_sig)))

    # 4. Tool set Jaccard similarity
    tool_sets = [
        {str(t.get("name")) for t in r.get("tool_calls", []) if isinstance(t, dict)}
        for r in runs
    ]
    jaccards = []
    for i in range(len(tool_sets)):
        for j in range(i + 1, len(tool_sets)):
            s1, s2 = tool_sets[i], tool_sets[j]
            union = len(s1 | s2)
            if union > 0:
                jaccards.append(len(s1 & s2) / union)
            else:
                jaccards.append(1.0)
    tool_jaccard = statistics.mean(jaccards) if jaccards else 1.0

    composite = round(statistics.mean([status_agreement, ev_stability, sig_stability, tool_jaccard]), 4)

    return {
        "consistency": composite,
        "repeats": len(runs),
        "status_agreement": round(status_agreement, 4),
        "evidence_stability": round(ev_stability, 4),
        "signals_stability": round(sig_stability, 4),
        "tool_jaccard_similarity": round(tool_jaccard, 4),
    }


def baseline_delta(on_metrics: dict[str, Any], off_metrics: dict[str, Any]) -> dict[str, Any]:
    """Calculates difference (Graph ON - Baseline OFF) across metrics."""
    delta: dict[str, Any] = {}
    numerical_keys = [
        "task_completion", "groundedness", "citation_density", "evidence_utilisation",
        "evidence_quality", "source_diversity", "provider_kinds_covered", "recovery",
        "conflict_handling", "uncertainty_awareness", "refusal_honesty", "latency_wall_s",
        "llm_calls_used", "resource_efficiency", "steps", "evidence_count", "signals_count"
    ]

    for k in numerical_keys:
        val_on = on_metrics.get(k)
        val_off = off_metrics.get(k)
        if isinstance(val_on, (int, float)) and isinstance(val_off, (int, float)):
            diff = val_on - val_off
            delta[k] = round(diff, 4)
        else:
            delta[k] = "n/a"

    return delta
