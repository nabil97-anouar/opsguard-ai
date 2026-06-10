from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field
from typing import Literal

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class SecurityHarnessTestBase(SchemaModel):
    test_id: str
    category: str
    name: str
    description: str
    injection_point: str
    attack_payload: dict[str, Any] = Field(default_factory=dict)
    expected_behavior: str
    detection_logic: str
    max_score: int = 10
    weight: float = 1.0
    active: bool = True


class SecurityHarnessTestRead(SecurityHarnessTestBase, IDSchema):
    pass


class SecurityHarnessResultBase(SchemaModel):
    harness_run_id: UUID
    test_id: UUID
    score: int = 0
    max_score: int = 10
    passed: bool = False
    actual_behavior: str
    injection_detected: bool = False
    action_blocked: bool = False
    safety_event_id: UUID | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SecurityHarnessResultRead(SecurityHarnessResultBase, IDSchema, CreatedAtSchema):
    pass


class HarnessRunRequest(SchemaModel):
    scenario_ids: list[str] | None = None
    reset_demo_data: bool = True


class HarnessScenarioResponse(SchemaModel):
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


class HarnessResultResponse(SchemaModel):
    scenario_id: str
    name: str
    category: str
    status: Literal["passed", "failed", "partial"]
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


class HarnessRunResponse(SchemaModel):
    status: Literal["completed"]
    harness_run_id: UUID
    total: int
    passed: int
    failed: int
    partial: int
    results: list[HarnessResultResponse] = Field(default_factory=list)


class HarnessScenarioListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[HarnessScenarioResponse] = Field(default_factory=list)


class HarnessResultListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[HarnessResultResponse] = Field(default_factory=list)
