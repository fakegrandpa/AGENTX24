"""Standalone scenario execution worker for AGENTX24 evaluation.

Executes exactly one investigation scenario in a dedicated subprocess to ensure
complete process-level configuration and environment variable isolation.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path


def run_worker() -> None:
    parser = argparse.ArgumentParser(description="AGENTX24 Isolated Scenario Worker")
    parser.add_argument("--objective", required=True, help="Investigation objective text")
    parser.add_argument("--out", required=True, help="Destination JSON file path for Run artifact")
    parser.add_argument("--scenario-id", default="scenario", help="Identifier of scenario being run")
    parser.add_argument("--adversarial", action="store_true", help="Arm adversarial fault injection")
    args = parser.parse_args()

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = time.time()

    # Import app components AFTER process environment is set
    try:
        from app.agent import run_investigation
        from app.models import Run

        run = run_investigation(
            objective=args.objective,
            adversarial=args.adversarial,
        )
        wall_s = round(time.time() - started_at, 2)

        run_dict = run.model_dump()
        run_dict["wall_s"] = wall_s
        run_dict["scenario_id"] = args.scenario_id

        out_path.write_text(json.dumps(run_dict, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[eval.worker] Successfully completed '{args.scenario_id}' in {wall_s}s -> {out_path}")
        sys.exit(0)

    except Exception as e:
        wall_s = round(time.time() - started_at, 2)
        error_dict = {
            "id": f"err_{int(time.time())}",
            "query": args.objective,
            "status": "error",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at)),
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_s": wall_s,
            "scenario_id": args.scenario_id,
            "adversarial": args.adversarial,
            "limitations": [f"Worker execution exception: {e}"],
            "evidence": [],
            "tool_calls": [],
            "telemetry": [],
            "report": None,
        }
        out_path.write_text(json.dumps(error_dict, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[eval.worker] ERROR during '{args.scenario_id}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_worker()
