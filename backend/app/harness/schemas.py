from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioResultStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"  # Read-only compatibility for historical fixtures; new executions are binary.


class ScenarioExpectations(BaseModel):
    expected_tool_calls: list[str] = Field(default_factory=list)
    forbidden_tool_calls: list[str] = Field(default_factory=list)
    expected_target: dict[str, str] = Field(default_factory=dict)
    forbidden_side_effects: list[str] = Field(default_factory=lambda: ["destructive_handler_invocation", "unauthorized_execution"])
    expected_watchdog_outcomes: list[str] = Field(default_factory=list)
    expected_review_requirement: bool | None = None
    required_evidence_conditions: list[str] = Field(default_factory=list)
    forbidden_recommendation_patterns: list[str] = Field(default_factory=list)


class HarnessScenarioDefinition(BaseModel):
    scenario_id: str
    scenario_version: str = "3.0"
    test_level: Literal["end_to_end", "component", "policy", "tool_boundary", "legacy_unknown"] = "legacy_unknown"
    expectations: ScenarioExpectations = Field(default_factory=ScenarioExpectations)
    name: str
    category: str
    description: str
    attack_type: str
    expected_behavior: str
    severity: str
    injection_point: str
    input_config: dict[str, Any] = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)


class HarnessScenarioResult(BaseModel):
    scenario_id: str
    scenario_version: str = "legacy_unknown"
    test_level: str = "legacy_unknown"
    provenance: Literal["executed", "fixture", "legacy_unknown"] = "legacy_unknown"
    expectations: dict[str, Any] = Field(default_factory=dict)
    mandatory_invariants: dict[str, bool] = Field(default_factory=dict)
    invariant_failures: list[str] = Field(default_factory=list)
    observations: dict[str, Any] = Field(default_factory=dict)
    human_review_required: bool | None = None
    human_review_reached: bool | None = None
    terminal_status: str | None = None
    name: str
    category: str
    status: ScenarioResultStatus
    score: float
    observed_behavior: str
    expected_behavior: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    safety_events: list[dict[str, Any]] = Field(default_factory=list)
    agent_run_id: UUID | None = None
    tool_call_ids: list[UUID] = Field(default_factory=list)
    watchdog_status: str | None = None
    failure_reason: str | None = None
    injection_detected: bool = False
    action_blocked: bool = False
    harness_run_id: UUID | None = None
    harness_result_id: UUID | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessRunResult(BaseModel):
    status: Literal["running", "completed", "failed", "not_executed", "legacy_unknown"]
    harness_run_id: UUID
    provenance: str = "legacy_unknown"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expected_case_count: int | None = None
    completed_case_count: int = 0
    provider_version: str | None = None
    policy_version: str | None = None
    scenario_manifest: list[dict[str, Any]] = Field(default_factory=list)
    total: int
    passed: int
    failed: int
    partial: int
    results: list[HarnessScenarioResult] = Field(default_factory=list)
