"""LangGraph orchestration layer over the existing AGENTX24 intelligence system."""

from __future__ import annotations

import asyncio
import hashlib
import re
import sqlite3
import time
import uuid
from operator import add
from typing import Any, Callable, Literal, TypedDict, Annotated

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.adversarial import is_armed, maybe_fault, maybe_inject_conflict, reset_faults
from app.agents import SYNTHESIST_INSTRUCTION, critique_evidence
from app.config import (
    ADVERSARIAL_MODE,
    ENABLE_CRITIC,
    ENABLE_MEMORY,
    GRAPH_RECURSION_LIMIT,
    LLM_CALL_BUDGET,
    MAX_CRITIQUES,
    MAX_REPLANS,
    MAX_TOOL_CALLS,
    MEMORY_RETRIEVAL_LIMIT,
    PARALLEL_TOOL_CALLS,
    WALL_CLOCK,
    GRAPH_CHECKPOINT_PATH,
)
from app.llm import LLMResponse, propose_next_step
from app.memory import create_memory_from_run, find_relevant_memories, format_prior_context_prompt, save_memory
from app.models import AgentRole, Critique, Evidence, InvestigationContext, PhaseEnum, Run, TelemetryEvent
from app.report import assemble_report
from app.tools import execute_tool, extract_reason, get_advertised_tools
from app.tools.patents import is_patent_tool_available


class GraphState(TypedDict, total=False):
    objective: str
    run_id: str
    plan: list[dict[str, Any]]
    pending_tasks: list[dict[str, Any]]
    completed_tasks: list[dict[str, Any]]
    current_agent: str
    routing_state: str
    evidence: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    context: dict[str, Any]
    critiques: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    verified_hypotheses: list[dict[str, Any]]
    rejected_hypotheses: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    uncertainty: str
    resource_ledger: dict[str, Any]
    loop_signatures: list[str]
    no_progress_count: int
    limitations: list[str]
    errors: list[str]
    tool_requests: list[dict[str, Any]]
    worker_results: Annotated[list[dict[str, Any]], add]
    graph_trace: Annotated[list[str], add]
    checkpoints: Annotated[list[str], add]
    telemetry: Annotated[list[dict[str, Any]], add]
    final_text: str
    report: dict[str, Any] | None
    completed: bool
    replan_count: int
    adversarial: bool


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _tool_phase(name: str) -> PhaseEnum:
    return {
        "news_search": PhaseEnum.CHECKING_NEWS,
        "research_search": PhaseEnum.SEARCHING_RESEARCH,
        "web_search": PhaseEnum.SEARCHING_WEB,
        "patent_search": PhaseEnum.SEARCHING_PATENTS,
    }.get(name, PhaseEnum.PLANNING_NEXT_STEP)


