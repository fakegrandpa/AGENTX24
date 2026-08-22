"""Evaluation criteria, metric registries, and human evaluation rubric definitions."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    label: str
    dimension: str
    formula_doc: str
    direction: Literal["higher", "lower", "neutral"]
    unit: str
    threshold: float | int | None = None
    range_desc: str = "0-1"


DIMENSIONS: dict[str, str] = {
    "accuracy": "Accuracy & Groundedness (Faithfulness to gathered facts, blocked hallucinations, verifiable citations)",
    "task_completion": "Task Completion (Structured intelligence brief synthesis, coverage of key strategic sections)",
    "reliability": "Reliability & Consistency (Reproducibility across repeated runs, stability against variance)",
    "robustness": "Robustness & Recovery (Failure recovery, adversarial resilience, conflict resolution, honest uncertainty)",
    "evidence_quality": "Evidence Quality (Provider diversity, temporal recency, cross-source corroboration)",
    "efficiency": "Efficiency & Resource Footprint (Latency, LLM budget economy, tool dispatch performance)",
}

CRITERIA: dict[str, MetricDefinition] = {
    # 1. Accuracy & Groundedness
    "task_completion": MetricDefinition(
        id="task_completion",
        label="Task Completion Rate",
        dimension="task_completion",
        formula_doc="mean(status=='done', report present, len(signals)>0, summary non-empty, >=1 section populated)",
        direction="higher",
        unit="ratio",
        threshold=1.0,
        range_desc="0.0-1.0",
    ),
    "groundedness": MetricDefinition(
        id="groundedness",
        label="Evidence Groundedness",
        dimension="accuracy",
        formula_doc="1.0 - (unresolved_citations / total_citations) where unresolved means [En] not in evidence pool",
        direction="higher",
        unit="ratio",
        threshold=0.95,
        range_desc="0.0-1.0",
    ),
    "citation_density": MetricDefinition(
        id="citation_density",
        label="Citation Density",
        dimension="accuracy",
        formula_doc="total_resolved_citations / max(1, len(report.signals))",
        direction="higher",
        unit="citations/signal",
        threshold=1.0,
        range_desc=">=0.0",
    ),
    "evidence_utilisation": MetricDefinition(
        id="evidence_utilisation",
        label="Evidence Pool Utilisation",
        dimension="accuracy",
        formula_doc="len(cited_evidence_ids) / max(1, len(evidence_items))",
        direction="higher",
        unit="ratio",
        threshold=0.30,
        range_desc="0.0-1.0",
    ),
    "fabrication_attempts_blocked": MetricDefinition(
        id="fabrication_attempts_blocked",
        label="Fabrication Attempts Blocked",
        dimension="accuracy",
        formula_doc="count of report.limitations matching '^Stripped unverified citation marker' or '^Removed a model-authored link'",
        direction="neutral",
        unit="count",
        threshold=None,
        range_desc="integer (counts enforcement interventions)",
    ),
    "unsupported_claim_rate": MetricDefinition(
        id="unsupported_claim_rate",
        label="Unsupported Claim Rate",
        dimension="accuracy",
        formula_doc="len([s for s in report.signals if not s.citations]) / max(1, len(report.signals))",
        direction="lower",
        unit="ratio",
        threshold=0.10,
        range_desc="0.0-1.0 (lower is better)",
    ),
    # 2. Evidence Quality
    "evidence_quality": MetricDefinition(
        id="evidence_quality",
        label="Composite Evidence Quality",
        dimension="evidence_quality",
        formula_doc="mean(min(1, len(ev)/8), len(kinds)/4, share_published, min(1, median_days<=730), min(1, mean_corrob/2))",
        direction="higher",
        unit="score",
        threshold=0.70,
        range_desc="0.0-1.0",
    ),
    "source_diversity": MetricDefinition(
        id="source_diversity",
        label="Source Diversity (Providers)",
        dimension="evidence_quality",
        formula_doc="count of distinct external providers used in evidence collection",
        direction="higher",
        unit="providers",
        threshold=2,
        range_desc="integer (>=1)",
    ),
    "provider_kinds_covered": MetricDefinition(
        id="provider_kinds_covered",
        label="Provider Kinds Covered",
        dimension="evidence_quality",
        formula_doc="count of distinct provider kinds (news, research, web, patent) represented in evidence",
        direction="higher",
        unit="kinds",
        threshold=2,
        range_desc="1-4",
    ),
    # 3. Robustness & Recovery
    "recovery": MetricDefinition(
        id="recovery",
        label="Failure Recovery Rate",
        dimension="robustness",
        formula_doc="On failure scenarios: mean(status=='done', >=1 failed tool call, later successful tool call, replan/fallback in trace)",
        direction="higher",
        unit="ratio",
        threshold=0.75,
        range_desc="0.0-1.0",
    ),
    "conflict_handling": MetricDefinition(
        id="conflict_handling",
        label="Conflict Detection & Handling",
        dimension="robustness",
        formula_doc="1 if len(conflicts)>0 and (resolution in graph_trace or limitation noted) else 0",
        direction="higher",
        unit="binary",
        threshold=1.0,
        range_desc="0 or 1",
    ),
    "uncertainty_awareness": MetricDefinition(
        id="uncertainty_awareness",
        label="Uncertainty Identification",
        dimension="robustness",
        formula_doc="1 if uncertainty is calibrated or limitations acknowledge ambiguous/missing data else 0",
        direction="higher",
        unit="binary",
        threshold=1.0,
        range_desc="0 or 1",
    ),
    "refusal_honesty": MetricDefinition(
        id="refusal_honesty",
        label="Unsupported Refusal Honesty",
        dimension="robustness",
        formula_doc="On incomplete scenarios: 1 if unsupported_claim_rate==0 and len(report.limitations)>0 else 0",
        direction="higher",
        unit="binary",
        threshold=1.0,
        range_desc="0 or 1",
    ),
    # 4. Reliability & Consistency
    "consistency": MetricDefinition(
        id="consistency",
        label="Multi-Run Consistency Score",
        dimension="reliability",
        formula_doc="Across repeats: mean(1-norm_std(ev_count), 1-norm_std(signal_count), mean_jaccard(tool_sets), status_agreement)",
        direction="higher",
        unit="score",
        threshold=0.75,
        range_desc="0.0-1.0",
    ),
    # 5. Efficiency & Resource Footprint
    "latency_wall_s": MetricDefinition(
        id="latency_wall_s",
        label="Wall-Clock Latency",
        dimension="efficiency",
        formula_doc="Total investigation execution time in seconds (finished_at - started_at)",
        direction="lower",
        unit="seconds",
        threshold=120.0,
        range_desc="seconds (lower is faster)",
    ),
    "tool_latency_ms": MetricDefinition(
        id="tool_latency_ms",
        label="Total Tool Execution Time",
        dimension="efficiency",
        formula_doc="Sum of execution durations for all dispatched external tools in milliseconds",
        direction="lower",
        unit="ms",
        threshold=None,
        range_desc="milliseconds",
    ),
    "llm_calls_used": MetricDefinition(
        id="llm_calls_used",
        label="LLM Budget Consumption",
        dimension="efficiency",
        formula_doc="Count of LLM reasoning calls executed during the investigation run",
        direction="lower",
        unit="calls",
        threshold=14,
        range_desc="calls (<=14 limit)",
    ),
    "resource_efficiency": MetricDefinition(
        id="resource_efficiency",
        label="Evidence / LLM Efficiency Ratio",
        dimension="efficiency",
        formula_doc="len(evidence) / max(1, llm_calls_used)",
        direction="higher",
        unit="items/call",
        threshold=1.5,
        range_desc=">=0.0",
    ),
    "steps": MetricDefinition(
        id="steps",
        label="Telemetry Step Count",
        dimension="efficiency",
        formula_doc="Total number of logged telemetry and graph state transition events",
        direction="neutral",
        unit="events",
        threshold=None,
        range_desc="integer count",
    ),
}


HUMAN_RUBRIC = [
    {
        "criterion": "Strategic Intelligence Value",
        "dimension": "accuracy",
        "description": "Does the report provide meaningful, non-obvious competitor & technology insights rather than generic textbook summaries?",
        "scale": "1 (Generic / Trivial) to 5 (Deep, highly actionable strategic briefing)",
    },
    {
        "criterion": "Signal Prioritisation Correctness",
        "dimension": "task_completion",
        "description": "Are critical strategic developments correctly ranked under High / Important / Emerging tiers with clear rationale?",
        "scale": "1 (Arbitrary / Flat ranking) to 5 (Flawless strategic tiering and synthesis)",
    },
    {
        "criterion": "Evidence Appropriateness & Source Grounding",
        "dimension": "evidence_quality",
        "description": "Are citations used in context and representative of primary literature, news releases, or patent filings?",
        "scale": "1 (Misattributed / Out-of-context) to 5 (Rigorous, perfectly corroborated citation)",
    },
    {
        "criterion": "Honesty Regarding Gaps & Limitations",
        "dimension": "robustness",
        "description": "Does the system transparently acknowledge missing knowledge, unverified claims, or incomplete search spaces?",
        "scale": "1 (Unwarranted confidence / Overclaiming) to 5 (Transparent, rigorous boundary definition)",
    },
    {
        "criterion": "Investigation Readability & Auditability",
        "dimension": "reliability",
        "description": "Is the live decision trace clear, logical, and easy for an analyst or judge to inspect and verify?",
        "scale": "1 (Opaque / Confusing trace) to 5 (Crystal clear step-by-step reasoning & tool provenance)",
    },
]


def print_criteria_summary() -> None:
    """CLI helper to inspect metric definitions and dimension coverage."""
    print("=== AGENTX24 Evaluation Criteria & Metrics Registry ===")
    print(f"Total Dimensions : {len(DIMENSIONS)}")
    print(f"Total Metrics    : {len(CRITERIA)}")
    print(f"Human Rubrics    : {len(HUMAN_RUBRIC)}")
    print("\n--- Dimensions & Metrics Mapping ---")

    for dim_key, dim_desc in DIMENSIONS.items():
        dim_metrics = [m for m in CRITERIA.values() if m.dimension == dim_key]
        print(f"\n[{dim_key.upper()}] {dim_desc}")
        assert len(dim_metrics) >= 1, f"Dimension {dim_key} has no assigned metrics!"
        for m in dim_metrics:
            thresh_str = f" [Threshold: {m.threshold}]" if m.threshold is not None else ""
            print(f"  * {m.id:28} : {m.label} ({m.range_desc}){thresh_str}")
            print(f"    Formula: {m.formula_doc}")

    print("\n--- Human Evaluation Rubric (5 Criteria, 1-5 Scale) ---")
    for idx, r in enumerate(HUMAN_RUBRIC, 1):
        print(f"  {idx}. {r['criterion']} ({r['dimension']}): {r['description']}")
    print("\n=======================================================")


if __name__ == "__main__":
    print_criteria_summary()
