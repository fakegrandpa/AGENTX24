"""Opt-in deterministic fault and evidence-conflict injection for live demos."""

from __future__ import annotations

import os
from typing import Any


_FAULTS: dict[str, int] = {}


def reset_faults() -> None:
    _FAULTS.clear()


def is_armed(run_flag: bool = False) -> bool:
    env_value = os.getenv("ADVERSARIAL_MODE", "0").strip().lower()
    return run_flag or env_value not in ("", "0", "false", "no", "off")


def maybe_fault(tool: str, args: dict[str, Any], run_flag: bool = False) -> dict[str, Any] | None:
    if not is_armed(run_flag):
        return None

    count = _FAULTS.get(tool, 0)
    _FAULTS[tool] = count + 1
    if count > 0:
        return None

    fault_kind = {
        "news_search": "timeout",
        "research_search": "provider_down",
    }.get(tool)
    if not fault_kind:
        return None
    return {
        "error": "adversarial_injected_failure",
        "tool": tool,
        "detail": f"Adversarial test injected {fault_kind} for {tool}",
        "results": [],
        "adversarial": True,
    }


def maybe_inject_conflict(tool: str, result: dict[str, Any], run_flag: bool = False) -> dict[str, Any]:
    if not is_armed(run_flag) or not result.get("results") or tool != "web_search":
        return result

    first = result["results"][0]
    injected = dict(first)
    injected.update(
        {
            "title": f"[ADVERSARIAL TEST] Contradictory signal: {first.get('title', 'source')}",
            "snippet": f"Contradictory test evidence: the opposite conclusion is reported for {first.get('title', 'this claim')}",
            "source": "Adversarial test source",
            "url": "https://example.invalid/adversarial-conflict",
            "meta": {**(first.get("meta") or {}), "synthetic": True, "adversarial": True},
        }
    )
    return {**result, "results": [*result["results"], injected]}


if __name__ == "__main__":
    reset_faults()
    print(maybe_fault("news_search", {"query": "demo"}, run_flag=True))
