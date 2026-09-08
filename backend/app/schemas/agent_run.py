from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel
from app.schemas.tools import ToolCallRead


class ExecutionProvenance(SchemaModel):
    provenance: str = "legacy_unknown"
    execution_kind: str = "unknown"
    provider_version: str | None = None
    policy_version: str | None = None


class AgentRunBase(ExecutionProvenance):
    alert_id: UUID
    status: str
    llm_provider: str
    model_version: str | None = None
    total_steps: int = 0
    total_tool_calls: int = 0
    total_tokens_used: int | None = None
    evidence_grounding_score: float | None = None
    risk_level: str
    approval_status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    is_demo: bool = False


class AgentRunRead(AgentRunBase, IDSchema):
    pass


class AgentStepBase(SchemaModel):
    agent_run_id: UUID
    step_index: int
    node_name: str
    status: str
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    error: str | None = None


class AgentStepRead(AgentStepBase, IDSchema, CreatedAtSchema):
    pass


class AgentRunCreateRequest(SchemaModel):
    alert_id: UUID


class AgentAssessmentResponse(SchemaModel):
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


from app.agent.actions import ProposedAction, RecommendationState


class FinalRecommendationResponse(SchemaModel):
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


class AgentStepResponse(SchemaModel):
    id: UUID
    step_index: int
    node_name: str
    status: str
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    error: str | None = None
    created_at: datetime


class AgentRunResponse(ExecutionProvenance):
    status: Literal["waiting_for_human", "failed"]
    agent_run_id: UUID
    alert_id: UUID
    steps: list[AgentStepResponse] = Field(default_factory=list)
    self_assessment: AgentAssessmentResponse | None = None
    final_recommendation: FinalRecommendationResponse | None = None


class AgentRunDetailResponse(ExecutionProvenance):
    agent_run_id: UUID
    alert_id: UUID
    status: str
    llm_provider: str
    model_version: str | None = None
    risk_level: str
    approval_status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    steps: list[AgentStepResponse] = Field(default_factory=list)
    tool_calls: list[ToolCallRead] = Field(default_factory=list)
    tool_attempts: list[dict[str, Any]] = Field(default_factory=list)
    self_assessment: AgentAssessmentResponse | None = None
    final_recommendation: FinalRecommendationResponse | None = None


class AgentRunListItem(ExecutionProvenance):
    agent_run_id: UUID
    alert_id: UUID
    status: str
    risk_level: str
    approval_status: str
    started_at: datetime
    completed_at: datetime | None = None


class AgentRunListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[AgentRunListItem] = Field(default_factory=list)