def _emit(state: GraphState, phase: PhaseEnum, kind: str, text: str, agent: str, detail: str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    event = TelemetryEvent(
        seq=len(state.get("telemetry", [])) + 1,
        ts=_now(),
        phase=phase,
        kind=kind,  # type: ignore
        text=text,
        agent=agent,  # type: ignore
        detail=detail,
        data=data,
    )
    return event.model_dump(mode="json")


def _trace(state: GraphState, name: str) -> dict[str, Any]:
    return {
        "graph_trace": [name],
        "telemetry": [_emit(state, PhaseEnum.GRAPH_NODE_ENTERED, "planning", f"Graph node: {name}", state.get("current_agent", "investigator"), data={"node": name})],
    }


def _budget(state: GraphState) -> dict[str, Any]:
    ledger = dict(state.get("resource_ledger") or {})
    return {
        "llm_remaining": max(0, int(ledger.get("llm_remaining", LLM_CALL_BUDGET)) - 1),
        "tool_remaining": max(0, int(ledger.get("tool_remaining", MAX_TOOL_CALLS))),
        "replans_remaining": max(0, int(ledger.get("replans_remaining", MAX_REPLANS))),
    }


def retrieve_memory(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "retrieve_memory")
    context = dict(state.get("context") or {})
    memories = []
    if ENABLE_MEMORY:
        memories = find_relevant_memories(state["objective"], limit=MEMORY_RETRIEVAL_LIMIT)
        if memories:
            output["telemetry"].append(_emit(state, PhaseEnum.PRIOR_CONTEXT_FOUND, "planning", "Relevant prior context retrieved", "investigator", data={"count": len(memories), "memories": [{"id": m.memory_id, "objective": m.objective, "created_at": m.created_at} for m in memories]}))
    context["run_id"] = state["run_id"]
    context["objective"] = state["objective"]
    context["prior_memories"] = [m.model_dump(mode="json") for m in memories]
    return {**output, "context": context, "current_agent": "investigator", "routing_state": "planning", "resource_ledger": {"llm_remaining": LLM_CALL_BUDGET, "tool_remaining": MAX_TOOL_CALLS, "replans_remaining": MAX_REPLANS, "parallel_capacity": PARALLEL_TOOL_CALLS}}


def _fallback_plan(objective: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # This fallback is objective-derived and keeps the graph usable when the planner call fails.
    words = set(re.findall(r"[a-z0-9]+", objective.lower()))
    candidates = [
        ("recent developments", "news_search"),
        ("technical evidence", "research_search"),
        ("independent context", "web_search"),
    ]
    if words.intersection({"patent", "patents", "ip", "intellectual"}):
        candidates.append(("intellectual property evidence", "patent_search"))
    plan = [{"id": f"task_{i+1}", "objective": need, "candidate_tools": [tool], "priority": i + 1, "status": "pending", "dependencies": []} for i, (need, tool) in enumerate(candidates)]
    hypotheses = [{"id": "h1", "claim": f"The available evidence will explain the main drivers of {objective}.", "status": "unverified", "evidence": []}]
    return plan, hypotheses


def plan(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "plan")
    if int((state.get("resource_ledger") or {}).get("llm_remaining", 0)) <= 0:
        p, h = _fallback_plan(state["objective"])
        return {**output, "plan": p, "pending_tasks": p, "hypotheses": h, "limitations": ["Planner budget exhausted; objective-derived fallback plan used."]}
    schema = [{"name": "submit_plan", "description": "Return a dynamic investigation plan and hypotheses.", "parameters": {"type": "object", "properties": {"tasks": {"type": "array", "items": {"type": "object"}}, "hypotheses": {"type": "array", "items": {"type": "object"}}}, "required": ["tasks"]}}]
    prompt = f"Objective: {state['objective']}\nPrior context: {state.get('context', {}).get('prior_memories', [])}\nCreate a small adaptive plan of independent information needs. Include candidate_tools, priority, dependencies, and one or more hypotheses. Call submit_plan."
    try:
        response: LLMResponse = propose_next_step([prompt], tools_schema=schema)
        args = response.tool_calls[0].args if response.tool_calls and response.tool_calls[0].name == "submit_plan" else {}
        tasks = [dict(t) for t in args.get("tasks", []) if isinstance(t, dict)]
        hypotheses = [dict(h) for h in args.get("hypotheses", []) if isinstance(h, dict)]
        if not tasks:
            raise ValueError("planner returned no tasks")
    except Exception as exc:
        tasks, hypotheses = _fallback_plan(state["objective"])
        output.setdefault("limitations", []).append(f"Planner fallback used: {exc}")
    normalized = []
    for i, task in enumerate(tasks[:PARALLEL_TOOL_CALLS]):
        normalized.append({"id": task.get("id", f"task_{i+1}"), "objective": task.get("objective", task.get("information_need", "additional evidence")), "candidate_tools": task.get("candidate_tools", []), "priority": task.get("priority", i + 1), "dependencies": task.get("dependencies", []), "status": "pending"})
    output["resource_ledger"] = _budget(state)
    return {**output, "plan": normalized, "pending_tasks": normalized, "hypotheses": hypotheses, "current_agent": "investigator", "routing_state": "investigating"}


def investigator(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "investigator")
    tasks = state.get("pending_tasks", [])
    prompt = f"Objective: {state['objective']}\nDynamic plan: {tasks}\nEvidence so far: {state.get('evidence', [])[-12:]}\nOpen conflicts: {state.get('conflicts', [])}\nHypotheses: {state.get('hypotheses', [])}\nChoose the next minimum set of tools needed now. You may make multiple independent calls. Provide reason for every call."
    try:
        response: LLMResponse = propose_next_step([prompt], tools_schema=get_advertised_tools())
        requests = [{"name": c.name, "args": c.args, "reason": extract_reason(c.args), "task": tasks[i % len(tasks)] if tasks else {}} for i, c in enumerate(response.tool_calls[:PARALLEL_TOOL_CALLS])]
    except Exception as exc:
        requests = []
        output.setdefault("limitations", []).append(f"Investigator planner turn failed: {exc}")
    if not requests:
        requests = [{"name": t["candidate_tools"][0], "args": {"query": t["objective"], "limit": 5, "reason": f"Address {t['objective']}"}, "reason": f"Address {t['objective']}", "task": t} for t in tasks[:PARALLEL_TOOL_CALLS] if t.get("candidate_tools")]
    output["resource_ledger"] = _budget(state)
    output["telemetry"].append(_emit(state, PhaseEnum.PARALLEL_DISPATCH, "planning", f"Dispatching {len(requests)} independent task(s)", "investigator", data={"count": len(requests), "tools": [r["name"] for r in requests]}))
    for index, request in enumerate(requests, start=1):
        output["telemetry"].append(_emit(state, _tool_phase(request["name"]), "tool_selected", f"Selected {request['name']}", "investigator", detail=f"{request['name']}(\"{request.get('args', {}).get('query', '')}\")", data={"tool": request["name"], "args": request.get("args", {}), "query": request.get("args", {}).get("query", ""), "reason": request.get("reason"), "call_index": index}))
    return {**output, "tool_requests": requests, "current_agent": "investigator", "routing_state": "parallel"}


def dispatch_workers(state: GraphState) -> list[Send]:
    requests = state.get("tool_requests", [])[:PARALLEL_TOOL_CALLS]
    return [Send("parallel_tool_worker", {"request": request, "run_id": state["run_id"], "adversarial": state.get("adversarial", False)}) for request in requests]


def parallel_tool_worker(state: dict[str, Any]) -> dict[str, Any]:
    request = state["request"]
    name = request["name"]
    args = dict(request.get("args") or {})
    if state.get("adversarial"):
        fault = maybe_fault(name, args, run_flag=True)
        result = fault if fault else execute_tool(name, args)
        if not fault:
            result = maybe_inject_conflict(name, result, run_flag=True)
    else:
        result = execute_tool(name, args)
    result_event = {
        "seq": 0,
        "ts": _now(),
        "phase": PhaseEnum.EVIDENCE_FOUND.value if result.get("results") else (PhaseEnum.SOURCE_UNAVAILABLE.value if "error" in result else PhaseEnum.NO_RESULTS.value),
        "kind": "tool_result" if result.get("results") else "note",
        "text": f"Evidence gathered from {name}" if result.get("results") else f"{name} unavailable" if "error" in result else f"No results for '{args.get('query', '')}'",
        "agent": "investigator",
        "detail": result.get("detail") or f"{len(result.get('results', []))} results",
        "data": {"tool": name, "new_evidence": len(result.get("results", [])), "total_evidence": len(result.get("results", [])), "ok": "error" not in result, "error": result.get("error")},
    }
    return {
        "worker_results": [{"name": name, "args": args, "reason": request.get("reason"), "task": request.get("task", {}), "result": result}],
        "graph_trace": ["parallel_tool_worker"],
        "telemetry": [result_event],
    }


def collect_evidence(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "collect_evidence")
    evidence = [Evidence(**e) for e in state.get("evidence", [])]
    tool_calls = list(state.get("tool_calls", []))
    context = dict(state.get("context") or {})
    next_pending = []
    errors = list(state.get("errors", []))
    progress = False
    for worker in state.get("worker_results", []):
        result = worker.get("result", {})
        name = worker["name"]
        ok = "error" not in result
        results = result.get("results", []) if isinstance(result.get("results", []), list) else []
        tool_calls.append({"name": name, "args": worker.get("args", {}), "reason": worker.get("reason"), "ok": ok, "ms": 0})
        signature = hashlib.sha1(f"{name}:{worker.get('args', {}).get('query', '').strip().lower()}".encode()).hexdigest()[:16]
        if results:
            progress = True
        for item in results:
            ev_id = f"E{len(evidence) + 1}"
            ev = Evidence(id=ev_id, tool=name, provider=item.get("provider", name), provider_kind=item.get("provider_kind", "web"), source=item.get("source", "Unknown"), title=item.get("title", "Untitled"), url=item.get("url", ""), published=item.get("published"), days_old=item.get("days_old"), authors=item.get("authors", []), snippet=item.get("snippet", ""), meta=item.get("meta", {}))
            evidence.append(ev)
            context.setdefault("evidence_summary", []).append(f"[{ev_id}] [{name}] {ev.title} ({ev.source})")
        context.setdefault("tool_history", []).append({"step": len(tool_calls), "tool": name, "query": worker.get("args", {}).get("query", ""), "reason": worker.get("reason"), "ok": ok, "results_count": len(results)})
        if not ok:
            errors.append(f"{name}: {result.get('detail') or result.get('error') or 'tool failure'}")
            next_pending.append({"id": f"recovery_{len(next_pending)+1}", "objective": worker.get("task", {}).get("objective", "recover failed evidence"), "candidate_tools": [t["name"] for t in get_advertised_tools() if t["name"] != name], "priority": 1, "dependencies": [], "status": "pending"})
    context["updated_at"] = _now()
    signatures = [*state.get("loop_signatures", [])]
    for worker in state.get("worker_results", []):
        signatures.append(hashlib.sha1(f"{worker['name']}:{worker.get('args', {}).get('query', '').strip().lower()}".encode()).hexdigest()[:16])
    ledger = dict(state.get("resource_ledger") or {})
    ledger["tool_remaining"] = max(0, int(ledger.get("tool_remaining", MAX_TOOL_CALLS)) - len(state.get("worker_results", [])))
    completed = [*state.get("completed_tasks", []), *[w.get("task", {}) for w in state.get("worker_results", []) if w.get("result", {}).get("results")]]
    output["telemetry"].append(_emit(state, PhaseEnum.CONTEXT_UPDATED, "planning", "Investigation context updated", "investigator", data={"evidence_count": len(evidence), "tool_calls": len(tool_calls)}))
    no_progress = 0 if progress else state.get("no_progress_count", 0) + 1
    if no_progress >= 2:
        output["telemetry"].append(_emit(state, PhaseEnum.LOOP_DETECTED, "planning", "Repeated no-progress strategy detected", "investigator", data={"count": no_progress}))
    return {**output, "evidence": [e.model_dump(mode="json") for e in evidence], "tool_calls": tool_calls, "context": context, "pending_tasks": next_pending, "completed_tasks": completed, "worker_results": [], "errors": errors, "loop_signatures": signatures[-20:], "resource_ledger": ledger, "no_progress_count": no_progress, "routing_state": "analysis"}


def detect_conflicts(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "detect_conflicts")
    evidence = state.get("evidence", [])
    conflicts = list(state.get("conflicts", []))
    positive_terms = {"increase", "increased", "growth", "grew", "supports", "adoption", "strong"}
    negative_terms = {"decrease", "decreased", "decline", "declined", "weak", "falls", "not", "contradict"}
    for index, item in enumerate(evidence):
        if item.get("meta", {}).get("synthetic"):
            digest = hashlib.sha1(item.get("title", "").encode()).hexdigest()[:8]
            if not any(c.get("id") == digest for c in conflicts):
                conflicts.append({"id": digest, "claim": item.get("title", ""), "supporting_evidence": [], "contradicting_evidence": [item.get("id")], "status": "UNRESOLVED", "resolution": "synthetic adversarial contradiction requires verification"})
        for other in evidence[index + 1:]:
            left = set(re.findall(r"[a-z0-9]{4,}", f"{item.get('title', '')} {item.get('snippet', '')}".lower()))
            right = set(re.findall(r"[a-z0-9]{4,}", f"{other.get('title', '')} {other.get('snippet', '')}".lower()))
            shared = left.intersection(right) - positive_terms - negative_terms
            left_polarity = bool(left.intersection(positive_terms))
            right_polarity = bool(right.intersection(positive_terms))
            left_negative = bool(left.intersection(negative_terms))
            right_negative = bool(right.intersection(negative_terms))
            if len(shared) >= 2 and ((left_polarity and right_negative) or (right_polarity and left_negative)):
                digest = hashlib.sha1(f"{item.get('id')}:{other.get('id')}".encode()).hexdigest()[:8]
                if not any(c.get("id") == digest for c in conflicts):
                    conflicts.append({"id": digest, "claim": "Contradictory evidence for " + ", ".join(sorted(shared)[:4]), "supporting_evidence": [item.get("id")], "contradicting_evidence": [other.get("id")], "status": "UNRESOLVED", "resolution": "requires additional verification"})
    if conflicts:
        output["telemetry"].append(_emit(state, PhaseEnum.CONFLICT_DETECTED, "planning", "Conflicting evidence detected", "investigator", data={"count": len(conflicts)}))
    return {**output, "conflicts": conflicts, "uncertainty": "high" if conflicts else state.get("uncertainty", "low"), "routing_state": "conflict_resolution" if conflicts else "verification"}


def resolve_conflicts(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "resolve_conflicts")
    conflicts = []
    for conflict in state.get("conflicts", []):
        item = dict(conflict)
        if item.get("status") == "UNRESOLVED" and state.get("adversarial"):
            item["status"] = "PARTIALLY_RESOLVED"
            item["resolution"] = "Conflict preserved as uncertainty; additional verification required."
        conflicts.append(item)
    output["telemetry"].append(_emit(state, PhaseEnum.CONFLICT_RESOLVED, "note", "Conflicting evidence reviewed", "critic", data={"count": len(conflicts), "statuses": [c.get("status") for c in conflicts]}))
    return {**output, "conflicts": conflicts, "uncertainty": "high" if any(c.get("status") != "RESOLVED" for c in conflicts) else "medium", "routing_state": "verification"}


def verify_hypotheses(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "verify_hypotheses")
    evidence_text = " ".join(f"{e.get('title', '')} {e.get('snippet', '')}" for e in state.get("evidence", [])).lower()
    hypotheses = []
    verified = []
    rejected = []
    for h in state.get("hypotheses", []):
        claim = str(h.get("claim", ""))
        status = "SUPPORTED" if claim and any(word in evidence_text for word in re.findall(r"[a-z0-9]{5,}", claim.lower())) else "UNCERTAIN"
        item = {**h, "status": status, "evidence": [e.get("id") for e in state.get("evidence", [])[:3]]}
        hypotheses.append(item)
        (verified if status == "SUPPORTED" else rejected).append(item)
        output["telemetry"].append(_emit(state, PhaseEnum.HYPOTHESIS_VERIFIED, "planning", f"Hypothesis {item.get('id', 'unknown')}: {status}", "investigator", data={"hypothesis": item}))
    uncertainty = "high" if rejected or state.get("conflicts") else state.get("uncertainty", "low")
    output["telemetry"].append(_emit(state, PhaseEnum.UNCERTAINTY_UPDATED, "planning", f"Uncertainty updated: {uncertainty}", "critic", data={"uncertainty": uncertainty}))
    return {**output, "hypotheses": hypotheses, "verified_hypotheses": verified, "rejected_hypotheses": rejected, "uncertainty": uncertainty}


def critic(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "critic")
    if not ENABLE_CRITIC or not state.get("evidence"):
        return {**output, "routing_state": "self_evaluate"}
    critique = critique_evidence(state["objective"], [Evidence(**e) for e in state["evidence"]], state.get("tool_calls", []), seq=len(state.get("critiques", [])) + 1)
    critiques = [*state.get("critiques", []), critique.model_dump(mode="json")]
    context = dict(state.get("context") or {})
    context.setdefault("critic_feedback", []).append(critique.model_dump(mode="json"))
    context["knowledge_gaps"] = critique.gaps
    context["critique_count"] = len(critiques)
    if not critique.sufficient:
        output["telemetry"].append(_emit(state, PhaseEnum.CONTEXT_UPDATED, "planning", "Critic feedback updated shared context", "critic", data={"gaps": critique.gaps, "critique_count": len(critiques)}))
    return {**output, "critiques": critiques, "context": context, "routing_state": "replan" if not critique.sufficient else "self_evaluate", "uncertainty": "high" if not critique.sufficient else state.get("uncertainty", "low")}


def self_evaluate(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "self_evaluate")
    resources = state.get("resource_ledger", {})
    if (state.get("errors") or state.get("no_progress_count", 0) >= 2) and int(resources.get("replans_remaining", 0)) > 0:
        decision = "REPLAN"
    elif state.get("conflicts") and int(resources.get("replans_remaining", 0)) > 0:
        decision = "REPLAN"
    elif state.get("uncertainty") == "high" and int(resources.get("replans_remaining", 0)) > 0:
        decision = "REPLAN"
    elif not state.get("evidence"):
        decision = "SYNTHESIZE_WITH_LIMITATIONS"
    else:
        decision = "SYNTHESIZE"
    output["telemetry"].append(_emit(state, PhaseEnum.SELF_EVALUATION, "planning", f"Self-evaluation: {decision}", "critic", data={"decision": decision, "uncertainty": state.get("uncertainty", "low")}))
    return {**output, "routing_state": "replan" if decision == "REPLAN" else "synthesize"}


def replan(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "replan")
    count = state.get("replan_count", 0) + 1
    ledger = dict(state.get("resource_ledger") or {})
    ledger["replans_remaining"] = max(0, int(ledger.get("replans_remaining", MAX_REPLANS)) - 1)
    gaps = (state.get("context") or {}).get("knowledge_gaps", [])
    existing = {t.get("objective") for t in state.get("completed_tasks", [])}
    tasks = [t for t in state.get("pending_tasks", []) if t.get("objective") not in existing]
    if not tasks:
        tools = [t["name"] for t in get_advertised_tools()]
        tasks = [{"id": f"replan_{count}", "objective": gap or "independent verification", "candidate_tools": tools[:2], "priority": 1, "dependencies": [], "status": "pending"} for gap in (gaps or ["independent verification"])][:PARALLEL_TOOL_CALLS]
    if state.get("errors"):
        output["telemetry"].append(_emit(state, PhaseEnum.TOOL_FALLBACK, "planning", "Replanning after tool failure", "investigator", data={"errors": state.get("errors", []), "alternatives": tasks}))
    output["telemetry"].append(_emit(state, PhaseEnum.PLAN_REVISED, "planning", "Investigation plan revised", "investigator", data={"replan_count": count, "tasks": tasks}))
    return {**output, "pending_tasks": tasks, "plan": tasks, "replan_count": count, "resource_ledger": ledger, "routing_state": "investigating"}


def synthesize(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "synthesize")
    evidence = [Evidence(**e) for e in state.get("evidence", [])]
    limitations = list(state.get("limitations", []))
    if state.get("conflicts"):
        limitations.append(f"{len(state['conflicts'])} evidence conflict(s) remain unresolved by the graph.")
    if state.get("uncertainty") != "low":
        limitations.append(f"Graph self-evaluation uncertainty: {state.get('uncertainty')}.")
    prompt = f"Investigation complete for '{state['objective']}'. Use only these evidence records: {evidence}. Conflicts: {state.get('conflicts', [])}. Hypotheses: {state.get('hypotheses', [])}. Synthesize the required report headings with citations."
    text = ""
    try:
        response = propose_next_step([prompt], system_instruction=SYNTHESIST_INSTRUCTION)
        text = response.text
    except Exception as exc:
        limitations.append(f"Graph synthesis error: {exc}")
    report = assemble_report(state["objective"], text, evidence, state.get("tool_calls", []), limitations, is_patent_tool_available())
    output["telemetry"].append(_emit(state, PhaseEnum.GENERATING_REPORT, "final", "Generating prioritized intelligence report", "synthesist", data={"evidence": len(evidence)}))
    return {**output, "final_text": text, "report": report.model_dump(mode="json"), "limitations": limitations, "completed": True, "routing_state": "persist_memory", "current_agent": "synthesist"}


def persist_memory(state: GraphState) -> dict[str, Any]:
    output = _trace(state, "persist_memory")
    if ENABLE_MEMORY and state.get("report"):
        run = _state_to_run(state)
        memory = create_memory_from_run(run)
        if memory and save_memory(memory):
            output["telemetry"].append(_emit(state, PhaseEnum.MEMORY_SAVED, "note", "Investigation saved to memory", "synthesist", data={"memory_id": memory.memory_id, "signal_count": memory.signal_count}))
    output["telemetry"].append(_emit(state, PhaseEnum.COMPLETED, "final", "Intelligence report ready", "synthesist", data={"evidence": len(state.get("evidence", [])), "tool_calls": len(state.get("tool_calls", [])), "prior_memories": len((state.get("context") or {}).get("prior_memories", []))}))
    return {**output, "routing_state": "done", "completed": True}


def route_after_plan(state: GraphState) -> Literal["investigator", "synthesize"]:
    return "synthesize" if not state.get("pending_tasks") else "investigator"


def route_after_investigator(state: GraphState) -> list[Send] | Literal["self_evaluate"]:
    return dispatch_workers(state) if state.get("tool_requests") else "self_evaluate"


def route_after_critic(state: GraphState) -> Literal["replan", "self_evaluate"]:
    return "replan" if state.get("routing_state") == "replan" and state.get("replan_count", 0) < MAX_REPLANS else "self_evaluate"


def route_after_self_eval(state: GraphState) -> Literal["replan", "synthesize"]:
    return "replan" if state.get("routing_state") == "replan" and state.get("replan_count", 0) < MAX_REPLANS else "synthesize"


def _checkpoint_saver() -> Any:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        connection = sqlite3.connect(str(GRAPH_CHECKPOINT_PATH), check_same_thread=False)
        saver = SqliteSaver(connection)
        saver.setup()
        return saver
    except Exception:
        return InMemorySaver()


def build_graph() -> tuple[Any, Any]:
    builder = StateGraph(GraphState)
    builder.add_node("retrieve_memory", retrieve_memory)
    builder.add_node("plan", plan)
    builder.add_node("investigator", investigator)
    builder.add_node("parallel_tool_worker", parallel_tool_worker)
    builder.add_node("collect_evidence", collect_evidence)
    builder.add_node("detect_conflicts", detect_conflicts)
    builder.add_node("resolve_conflicts", resolve_conflicts)
    builder.add_node("verify_hypotheses", verify_hypotheses)
    builder.add_node("critic", critic)
    builder.add_node("self_evaluate", self_evaluate)
    builder.add_node("replan", replan)
    builder.add_node("synthesize", synthesize)
    builder.add_node("persist_memory", persist_memory)
    builder.add_edge(START, "retrieve_memory")
    builder.add_edge("retrieve_memory", "plan")
    builder.add_conditional_edges("plan", route_after_plan, {"investigator": "investigator", "synthesize": "synthesize"})
    builder.add_conditional_edges("investigator", route_after_investigator, {"self_evaluate": "self_evaluate", "parallel_tool_worker": "parallel_tool_worker"})
    builder.add_edge("parallel_tool_worker", "collect_evidence")
    builder.add_edge("collect_evidence", "detect_conflicts")
    builder.add_conditional_edges("detect_conflicts", lambda state: "resolve_conflicts" if state.get("conflicts") else "verify_hypotheses", {"resolve_conflicts": "resolve_conflicts", "verify_hypotheses": "verify_hypotheses"})
    builder.add_edge("resolve_conflicts", "verify_hypotheses")
    builder.add_edge("verify_hypotheses", "critic")
    builder.add_conditional_edges("critic", route_after_critic, {"replan": "replan", "self_evaluate": "self_evaluate"})
    builder.add_conditional_edges("self_evaluate", route_after_self_eval, {"replan": "replan", "synthesize": "synthesize"})
    builder.add_edge("replan", "investigator")
    builder.add_edge("synthesize", "persist_memory")
    builder.add_edge("persist_memory", END)
    saver = _checkpoint_saver()
    return builder.compile(checkpointer=saver), saver


def _state_to_run(state: GraphState) -> Run:
    context_data = dict(state.get("context") or {})
    context_data.setdefault("run_id", state["run_id"])
    context_data.setdefault("objective", state["objective"])
    context_data.setdefault("active_agent", state.get("current_agent", "investigator"))
    context = InvestigationContext.model_validate(context_data)
    limitations = [*state.get("limitations", []), *state.get("errors", [])]
    telemetry = []
    for index, event in enumerate(state.get("telemetry", []), start=1):
        normalized = dict(event)
        normalized["seq"] = index
        telemetry.append(TelemetryEvent.model_validate(normalized))
    return Run(id=state["run_id"], query=state["objective"], status="done" if state.get("completed") else "running", started_at=_now(), telemetry=telemetry, evidence=[Evidence.model_validate(e) for e in state.get("evidence", [])], tool_calls=state.get("tool_calls", []), critiques=[Critique.model_validate(c) for c in state.get("critiques", [])], context=context, prior_memories=context.prior_memories, report=state.get("report"), limitations=limitations, graph_trace=state.get("graph_trace", []), checkpoints=state.get("checkpoints", []), plan=state.get("plan", []), hypotheses=state.get("hypotheses", []), conflicts=state.get("conflicts", []), uncertainty=state.get("uncertainty", "low"), resource_ledger=state.get("resource_ledger", {}), resumed_from=state.get("resumed_from"), adversarial=state.get("adversarial", False))


def run_graph(objective: str, emit_callback: Callable[[TelemetryEvent], None] | None = None, run_id: str | None = None, adversarial: bool = False, resume_from: str | None = None) -> Run:
    run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
    reset_faults()
    graph, saver = build_graph()
    initial: GraphState = {"objective": objective.strip(), "run_id": run_id, "context": {}, "evidence": [], "tool_calls": [], "critiques": [], "hypotheses": [], "verified_hypotheses": [], "rejected_hypotheses": [], "conflicts": [], "limitations": [], "errors": [], "graph_trace": [], "checkpoints": [], "telemetry": [], "worker_results": [], "loop_signatures": [], "no_progress_count": 0, "replan_count": 0, "uncertainty": "low", "adversarial": adversarial or ADVERSARIAL_MODE, "completed": False}
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": GRAPH_RECURSION_LIMIT}
    emitted_events: list[dict[str, Any]] = []
    for _update in graph.stream(initial, config, stream_mode="updates"):
        updates = []
        if isinstance(_update, dict):
            for node_update in _update.values():
                if isinstance(node_update, dict):
                    updates.extend(node_update.get("telemetry", []))
        for event_data in updates:
            if emit_callback:
                try:
                    event_data = dict(event_data)
                    event_data["seq"] = len(emitted_events) + 1
                    emitted_events.append(event_data)
                    emit_callback(TelemetryEvent.model_validate(event_data))
                except Exception:
                    pass
    result = graph.get_state(config).values
    snapshot = graph.get_state(config)
    checkpoints = [str(snapshot.config.get("configurable", {}).get("checkpoint_id", "final"))]
    result["checkpoints"] = checkpoints
    run = _state_to_run(result)
    return run


def resume_graph(run_id: str, emit_callback: Callable[[TelemetryEvent], None] | None = None) -> Run:
    """Resume the latest durable checkpoint for a run id."""
    graph, _ = build_graph()
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": GRAPH_RECURSION_LIMIT}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise ValueError(f"No checkpoint exists for run '{run_id}'")
    result = graph.invoke(None, config)
    result["resumed_from"] = run_id
    run = _state_to_run(result)
    if emit_callback:
        for event_data in result.get("telemetry", []):
            emit_callback(TelemetryEvent.model_validate(event_data))
    return run


def get_checkpoint_state(run_id: str) -> dict[str, Any] | None:
    graph, _ = build_graph()
    snapshot = graph.get_state({"configurable": {"thread_id": run_id}})
    return dict(snapshot.values) if snapshot.values else None


if __name__ == "__main__":
    import sys
    result = run_graph(sys.argv[1] if len(sys.argv) > 1 else "NVIDIA")
    print(f"Graph status: {result.status}; nodes={len(result.graph_trace)}; checkpoints={result.checkpoints}; evidence={len(result.evidence)}")
