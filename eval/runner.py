"""Automated evaluation suite runner for AGENTX24.

Orchestrates isolated scenario execution in dedicated subprocesses,
measures multi-agent performance across 6 required dimensions, computes
baseline deltas and multi-run consistency, and compiles the evaluation scorecard.
"""

from __future__ import annotations
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.criteria import CRITERIA, DIMENSIONS
from eval.metrics import baseline_delta, compute, consistency
from eval.scenarios import SCENARIOS, Scenario, get_scenarios_for_suite
from eval.scorecard import render_scorecard


def _check_assertion(metric_val: Any, rule: tuple[str, Any]) -> bool:
    op, target = rule
    if metric_val is None or metric_val == "n/a":
        return False
    if op == "==":
        return metric_val == target
    elif op == ">=":
        return float(metric_val) >= float(target)
    elif op == "<=":
        return float(metric_val) <= float(target)
    elif op == ">":
        return float(metric_val) > float(target)
    elif op == "<":
        return float(metric_val) < float(target)
    return False


def run_suite(
    suite_name: str = "quick",
    scenario_filter: str | None = None,
    repeats_override: int | None = None,
    gap_seconds: float = 5.0,
    out_dir_path: str | None = None,
    require_yes: bool = False,
) -> dict[str, Any]:
    root_dir = Path(__file__).resolve().parent.parent
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    if out_dir_path:
        results_dir = Path(out_dir_path).resolve()
    else:
        results_dir = root_dir / "eval" / "results" / timestamp

    runs_dir = results_dir / "runs"
    temp_dir = results_dir / "_temp"
    runs_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Select Scenarios
    if scenario_filter:
        matched = [s for s in SCENARIOS if s.id.lower() == scenario_filter.lower()]
        if not matched:
            raise ValueError(f"Unknown scenario ID '{scenario_filter}'. Available: {[s.id for s in SCENARIOS]}")
        selected_scenarios: list[tuple[Scenario, int]] = [(matched[0], repeats_override or 1)]
    else:
        selected_scenarios = get_scenarios_for_suite(suite_name, repeats_override)

    total_projected_runs = sum(reps for _, reps in selected_scenarios)

    print("==================================================================")
    print(f" AGENTX24 Autonomous Evaluation Harness - Suite '{suite_name.upper()}'")
    print("==================================================================")
    print(f"Timestamp          : {timestamp}")
    print(f"Target Output Dir  : {results_dir}")
    print(f"Scenarios Selected : {len(selected_scenarios)}")
    print(f"Total Runs to Run  : {total_projected_runs}")
    print(f"Inter-Run Spacing  : {gap_seconds}s")
    print(f"LLM Budget Ceiling : ~{total_projected_runs * 14} calls max")
    print("------------------------------------------------------------------")

    # 2. Memory & Live Store Isolation
    live_memory_file = root_dir / "data" / "investigation_memory.json"
    memory_backup_file = results_dir / "_memory_backup.json"
    
    if live_memory_file.exists():
        shutil.copy2(live_memory_file, memory_backup_file)

    isolated_memory_path = temp_dir / "isolated_memory.json"
    isolated_checkpoint_path = temp_dir / "isolated_checkpoints.sqlite"

    scenario_results: dict[str, Any] = {}
    all_executed_runs: list[dict[str, Any]] = []

    try:
        run_counter = 0
        for sc, repeat_count in selected_scenarios:
            print(f"\n>>> Running Scenario: '{sc.id}' ({sc.klass}) x{repeat_count} run(s)")
            print(f"    Objective: \"{sc.objective}\"")

            sc_runs_data: list[dict[str, Any]] = []
            sc_metrics_list: list[dict[str, Any]] = []

            for rep_idx in range(1, repeat_count + 1):
                run_counter += 1
                run_file_name = f"{sc.id}_rep{rep_idx}.json"
                out_run_json = runs_dir / run_file_name

                print(f"  [{run_counter}/{total_projected_runs}] Spawning worker for '{sc.id}' (run {rep_idx}/{repeat_count})...")

                worker_env = os.environ.copy()
                worker_env["MEMORY_STORAGE_PATH"] = str(isolated_memory_path)
                worker_env["GRAPH_CHECKPOINT_PATH"] = str(isolated_checkpoint_path)
                
                # Apply scenario-specific environment overrides
                for k, v in sc.env.items():
                    worker_env[k] = str(v)

                cmd = [
                    sys.executable,
                    "-m",
                    "eval.worker",
                    "--objective",
                    sc.objective,
                    "--out",
                    str(out_run_json),
                    "--scenario-id",
                    sc.id,
                ]
                if sc.adversarial:
                    cmd.append("--adversarial")

                proc = subprocess.run(cmd, cwd=str(root_dir), env=worker_env, capture_output=True, text=True)

                if proc.returncode != 0 and not out_run_json.exists():
                    print(f"    [WARN] Worker process failed with exit code {proc.returncode}: {proc.stderr}", file=sys.stderr)
                    # Write fallback failure record
                    run_dict = {
                        "id": f"err_worker_{int(time.time())}",
                        "query": sc.objective,
                        "status": "error",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                        "wall_s": 0.0,
                        "scenario_id": sc.id,
                        "limitations": [f"Worker process crashed: {proc.stderr}"],
                        "evidence": [],
                        "tool_calls": [],
                        "telemetry": [],
                        "report": None,
                    }
                    out_run_json.write_text(json.dumps(run_dict, indent=2), encoding="utf-8")
                else:
                    run_dict = json.loads(out_run_json.read_text(encoding="utf-8"))

                # Compute pure metrics from artifact
                run_metrics = compute(run_dict)
                sc_runs_data.append({"run_file": str(out_run_json.relative_to(results_dir)), "metrics": run_metrics})
                sc_metrics_list.append(run_metrics)
                all_executed_runs.append(run_dict)

                print(f"    -> Done (status: {run_metrics['status']}, completion: {run_metrics['task_completion']:.1%}, grounded: {run_metrics['groundedness']:.1%}, time: {run_metrics['latency_wall_s']}s)")

                if gap_seconds > 0 and run_counter < total_projected_runs:
                    time.sleep(gap_seconds)

            # Average metrics across repeats for this scenario
            avg_m: dict[str, Any] = {}
            for k in sc_metrics_list[0].keys():
                vals = [m[k] for m in sc_metrics_list if isinstance(m.get(k), (int, float))]
                if vals:
                    avg_m[k] = round(statistics.mean(vals), 4)
                else:
                    avg_m[k] = sc_metrics_list[0].get(k)

            # Check scenario assertions
            assertions_passed = True
            assertion_evals: dict[str, bool] = {}
            for k, rule in sc.assertions.items():
                passed = _check_assertion(avg_m.get(k), rule)
                assertion_evals[k] = passed
                if not passed:
                    assertions_passed = False

            scenario_results[sc.id] = {
                "class": sc.klass,
                "objective": sc.objective,
                "repeats": repeat_count,
                "adversarial": sc.adversarial,
                "runs": sc_runs_data,
                "average_metrics": avg_m,
                "assertions_passed": assertions_passed,
                "assertion_details": assertion_evals,
            }

    finally:
        # Restore live memory file to guarantee zero pollution
        if memory_backup_file.exists():
            shutil.copy2(memory_backup_file, live_memory_file)
            memory_backup_file.unlink(missing_ok=True)
        # Cleanup temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    # 3. Compute Cross-Run Consistency (using repeated runs of 'normal' scenario)
    normal_runs = [
        r for r in all_executed_runs
        if r.get("scenario_id") == "normal" and r.get("status") == "done"
    ]
    if len(normal_runs) > 1:
        consistency_res = consistency(normal_runs)
    else:
        consistency_res = consistency(all_executed_runs[:3] if len(all_executed_runs) >= 2 else all_executed_runs)

    # 4. Compute Baseline Delta (normal vs graph_off)
    normal_avg = scenario_results.get("normal", {}).get("average_metrics", {})
    graph_off_avg = scenario_results.get("graph_off", {}).get("average_metrics", {})
    delta_res = baseline_delta(normal_avg, graph_off_avg)

    # 5. Compile Complete Metrics Artifact
    metrics_payload: dict[str, Any] = {
        "metadata": {
            "timestamp": timestamp,
            "suite": suite_name,
            "total_runs": total_projected_runs,
            "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            "framework": "LangGraph (Stage 5 Architecture)",
            "output_directory": str(results_dir),
        },
        "scenarios": scenario_results,
        "consistency": consistency_res,
        "baseline_delta": delta_res,
    }

    metrics_json_path = results_dir / "metrics.json"
    metrics_json_path.write_text(json.dumps(metrics_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[eval.runner] Wrote metrics JSON -> {metrics_json_path}")

    # 6. Generate Markdown Scorecard
    scorecard_path = results_dir / "scorecard.md"
    scorecard_md = render_scorecard(metrics_payload)
    scorecard_path.write_text(scorecard_md, encoding="utf-8")
    print(f"[eval.runner] Wrote Scorecard -> {scorecard_path}")

    print("\n==================================================================")
    print("                  EVALUATION RUN COMPLETE")
    print("==================================================================")
    print(f"Scorecard Artifact : {scorecard_path}")
    print(f"Metrics JSON       : {metrics_json_path}")
    print("==================================================================")

    return metrics_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENTX24 Automated Evaluation Runner")
    parser.add_argument("--suite", choices=["quick", "full"], default="quick", help="Evaluation suite to execute")
    parser.add_argument("--scenario", default=None, help="Execute only one specific scenario ID")
    parser.add_argument("--repeats", type=int, default=None, help="Override repeat count for scenarios")
    parser.add_argument("--gap", type=float, default=5.0, help="Inter-run delay in seconds")
    parser.add_argument("--out", default=None, help="Custom output directory")
    parser.add_argument("--yes", action="store_true", help="Bypass confirmation prompt")
    args = parser.parse_args()

    run_suite(
        suite_name=args.suite,
        scenario_filter=args.scenario,
        repeats_override=args.repeats,
        gap_seconds=args.gap,
        out_dir_path=args.out,
        require_yes=args.yes,
    )


if __name__ == "__main__":
    main()
