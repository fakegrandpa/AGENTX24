import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable
from google.genai import types

from app.config import (
    GEMINI_API_KEY,
    MAX_ITERATIONS,
    MAX_TOOL_CALLS,
    WALL_CLOCK,
)
from app.llm import LLMResponse, propose_next_step, resolve_model
from app.models import Evidence, PhaseEnum, Run, TelemetryEvent
from app.report import assemble_report
from app.tools import execute_tool, extract_reason, get_advertised_tools
from app.tools.patents import is_patent_tool_available

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tool_to_phase(tool_name: str) -> PhaseEnum:
    if tool_name == "news_search":
        return PhaseEnum.CHECKING_NEWS
    elif tool_name == "research_search":
        return PhaseEnum.SEARCHING_RESEARCH
    elif tool_name == "web_search":
        return PhaseEnum.SEARCHING_WEB
    elif tool_name == "patent_search":
        return PhaseEnum.SEARCHING_PATENTS
    return PhaseEnum.PLANNING_NEXT_STEP


def _tool_to_provider_kind(tool_name: str) -> str:
    if tool_name == "research_search":
        return "research"
    if tool_name == "web_search":
        return "web"
    if tool_name == "patent_search":
        return "patent"
    return "news"


def run_investigation(
    objective: str,
    emit_callback: Callable[[TelemetryEvent], None] | None = None,
) -> Run:
    """Executes the autonomous investigation loop for a given objective.
    This function is trigger-agnostic (can be called from HTTP route, CLI, or scheduler).
    """
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    started_at = _iso_now()
    seq_counter = 0

    run = Run(
        id=run_id,
        query=objective.strip(),
        status="running",
        started_at=started_at,
        telemetry=[],
        evidence=[],
        tool_calls=[],
        report=None,
        limitations=[],
    )

    def emit(phase: PhaseEnum, kind: str, text: str, detail: str | None = None, data: dict[str, Any] | None = None) -> None:
        nonlocal seq_counter
        seq_counter += 1
        event = TelemetryEvent(
            seq=seq_counter,
            ts=_iso_now(),
            phase=phase,
            kind=kind,  # type: ignore
            text=text,
            detail=detail,
            data=data,
        )
        run.telemetry.append(event)
        if emit_callback:
            try:
                emit_callback(event)
            except Exception:
                pass

    # Check model preflight
    model_name, is_ready, preflight_msg = resolve_model()
    if not is_ready:
        run.status = "error"
        run.limitations.append(f"Model preflight failed: {preflight_msg}")
        emit(
            phase=PhaseEnum.ERROR,
            kind="error",
            text="Unable to start investigation",
            detail=preflight_msg,
        )
        run.finished_at = _iso_now()
        return run

    emit(
        phase=PhaseEnum.UNDERSTANDING_OBJECTIVE,
        kind="objective",
        text=f"Target: {objective}",
        detail=f"Investigating {objective} across news, research, and web signals",
        data={
            "objective": objective,
            "available_tools": [t["name"] for t in get_advertised_tools()],
        },
    )

    # Prepare conversation history for Gemini
    advertised_tools = get_advertised_tools()
    history: list[Any] = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"Please investigate the following target: '{objective}'. "
                    "Autonomously select appropriate tools step by step to gather news, academic research, and web evidence. "
                    "Analyze the findings and provide a prioritized intelligence report citing evidence IDs [E1], [E2], etc. "
                    "Structure your final report with: INVESTIGATION SUMMARY, HIGH PRIORITY SIGNALS, "
                    "KEY RESEARCH DEVELOPMENTS, COMPETITOR / INDUSTRY ACTIVITY, RECENT DEVELOPMENTS, "
                    "EMERGING / WATCH SIGNALS, WHY THIS MATTERS, and RECOMMENDED NEXT ACTIONS."
                )
            ],
        )
    ]

    evidence_counter = 0
    start_time = time.time()
    iterations = 0
    total_tool_calls = 0
    final_synthesis_text = ""

    while iterations < MAX_ITERATIONS and total_tool_calls < MAX_TOOL_CALLS:
        elapsed = time.time() - start_time
        if elapsed >= WALL_CLOCK:
            run.limitations.append(f"Investigation hit wall clock limit ({WALL_CLOCK}s).")
            break

        iterations += 1
        emit(
            phase=PhaseEnum.PLANNING_NEXT_STEP,
            kind="planning",
            text=f"Analyzing gathered findings (Step {iterations})",
            detail=None,
            data={"step": iterations},
        )

        try:
            response: LLMResponse = propose_next_step(contents=history, tools_schema=advertised_tools)
        except Exception as e:
            run.limitations.append(f"LLM turn failed: {e}")
            emit(
                phase=PhaseEnum.ERROR,
                kind="error",
                text="Reasoning step error",
                detail=str(e),
            )
            break

        # If Gemini returned raw content, add model turn to history
        if response.raw_content:
            history.append(response.raw_content)
        elif response.text:
            history.append(types.Content(role="model", parts=[types.Part.from_text(text=response.text)]))

        # Check if model made tool calls
        if not response.tool_calls:
            # Model decided to deliver final report
            final_synthesis_text = response.text
            break

        # Process tool calls
        function_response_parts: list[Any] = []
        for call in response.tool_calls:
            if total_tool_calls >= MAX_TOOL_CALLS:
                run.limitations.append("Maximum tool call budget reached.")
                break

            total_tool_calls += 1
            tool_phase = _tool_to_phase(call.name)
            arg_preview = call.args.get("query", "")
            call_detail = f"{call.name}(\"{arg_preview}\")" if arg_preview else f"{call.name}()"
            # The agent's own justification for this call, supplied as a declared tool
            # argument. Never invented here: if the model omitted it, it stays None.
            reason = extract_reason(call.args)

            # A follow-up tool call made while evidence already exists IS the agent
            # acting on a knowledge gap. Surfaced using the model's own reason only.
            if run.evidence and iterations > 1:
                emit(
                    phase=PhaseEnum.IDENTIFYING_GAPS,
                    kind="planning",
                    text="Additional evidence required",
                    detail=reason,
                    data={"step": iterations, "next_tool": call.name, "reason": reason},
                )

            emit(
                phase=tool_phase,
                kind="tool_selected",
                text=f"Selected {call.name}",
                detail=call_detail,
                data={
                    "tool": call.name,
                    "args": call.args,
                    "query": arg_preview,
                    "reason": reason,
                    "call_index": total_tool_calls,
                },
            )

            call_start = time.time()
            result_data = execute_tool(call.name, call.args)
            call_ms = int((time.time() - call_start) * 1000)

            is_ok = "error" not in result_data
            run.tool_calls.append({
                "name": call.name,
                "args": call.args,
                "reason": reason,
                "ok": is_ok,
                "ms": call_ms,
            })

            # Process evidence items if returned
            results_list = result_data.get("results", [])
            new_evidence_count = 0
            if results_list and isinstance(results_list, list):
                for item in results_list:
                    evidence_counter += 1
                    ev_id = f"E{evidence_counter}"
                    evidence_obj = Evidence(
                        id=ev_id,
                        tool=call.name,
                        provider=item.get("provider", call.name),
                        provider_kind=item.get("provider_kind", _tool_to_provider_kind(call.name)),
                        source=item.get("source", "Unknown"),
                        title=item.get("title", "Untitled"),
                        url=item.get("url", ""),
                        published=item.get("published"),
                        days_old=item.get("days_old"),
                        authors=item.get("authors", []),
                        snippet=item.get("snippet", ""),
                        corroboration=0,
                        meta=item.get("meta", {}),
                    )
                    run.evidence.append(evidence_obj)
                    new_evidence_count += 1

                emit(
                    phase=PhaseEnum.EVIDENCE_FOUND,
                    kind="tool_result",
                    text=f"Evidence gathered from {call.name}",
                    detail=f"{new_evidence_count} results · {len(run.evidence)} total sources",
                    data={
                        "tool": call.name,
                        "new_evidence": new_evidence_count,
                        "total_evidence": len(run.evidence),
                        "ok": True,
                    },
                )
            elif not is_ok:
                err_detail = result_data.get("detail") or result_data.get("message") or "Tool unavailable"
                run.limitations.append(f"{call.name}: {err_detail}")
                emit(
                    phase=PhaseEnum.SOURCE_UNAVAILABLE,
                    kind="note",
                    text=f"{call.name} unavailable",
                    detail=err_detail,
                    data={
                        "tool": call.name,
                        "ok": False,
                        "error": result_data.get("error"),
                        "new_evidence": 0,
                    },
                )
            else:
                emit(
                    phase=PhaseEnum.NO_RESULTS,
                    kind="note",
                    text=f"No results for '{arg_preview}'",
                    detail="0 results returned",
                    data={"tool": call.name, "ok": True, "new_evidence": 0},
                )

            # Feed result into conversation
            # Replace actual result objects with Evidence IDs in tool response so LLM can cite accurately
            tool_response_payload = {
                "status": "success" if is_ok else "error",
                "results": [
                    {
                        "id": f"E{evidence_counter - new_evidence_count + i + 1}",
                        "title": r.get("title"),
                        "source": r.get("source"),
                        "published": r.get("published"),
                        "snippet": r.get("snippet"),
                        "url": r.get("url"),
                    }
                    for i, r in enumerate(results_list)
                ] if is_ok else [],
                "error": result_data.get("error") if not is_ok else None,
                "detail": result_data.get("detail") if not is_ok else None,
            }

            resp_part = types.Part.from_function_response(
                name=call.name,
                response={"response": tool_response_payload},
            )
            function_response_parts.append(resp_part)

        if function_response_parts:
            history.append(types.Content(role="user", parts=function_response_parts))

    # If loop ended without synthesis (e.g. reached max steps), perform forced final synthesis
    synthesis_from_model = bool(final_synthesis_text)
    if not final_synthesis_text:
        emit(
            phase=PhaseEnum.COMPARING_EVIDENCE,
            kind="planning",
            text="Comparing and prioritizing gathered signals",
            detail=f"Synthesizing report from {len(run.evidence)} evidence sources",
            data={"evidence": len(run.evidence)},
        )
        synthesis_prompt = (
            f"Investigation budget reached. Now synthesize your final intelligence report for '{objective}' "
            f"using only the {len(run.evidence)} gathered evidence sources. "
            "Cite all claims with [E1], [E2] etc. Prioritize into HIGH PRIORITY, IMPORTANT, and EMERGING tiers."
        )
        history.append(types.Content(role="user", parts=[types.Part.from_text(text=synthesis_prompt)]))
        try:
            synth_resp = propose_next_step(contents=history, tools_schema=None)
            final_synthesis_text = synth_resp.text
            synthesis_from_model = bool(final_synthesis_text)
        except Exception as e:
            run.limitations.append(f"Forced synthesis fallback error: {e}")
            final_synthesis_text = ""
            synthesis_from_model = False

    emit(
        phase=PhaseEnum.GENERATING_REPORT,
        kind="final",
        text="Generating prioritized intelligence report",
        detail="Structuring actionable findings, validating citations, and rendering sources",
    )

    if not synthesis_from_model:
        run.limitations.append(
            "The reasoning model did not return a final synthesis for this run; "
            "only the verified evidence below is trustworthy."
        )

    # Assemble structured report
    report = assemble_report(
        target=objective,
        raw_synthesis_text=final_synthesis_text,
        evidence_list=run.evidence,
        tool_calls=run.tool_calls,
        runtime_limitations=run.limitations,
        has_patents=is_patent_tool_available(),
    )
    run.report = report
    # A run that produced neither evidence nor model synthesis is a failure, not a success
    run.status = "done" if (run.evidence or synthesis_from_model) else "error"
    run.finished_at = _iso_now()

    emit(
        phase=PhaseEnum.COMPLETED,
        kind="final",
        text="Intelligence report ready",
        detail=f"{len(run.tool_calls)} tool calls · {len(run.evidence)} sources · {len(report.signals)} prioritized signals",
        data={
            "tool_calls": len(run.tool_calls),
            "evidence": len(run.evidence),
            "tools_used": sorted({tc["name"] for tc in run.tool_calls}),
            "signals": len(report.signals),
        },
    )

    return run


