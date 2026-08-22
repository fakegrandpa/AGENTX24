from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class PhaseEnum(str, Enum):
    UNDERSTANDING_OBJECTIVE = "Understanding the objective"
    PLANNING_NEXT_STEP = "Planning the next step"
    SEARCHING_RESEARCH = "Searching recent research"
    CHECKING_NEWS = "Checking recent industry developments"
    SEARCHING_WEB = "Searching the web"
    SEARCHING_PATENTS = "Searching patent records"
    EVIDENCE_FOUND = "Evidence found"
    NO_RESULTS = "No results for that angle"
    SOURCE_UNAVAILABLE = "Source unavailable"
    COMPARING_EVIDENCE = "Comparing and prioritising evidence"
    GENERATING_REPORT = "Generating intelligence report"
    COMPLETED = "Completed"
    ERROR = "Error encountered"


class Evidence(BaseModel):
    id: str  # E1, E2, ...
    tool: str  # news_search, research_search, web_search, patent_search
    provider: str  # google_news, openalex, arxiv, ddgs, wikipedia, etc.
    provider_kind: Literal["research", "news", "web", "patent"]
    source: str  # Domain or publisher name
    title: str
    url: str
    published: str | None = None  # ISO date YYYY-MM-DD
    days_old: int | None = None
    authors: list[str] = Field(default_factory=list)
    snippet: str = ""
    corroboration: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class TelemetryEvent(BaseModel):
    seq: int
    ts: str  # ISO8601 timestamp
    phase: PhaseEnum
    kind: Literal["objective", "planning", "tool_selected", "tool_result", "note", "error", "final"]
    text: str
    detail: str | None = None
    data: dict[str, Any] | None = None


class Signal(BaseModel):
    tier: Literal["high", "important", "emerging"]
    headline: str
    detail: str
    citations: list[str] = Field(default_factory=list)  # e.g. ["E1", "E3"]


class ReportSections(BaseModel):
    research: str | None = None
    competitor_industry: str | None = None
    recent_developments: str | None = None
    patents: str | None = None
    why_it_matters: str | None = None


class Report(BaseModel):
    target: str
    summary: str
    signals: list[Signal] = Field(default_factory=list)
    sections: ReportSections = Field(default_factory=ReportSections)
    next_actions: list[str] = Field(default_factory=list)
    coverage: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Run(BaseModel):
    id: str
    query: str
    status: Literal["running", "done", "error"]
    started_at: str
    finished_at: str | None = None
    telemetry: list[TelemetryEvent] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    report: Report | None = None
    limitations: list[str] = Field(default_factory=list)
