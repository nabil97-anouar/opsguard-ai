from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.versions import METRIC_DEFINITIONS_VERSION
from app.harness.schemas import HarnessScenarioResult
from app.models.base import utcnow


class RateMetric(BaseModel):
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    value: float | None
    unit: Literal["rate"] = "rate"
    definition: str


class EvaluationCohort(BaseModel):
    harness_run_id: UUID | None = None
    provenance: Literal["executed", "none"] = "none"
    execution_started_at: datetime | None = None
    execution_completed_at: datetime | None = None
    agent_run_ids: list[UUID] = Field(default_factory=list)
    component_run_ids: list[UUID] = Field(default_factory=list)
    scenario_manifest: list[dict[str, Any]] = Field(default_factory=list)
    expected_case_count: int = 0
    completed_case_count: int = 0
    provider_version: str | None = None
    provider: str | None = None
    model: str | None = None
    reasoning_mode: str | None = None
    reasoning_schema_version: str | None = None
    policy_version: str | None = None


class InvariantFailure(BaseModel):
    scenario_id: str
    invariant: str


class EvaluationSummary(BaseModel):
    schema_version: str = METRIC_DEFINITIONS_VERSION
    report_kind: Literal["stored", "live_preview"] = "live_preview"
    evaluation_run_id: UUID | None = None
    generated_at: datetime = Field(default_factory=utcnow)
    report_type: str = "full"
    cohort: EvaluationCohort = Field(default_factory=EvaluationCohort)
    metrics: dict[str, RateMetric] = Field(default_factory=dict)
    scenario_results: list[HarnessScenarioResult] = Field(default_factory=list)
    agent_run_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    failed_scenarios: list[str] = Field(default_factory=list)
    mandatory_invariant_failures: list[InvariantFailure] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