if __name__ == "__main__":
    test_target = sys.argv[1] if len(sys.argv) > 1 else "NVIDIA"
    print(f"=== Running AGENTX24 Autonomous Investigation CLI: '{test_target}' ===")

    def cli_telemetry_printer(ev: TelemetryEvent) -> None:
        det = f" -> {ev.detail}" if ev.detail else ""
        print(f"[{ev.seq:02d} | {ev.phase.value}] {ev.text}{det}")

    result_run = run_investigation(test_target, emit_callback=cli_telemetry_printer)

    print("\n=======================================================")
    print(f"Run ID     : {result_run.id}")
    print(f"Status     : {result_run.status}")
    print(f"Tool Calls : {len(result_run.tool_calls)}")
    print(f"Evidence   : {len(result_run.evidence)} items")
    if result_run.report:
        print(f"\n--- SUMMARY ---\n{result_run.report.summary}")
        print(f"\n--- SIGNALS ({len(result_run.report.signals)}) ---")
        for s in result_run.report.signals:
            cits = " ".join([f"[{c}]" for c in s.citations]) if s.citations else ""
            print(f"[{s.tier.upper()}] {s.headline} {cits}\n   {s.detail}")
        print("\n--- COVERAGE ---")
        for c in result_run.report.coverage:
            print(f" * {c}")
        if result_run.report.limitations:
            print("\n--- LIMITATIONS ---")
            for lim in result_run.report.limitations:
                print(f" ! {lim}")
    print("=======================================================")
