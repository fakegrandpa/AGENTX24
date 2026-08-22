import asyncio
import uuid
from datetime import datetime, timezone
from app.models import Run, TelemetryEvent

# In-memory runs store
_RUNS: dict[str, Run] = {}
_QUEUES: dict[str, list[asyncio.Queue[TelemetryEvent | None]]] = {}


def create_run(query: str) -> Run:
    """Creates a new Run entry in the store."""
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    started_at = datetime.now(timezone.utc).isoformat()
    run = Run(
        id=run_id,
        query=query.strip(),
        status="running",
        started_at=started_at,
        telemetry=[],
        evidence=[],
        tool_calls=[],
        report=None,
        limitations=[],
    )
    _RUNS[run_id] = run
    _QUEUES[run_id] = []
    return run


def get_run(run_id: str) -> Run | None:
    """Retrieves a run by ID."""
    return _RUNS.get(run_id)


def subscribe(run_id: str) -> asyncio.Queue[TelemetryEvent | None]:
    """Subscribes an SSE listener queue to the given run."""
    q: asyncio.Queue[TelemetryEvent | None] = asyncio.Queue()
    if run_id not in _QUEUES:
        _QUEUES[run_id] = []
    _QUEUES[run_id].append(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue[TelemetryEvent | None]) -> None:
    """Removes an SSE listener queue."""
    if run_id in _QUEUES and q in _QUEUES[run_id]:
        _QUEUES[run_id].remove(q)


def broadcast_event(run_id: str, event: TelemetryEvent) -> None:
    """Broadcasts a telemetry event to all active SSE queues for this run."""
    if run_id in _QUEUES:
        for q in list(_QUEUES[run_id]):
            try:
                q.put_nowait(event)
            except Exception:
                pass


def close_stream(run_id: str) -> None:
    """Signals all SSE listeners for this run that the stream is finished."""
    if run_id in _QUEUES:
        for q in list(_QUEUES[run_id]):
            try:
                q.put_nowait(None)
            except Exception:
                pass
