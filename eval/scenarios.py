"""Declarative scenario suite for AGENTX24 evaluation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scenario:
    id: str
    klass: str  # normal | ambiguous | adversarial | contradictory | incomplete | tool_failure | baseline
    objective: str
    env: dict[str, str] = field(default_factory=dict)
    adversarial: bool = False
    repeats_quick: int = 1
    repeats_full: int = 1
    suites: list[str] = field(default_factory=lambda: ["quick", "full"])
    description: str = ""
    assertions: dict[str, Any] = field(default_factory=dict)


SCENARIOS: list[Scenario] = [
    Scenario(
        id="normal",
        klass="normal",
        objective="NVIDIA competitive position in AI infrastructure and datacenter networking",
        env={},
        adversarial=False,
        repeats_quick=2,
        repeats_full=3,
        suites=["quick", "full"],
        description="Standard multi-angle competitor and market intelligence investigation",
        assertions={
            "task_completion": (">=", 0.90),
            "groundedness": (">=", 0.95),
            "provider_kinds_covered": (">=", 2),
        },
    ),
    Scenario(
        id="ambiguous",
        klass="ambiguous",
        objective="Apple",
        env={},
        adversarial=False,
        repeats_quick=1,
        repeats_full=1,
        suites=["quick", "full"],
        description="Broad, under-specified one-word entity requiring uncertainty qualification",
        assertions={
            "task_completion": (">=", 0.80),
            "uncertainty_awareness": ("==", 1.0),
        },
    ),
    Scenario(
        id="incomplete",
        klass="incomplete",
        objective="zzqvx nonexistent nonsense subject 41927 quantum flux capacitor",
        env={},
        adversarial=False,
        repeats_quick=1,
        repeats_full=1,
        suites=["quick", "full"],
        description="Fictitious / impossible subject requiring honest refusal and zero hallucination",
        assertions={
            "unsupported_claim_rate": ("==", 0.0),
            "refusal_honesty": ("==", 1.0),
        },
    ),
    Scenario(
        id="adversarial",
        klass="adversarial",
        objective="Solid-state battery commercialization barriers and manufacturing scaling",
        env={"ADVERSARIAL_MODE": "1"},
        adversarial=True,
        repeats_quick=1,
        repeats_full=1,
        suites=["quick", "full"],
        description="Injected tool timeouts, provider downtime, and synthetic contradictory evidence",
        assertions={
            "status": ("==", "done"),
            "recovery": (">=", 0.75),
            "conflict_handling": ("==", 1.0),
        },
    ),
    Scenario(
        id="graph_off",
        klass="baseline",
        objective="NVIDIA competitive position in AI infrastructure and datacenter networking",
        env={"ENABLE_GRAPH": "0"},
        adversarial=False,
        repeats_quick=1,
        repeats_full=1,
        suites=["quick", "full"],
        description="Legacy baseline loop comparison (LangGraph disabled, fallback sequential loop)",
        assertions={
            "status": ("==", "done"),
        },
    ),
    Scenario(
        id="critic_off",
        klass="baseline",
        objective="NVIDIA competitive position in AI infrastructure and datacenter networking",
        env={"ENABLE_CRITIC": "0"},
        adversarial=False,
        repeats_quick=0,
        repeats_full=1,
        suites=["full"],
        description="Multi-agent ablation comparison (Evidence Critic feedback loop disabled)",
        assertions={
            "status": ("==", "done"),
        },
    ),
]


def get_scenarios_for_suite(suite_name: str = "quick", repeats_override: int | None = None) -> list[tuple[Scenario, int]]:
    """Returns list of (Scenario, repeat_count) tuples for a given suite name."""
    suite_key = suite_name.lower().strip()
    selected: list[tuple[Scenario, int]] = []

    for sc in SCENARIOS:
        if suite_key in sc.suites:
            if repeats_override is not None and repeats_override > 0:
                count = repeats_override
            elif suite_key == "quick":
                count = sc.repeats_quick
            else:
                count = sc.repeats_full

            if count > 0:
                selected.append((sc, count))

    return selected


def print_scenarios_summary() -> None:
    """CLI summary of scenario suites and projected execution counts."""
    print("=== AGENTX24 Evaluation Scenarios & Suites ===")
    
    classes_covered = {s.klass for s in SCENARIOS}
    print(f"Total Defined Scenarios : {len(SCENARIOS)}")
    print(f"Scenario Classes Covered: {', '.join(sorted(classes_covered))}")

    for suite in ["quick", "full"]:
        sc_pairs = get_scenarios_for_suite(suite)
        total_runs = sum(count for _, count in sc_pairs)
        print(f"\n--- Suite: '{suite.upper()}' ({len(sc_pairs)} scenarios, {total_runs} total runs) ---")
        for sc, reps in sc_pairs:
            adv_tag = " [ADVERSARIAL FAULT INJECTION]" if sc.adversarial else ""
            env_tag = f" [ENV: {sc.env}]" if sc.env else ""
            print(f"  * {sc.id:12} (class: {sc.klass:12}, repeats: {reps}){adv_tag}{env_tag}")
            print(f"    Objective: \"{sc.objective}\"")
            print(f"    Checks   : {sc.assertions}")

    print("\n==============================================")


if __name__ == "__main__":
    print_scenarios_summary()
