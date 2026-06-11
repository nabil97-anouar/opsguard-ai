from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.base import utcnow


class HarnessPerformanceMetrics(BaseModel):
    total_scenarios: int = 0
    passed: int = 0
    partial: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0
    latest_harness_run_id: UUID | None = None


class WatchdogCoverageMetrics(BaseModel):
    total_watchdog_events: int = 0
    policy_ids_triggered: list[str] = Field(default_factory=list)
    critical_findings: int = 0
    high_findings: int = 0
    warning_findings: int = 0
    block_decisions: int = 0
    require_human_approval_decisions: int = 0


class PromptInjectionResistanceMetrics(BaseModel):
    prompt_injection_events: int = 0
    unsafe_tool_output_events: int = 0
    suspicious_retrieval_events: int = 0
    prompt_injection_scenarios_passed: int = 0
    prompt_injection_scenarios_total: int = 0


class ToolSafetyMetrics(BaseModel):
    total_tool_calls: int = 0
    blocked_tool_calls: int = 0
    failed_tool_calls: int = 0
    flagged_tool_outputs: int = 0
    dangerous_tool_attempts: int = 0
    arbitrary_shell_execution_present: bool = False


class AgentQualityMetrics(BaseModel):
    total_agent_runs: int = 0
    waiting_for_human_runs: int = 0
    failed_runs: int = 0
    average_confidence: float = 0.0
    low_confidence_high_severity_count: int = 0
    runs_with_self_assessment: int = 0
    runs_with_ticket_draft: int = 0


class GroundingEvidenceMetrics(BaseModel):
    runs_with_citations: int = 0
    runs_missing_citations: int = 0
    weak_grounding_events: int = 0
    untrusted_context_events: int = 0


class HumanApprovalEnforcementMetrics(BaseModel):
    runs_requiring_human_approval: int = 0
    dangerous_recommendations_requiring_human_approval: int = 0
    auto_executed_dangerous_actions: int = 0


class EvaluationScorecard(BaseModel):
    safety_score: float = 0.0
    grounding_score: float = 0.0
    tool_safety_score: float = 0.0
    watchdog_score: float = 0.0
    overall_score: float = 0.0


class NotableSafetyEvent(BaseModel):
    id: UUID
    event_type: str
    severity: str
    source: str
    affected_component: str | None = None
    pattern_matched: str | None = None
    created_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummary(BaseModel):
    generated_at: datetime = Field(default_factory=utcnow)
    report_type: str = "full"
    latest_agent_run_id: UUID | None = None
    latest_harness_run_id: UUID | None = None
    harness_performance: HarnessPerformanceMetrics = Field(default_factory=HarnessPerformanceMetrics)
    watchdog_coverage: WatchdogCoverageMetrics = Field(default_factory=WatchdogCoverageMetrics)
    prompt_injection_resistance: PromptInjectionResistanceMetrics = Field(
        default_factory=PromptInjectionResistanceMetrics
    )
    tool_safety: ToolSafetyMetrics = Field(default_factory=ToolSafetyMetrics)
    agent_quality: AgentQualityMetrics = Field(default_factory=AgentQualityMetrics)
    grounding_evidence: GroundingEvidenceMetrics = Field(default_factory=GroundingEvidenceMetrics)
    human_approval_enforcement: HumanApprovalEnforcementMetrics = Field(
        default_factory=HumanApprovalEnforcementMetrics
    )
    scorecard: EvaluationScorecard = Field(default_factory=EvaluationScorecard)
    notable_safety_events: list[NotableSafetyEvent] = Field(default_factory=list)
    executive_summary: str = ""
    limitations: list[str] = Field(default_factory=list)

