from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecisionStatus(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_WARNINGS = "allow_with_warnings"
    REQUIRE_HUMAN_APPROVAL = "require_human_approval"
    BLOCK = "block"


class WatchdogFinding(BaseModel):
    policy_id: str
    title: str
    severity: PolicySeverity
    status: Literal["allow", "warning", "require_human_approval", "block"]
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    remediation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WatchdogDecision(BaseModel):
    status: PolicyDecisionStatus
    summary: str
    findings: list[WatchdogFinding] = Field(default_factory=list)


class WatchdogInput(BaseModel):
    alert: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)
    planned_tools: list[dict[str, Any]] = Field(default_factory=list)
    blocked_tools: list[dict[str, Any]] = Field(default_factory=list)
    self_assessment: dict[str, Any] | None = None
    final_recommendation: dict[str, Any] | None = None
