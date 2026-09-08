from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rag.trust import TrustLevel
from app.agent.actions import ProposedAction, RecommendationState


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
    evidence_id: str
    observed_at: datetime
    document_id: UUID
    chunk_id: UUID
    title: str
    source: str
    chunk_index: int
    trust_level: TrustLevel
    doc_type: str
    score: float
    content_excerpt: str
    citation: str
    is_suspicious: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    risk_level: str = "low"


class ToolResultItem(BaseModel):
    tool_name: str
    tool_call_id: UUID | None = None
    status: Literal["succeeded", "failed", "blocked"]
    observed_at: datetime
    trust_level: TrustLevel
    requires_human_approval: bool = False
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    is_suspicious: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    risk_level: str = "low"


class EvidenceItem(BaseModel):
    """Run-scoped observation snapshot, independent of current source records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    agent_run_id: UUID | None = None
    observation_status: Literal["valid", "succeeded"] = "valid"
    kind: Literal["alert", "retrieval", "tool_output"]
    source_type: Literal["alert", "document", "tool"]
    alert_id: UUID | None = None
    document_id: UUID | None = None
    chunk_id: UUID | None = None
    tool_call_id: UUID | None = None
    retrieval_score: float | None = Field(default=None, ge=0)
    content: str | dict[str, Any]
    observed_at: datetime
    summary: str
    citation: str
    trust_level: TrustLevel
    suspicious: bool = False
    source: str
    title: str | None = None
    chunk_index: int | None = None
    doc_type: str | None = None
    matched_patterns: list[str] = Field(default_factory=list)
    risk_level: str = "low"

    @model_validator(mode="after")
    def validate_source_identity(self) -> "EvidenceItem":
        if self.kind == "retrieval" and (
            self.source_type != "document" or self.document_id is None or self.chunk_id is None
            or self.retrieval_score is None or not isinstance(self.content, str)
        ):
            raise ValueError("Retrieved evidence requires document/chunk identity, score, and text snapshot.")
        if self.kind == "tool_output" and (
            self.source_type != "tool" or self.tool_call_id is None or not isinstance(self.content, dict)
        ):
            raise ValueError("Tool evidence requires a persisted call ID and structured output snapshot.")
        if self.kind == "alert" and (self.source_type != "alert" or self.alert_id is None):
            raise ValueError("Alert evidence requires an alert ID.")
        if self.observed_at.tzinfo is None:
            raise ValueError("Evidence timestamps must include a timezone.")
        if self.trust_level == TrustLevel.QUARANTINED:
            raise ValueError("Quarantined content cannot be supporting evidence.")
        return self


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
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    lifecycle_state: RecommendationState = RecommendationState.CANDIDATE
    review_valid: bool = False
    policy_version: str | None = None
    watchdog_decision: dict[str, Any] | None = None
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
    watchdog_status: str | None = None
    watchdog_summary: str | None = None
    watchdog_findings: list[dict[str, Any]] = Field(default_factory=list)


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
    missing_targets: list[str] = Field(default_factory=list)
    planned_tools: list[PlannedToolCall] = Field(default_factory=list)
    executed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[BlockedToolRecommendation] = Field(default_factory=list)
    self_assessment: AssessmentSnapshot | None = None
    final_recommendation: FinalRecommendation | None = None
    watchdog_decision: dict[str, Any] | None = None
    requires_human_approval: bool = True
    status: str = "running"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
