from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    INVESTIGATOR = "investigator"
    CRITIC = "critic"
    SYNTHESIST = "synthesist"


class PhaseEnum(str, Enum):
    UNDERSTANDING_OBJECTIVE = "Understanding the objective"
    PLANNING_NEXT_STEP = "Planning the next step"
    SEARCHING_RESEARCH = "Searching recent research"
    CHECKING_NEWS = "Checking recent industry developments"
    SEARCHING_WEB = "Searching the web"
    SEARCHING_PATENTS = "Searching patent records"
    IDENTIFYING_GAPS = "Identifying knowledge gaps"
    CRITIC_REVIEWING = "Reviewing evidence sufficiency"
    CRITIQUE_RETURNED = "Critique returned"
    SYNTHESIST_COMPOSING = "Composing intelligence report"
    PRIOR_CONTEXT_FOUND = "Relevant prior context retrieved"
    CONTEXT_UPDATED = "Investigation context updated"
    MEMORY_SAVED = "Investigation saved to memory"
    EVIDENCE_FOUND = "Evidence found"
    NO_RESULTS = "No results for that angle"
    SOURCE_UNAVAILABLE = "Source unavailable"
    COMPARING_EVIDENCE = "Comparing and prioritising evidence"
    GENERATING_REPORT = "Generating intelligence report"
    COMPLETED = "Completed"
    ERROR = "Error encountered"


class Critique(BaseModel):
    seq: int
    sufficient: bool
    gaps: list[str] = Field(default_factory=list)
    recommended_tool: str | None = None
    recommended_query: str | None = None
    confidence: float | None = None
    note: str | None = None


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
    agent: AgentRole = AgentRole.INVESTIGATOR
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


class MemoryRecord(BaseModel):
    memory_id: str
    created_at: str
    objective: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    entities_or_keywords: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    signal_count: int = 0


class InvestigationContext(BaseModel):
    run_id: str
    objective: str
    normalized_objective: str = ""
    phase: str = ""
    active_agent: AgentRole = AgentRole.INVESTIGATOR
    tool_history: list[dict[str, Any]] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    critic_feedback: list[dict[str, Any]] = Field(default_factory=list)
    critique_count: int = 0
    prior_memories: list[MemoryRecord] = Field(default_factory=list)
    updated_at: str = ""


class Run(BaseModel):
    id: str
    query: str
    status: Literal["running", "done", "error"]
    started_at: str
    finished_at: str | None = None
    telemetry: list[TelemetryEvent] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    critiques: list[Critique] = Field(default_factory=list)
    context: InvestigationContext | None = None
    prior_memories: list[MemoryRecord] = Field(default_factory=list)
    report: Report | None = None
    limitations: list[str] = Field(default_factory=list)
