from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator
from uuid import UUID, uuid5, NAMESPACE_URL
from app.agent.actions import ProposedAction
from app.core.versions import POLICY_VERSION


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
    finding_id: str = ""
    affected_action_ids: list[str] = Field(default_factory=list)
    policy_id: str
    title: str
    severity: PolicySeverity
    status: Literal["allow", "warning", "require_human_approval", "block"]
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    remediation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


    @model_validator(mode="after")
    def identity(self):
        if not self.finding_id:
            self.finding_id = str(uuid5(NAMESPACE_URL, POLICY_VERSION + self.policy_id + self.status + self.severity.value
                + self.reason + str(sorted(self.affected_action_ids)) + str(sorted(self.evidence_refs))))
        return self

    @computed_field
    @property
    def finding_type(self) -> str:
        return self.policy_id

    @computed_field
    @property
    def blocking(self) -> bool:
        return self.status == "block"

    @computed_field
    @property
    def mandatory_review(self) -> bool:
        return self.status in {"block", "require_human_approval"}


class WatchdogDecision(BaseModel):
    policy_version: str = POLICY_VERSION
    status: PolicyDecisionStatus
    summary: str
    findings: list[WatchdogFinding] = Field(default_factory=list)


    @computed_field
    @property
    def verdict(self) -> PolicyDecisionStatus:
        return self.status

    @computed_field
    @property
    def blocking(self) -> bool:
        return self.status == PolicyDecisionStatus.BLOCK

    @computed_field
    @property
    def mandatory_review(self) -> bool:
        return self.status in {PolicyDecisionStatus.BLOCK, PolicyDecisionStatus.REQUIRE_HUMAN_APPROVAL}

    @computed_field
    @property
    def reason(self) -> str:
        return self.summary

    @computed_field
    @property
    def severity(self) -> PolicySeverity:
        order = list(PolicySeverity)
        return max((finding.severity for finding in self.findings), key=order.index, default=PolicySeverity.INFO)

    @computed_field
    @property
    def finding_ids(self) -> list[str]:
        return [finding.finding_id for finding in self.findings]

    @computed_field
    @property
    def affected_action_ids(self) -> list[str]:
        return sorted({identity for finding in self.findings for identity in finding.affected_action_ids})


class WatchdogInput(BaseModel):
    agent_run_id: UUID | None = None
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    alert: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)
    planned_tools: list[dict[str, Any]] = Field(default_factory=list)
    blocked_tools: list[dict[str, Any]] = Field(default_factory=list)
    self_assessment: dict[str, Any] | None = None
    final_recommendation: dict[str, Any] | None = None


    @model_validator(mode="after")
    def collect_structured_actions(self):
        actions = {}
        for action in self.proposed_actions:
            if action.action_id in actions:
                raise ValueError("Duplicate proposed action identity")
            actions[action.action_id] = action
        for value in (self.final_recommendation or {}).get("proposed_actions", []):
            action = ProposedAction.model_validate(value)
            if action.action_id in actions and actions[action.action_id] != action:
                raise ValueError("Conflicting proposed action identity")
            actions[action.action_id] = action
        self.proposed_actions = list(actions.values())
        return self
