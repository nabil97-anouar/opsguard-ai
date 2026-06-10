from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioResultStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"


class HarnessScenarioDefinition(BaseModel):
    scenario_id: str
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
    status: Literal["completed"]
    harness_run_id: UUID
    total: int
    passed: int
    failed: int
    partial: int
    results: list[HarnessScenarioResult] = Field(default_factory=list)
