from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.evaluation.schemas import (
    AgentQualityMetrics,
    EvaluationScorecard,
    EvaluationSummary,
    GroundingEvidenceMetrics,
    HarnessPerformanceMetrics,
    HumanApprovalEnforcementMetrics,
    NotableSafetyEvent,
    PromptInjectionResistanceMetrics,
    ToolSafetyMetrics,
    WatchdogCoverageMetrics,
)
from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class EvaluationScoreBase(SchemaModel):
    agent_run_id: UUID
    report_type: str = "full"
    evidence_grounding: float = 0.0
    correctness: float = 0.0
    non_speculativeness: float = 0.0
    incident_focus: float = 0.0
    actionability: float = 0.0
    safety_score: float = 0.0
    response_time_seconds: float = 0.0
    safety_violations_blocked: int = 0
    prompt_injection_resistance: float = 0.0
    tool_misuse_resistance: float = 0.0
    uncertainty_calibration: float = 0.0
    human_approval_usefulness: float | None = None
    overall_score: float = 0.0
    summary_payload: dict[str, Any] = Field(default_factory=dict)


class EvaluationScoreRead(EvaluationScoreBase, IDSchema, CreatedAtSchema):
    pass


class EvaluationSummaryResponse(EvaluationSummary):
    pass


class EvaluationRunRequest(SchemaModel):
    run_harness_if_empty: bool = True
    report_type: str = "full"


class EvaluationRunResponse(SchemaModel):
    status: Literal["ok"]
    persisted: bool = True
    evaluation_score_id: UUID | None = None
    summary: EvaluationSummaryResponse
    scorecard: EvaluationScorecard


class EvaluationMetricsBundle(SchemaModel):
    harness_performance: HarnessPerformanceMetrics
    watchdog_coverage: WatchdogCoverageMetrics
    prompt_injection_resistance: PromptInjectionResistanceMetrics
    tool_safety: ToolSafetyMetrics
    agent_quality: AgentQualityMetrics
    grounding_evidence: GroundingEvidenceMetrics
    human_approval_enforcement: HumanApprovalEnforcementMetrics


class EvaluationReportResponse(SchemaModel):
    title: str
    generated_at: datetime
    report_type: str
    executive_summary: str
    scorecard: EvaluationScorecard
    metrics: EvaluationMetricsBundle
    latest_agent_run_id: UUID | None = None
    latest_harness_run_id: UUID | None = None
    notable_safety_events: list[NotableSafetyEvent] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str


class EvaluationScoreResponse(EvaluationScoreRead):
    pass


class EvaluationScoreListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[EvaluationScoreResponse] = Field(default_factory=list)
