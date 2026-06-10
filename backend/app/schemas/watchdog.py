from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import SchemaModel
from app.watchdog.schemas import WatchdogDecision, WatchdogFinding


class WatchdogEvaluateRequest(SchemaModel):
    alert: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)
    planned_tools: list[dict[str, Any]] = Field(default_factory=list)
    blocked_tools: list[dict[str, Any]] = Field(default_factory=list)
    self_assessment: dict[str, Any] | None = None
    final_recommendation: dict[str, Any] | None = None


class WatchdogPolicyItem(SchemaModel):
    policy_id: str
    title: str
    description: str


class WatchdogPoliciesResponse(SchemaModel):
    status: str
    items: list[WatchdogPolicyItem] = Field(default_factory=list)


class WatchdogEvaluateResponse(WatchdogDecision):
    pass


class WatchdogFindingResponse(WatchdogFinding):
    pass
