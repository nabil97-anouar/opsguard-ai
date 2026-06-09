from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AlertSummary(BaseModel):
    id: UUID
    title: str
    severity: str
    source: str
    infrastructure_type: str
    status: str
    description: str
    raw_data: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class RetrievedContextItem(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    source: str
    chunk_index: int
    trust_level: str
    doc_type: str
    score: float
    content_excerpt: str
    citation: str
    is_suspicious: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    risk_level: str = "low"


class ToolResultItem(BaseModel):
    tool_name: str
    status: str
    trust_level: str
    requires_human_approval: bool = False
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    is_suspicious: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    risk_level: str = "low"


class EvidenceItem(BaseModel):
    evidence_id: str
    kind: str
    summary: str
    citation: str
    trust_level: str
    suspicious: bool = False
    source: str


class PlannedToolCall(BaseModel):
    tool_name: str
    input: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    safe_to_execute: bool = True
    requires_human_approval: bool = False


class BlockedToolRecommendation(BaseModel):
    tool_name: str
    target: str | None = None
    rationale: str
    requires_human_approval: bool = True


class HypothesisItem(BaseModel):
    title: str
    summary: str
    confidence: float
    supporting_evidence: list[str] = Field(default_factory=list)


class AssessmentSnapshot(BaseModel):
    capability_area: str
    confidence_score: float
    uncertainty_level: str
    what_agent_knows: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    within_capability: bool = True
    decision: str
    rationale: str
    risk_flags: list[str] = Field(default_factory=list)
    overridden_by_policy: bool = False


class FinalRecommendation(BaseModel):
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    blocked_actions_requiring_human_approval: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: str
    missing_evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True
    ticket_draft_id: str | None = None


class AgentState(BaseModel):
    alert_id: UUID
    agent_run_id: UUID
    alert_summary: AlertSummary | None = None
    alert_classification: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: list[RetrievedContextItem] = Field(default_factory=list)
    tool_results: list[ToolResultItem] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    suspicious_items: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    hypotheses: list[HypothesisItem] = Field(default_factory=list)
    planned_tools: list[PlannedToolCall] = Field(default_factory=list)
    executed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[BlockedToolRecommendation] = Field(default_factory=list)
    self_assessment: AssessmentSnapshot | None = None
    final_recommendation: FinalRecommendation | None = None
    requires_human_approval: bool = True
    status: str = "running"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
