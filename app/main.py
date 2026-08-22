import os
import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.agent import run_investigation
from app.agents import AGENT_ROSTER
from app.config import ENABLE_CRITIC, ENABLE_MEMORY, GEMINI_API_KEY, GEMINI_MODEL, get_enabled_providers
from app.llm import resolve_model
from app.memory import load_all_memories
from app.models import Run, TelemetryEvent
from app.store import (
    broadcast_event,
    close_stream,
    create_run,
    get_run,
    subscribe,
    unsubscribe,
    _RUNS,
)
from app.tools import get_advertised_tools

# AGENTX24 FastAPI Application Server - Reloaded
ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"

app = FastAPI(
    title="AGENTX24 Research & Competitor Tracking Agent",
    description="Autonomous AI Agent for real-time competitor tracking, academic research gathering, and intelligence synthesis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvestigateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Target company, competitor, research topic, or industry")


def _execute_investigation_background(run_id: str, query: str) -> None:
    """Background task executor for an investigation run."""
    def on_event(event: TelemetryEvent) -> None:
        broadcast_event(run_id, event)

    try:
        final_run = run_investigation(objective=query, emit_callback=on_event)
        # Update run in store with final state
        _RUNS[run_id] = final_run
    except Exception as e:
        run = get_run(run_id)
        if run:
            run.status = "error"
            run.limitations.append(f"Fatal background execution failure: {e}")
    finally:
        close_stream(run_id)


@app.get("/api/health")
def api_health() -> dict:
    """Health check endpoint providing model status and enabled information tools."""
    model_name, is_ready, msg = resolve_model()
    advertised = [t["name"] for t in get_advertised_tools()]
    return {
        "status": "ok" if is_ready else "degraded",
        "gemini_model": model_name,
        "gemini_ready": is_ready,
        "gemini_status_message": msg,
        "has_api_key": bool(os.getenv("GEMINI_API_KEY", "").strip() or GEMINI_API_KEY),
        "advertised_tools": advertised,
        "providers": get_enabled_providers(),
        "agents": [AGENT_ROSTER[k] for k in ("investigator", "critic", "synthesist")],
        "critic_enabled": ENABLE_CRITIC,
        "memory_enabled": ENABLE_MEMORY,
        "memory_records_count": len(load_all_memories()),
    }


@app.post("/api/investigate")
def api_investigate(req: InvestigateRequest, background_tasks: BackgroundTasks) -> dict:
    """Initiates an autonomous investigation run for the given target."""
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    run = create_run(clean_query)
    background_tasks.add_task(_execute_investigation_background, run.id, clean_query)
    return {"run_id": run.id, "query": run.query, "status": "running"}


@app.get("/api/stream/{run_id}")
async def api_stream(run_id: str) -> StreamingResponse:
    """Server-Sent Events (SSE) live telemetry stream for a run."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    async def event_generator() -> AsyncGenerator[str, None]:
        q = subscribe(run_id)
        try:
            # Replay any telemetry events already recorded for this run
            for ev in list(run.telemetry):
                yield f"data: {ev.model_dump_json()}\n\n"

            if run.status in ("done", "error"):
                yield "data: {\"event\": \"stream_end\"}\n\n"
                return

            while True:
                # Wait for next event or stream termination
                event = await q.get()
                if event is None:
                    # Stream finished
                    yield "data: {\"event\": \"stream_end\"}\n\n"
                    break
                yield f"data: {event.model_dump_json()}\n\n"
        finally:
            unsubscribe(run_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/run/{run_id}")
def api_get_run(run_id: str) -> Run:
    """Fetches the full Run record including telemetry, evidence, tool calls, and final report."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run


# Static files serving for the Single-Page Judge Dashboard
@app.get("/")
def serve_index() -> FileResponse:
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(index_file)


@app.get("/app.css")
def serve_css() -> FileResponse:
    css_file = WEB_DIR / "app.css"
    if not css_file.exists():
        raise HTTPException(status_code=404, detail="app.css not found.")
    return FileResponse(css_file, media_type="text/css")


@app.get("/app.js")
def serve_js() -> FileResponse:
    js_file = WEB_DIR / "app.js"
    if not js_file.exists():
        raise HTTPException(status_code=404, detail="app.js not found.")
    return FileResponse(js_file, media_type="application/javascript")
