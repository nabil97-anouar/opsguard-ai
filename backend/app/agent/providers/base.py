from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.actions import ActionType, ProposedAction
from app.rag.trust import TrustLevel

REASONING_SCHEMA_VERSION = "reasoning-v1"


class ProviderClassification(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    alert_type: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=30)
    infrastructure_type: str = Field(min_length=1, max_length=100)
    urgency: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(ge=0, le=1)
    risk_level: Literal["low", "medium", "high", "critical"]
    classification_rationale: str = Field(min_length=1, max_length=5000)
    likely_root_cause: str = Field(min_length=1, max_length=2000)
    query_hint: str = Field(min_length=1, max_length=1000)
    initial_missing_evidence: list[str] = Field(default_factory=list, max_length=30)


class ProviderHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=5000)
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[str] = Field(default_factory=list, max_length=100)


class ProviderHypotheses(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypotheses: list[ProviderHypothesis] = Field(min_length=1, max_length=12)


class ProviderAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    capability_area: str = Field(min_length=1, max_length=100)
    confidence_score: float = Field(ge=0, le=1)
    uncertainty_level: Literal["low", "medium", "high"]
    what_agent_knows: list[str] = Field(default_factory=list, max_length=30)
    missing_evidence: list[str] = Field(default_factory=list, max_length=30)
    within_capability: bool = True
    decision: Literal["retrieve_more", "recommend_human_review", "stop_and_request_human_review"]
    rationale: str = Field(min_length=1, max_length=5000)
    risk_flags: list[str] = Field(default_factory=list, max_length=30)
    overridden_by_policy: bool = False


class ProviderRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=8000)
    recommended_next_steps: list[str] = Field(default_factory=list, max_length=30)
    proposed_actions: list[ProposedAction] = Field(default_factory=list, max_length=30)
    uncertainty: Literal["low", "medium", "high"]
    missing_evidence: list[str] = Field(default_factory=list, max_length=30)
    notes: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_action_targets(self) -> "ProviderRecommendation":
        target_required = set(ActionType) - {ActionType.REVIEW_EVIDENCE, ActionType.COLLECT_EVIDENCE}
        for action in self.proposed_actions:
            if action.action_type in target_required and not (action.target and action.target.strip()):
                raise ValueError(f"Action {action.action_type.value} requires a target.")
        return self


class ProviderEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source_type: Literal["alert", "document", "tool"]
    trust_level: TrustLevel
    observation_status: Literal["valid", "succeeded"]
    source: str
    title: str | None = None
    summary: str
    content: str | dict[str, object]

    @model_validator(mode="after")
    def reject_quarantined_evidence(self) -> "ProviderEvidence":
        if self.trust_level == TrustLevel.QUARANTINED:
            raise ValueError("Quarantined evidence cannot enter provider context.")
        return self


class ProviderContext(BaseModel):
    """Minimal reasoning context. Evidence is explicitly untrusted data."""

    model_config = ConfigDict(extra="forbid")

    agent_run_id: str
    task: Literal["classification", "hypotheses", "assessment", "recommendation"]
    alert: dict[str, object]
    classification: dict[str, object] = Field(default_factory=dict)
    untrusted_evidence: list[ProviderEvidence] = Field(default_factory=list, max_length=50)
    suspicious_observations: list[dict[str, object]] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    missing_targets: list[str] = Field(default_factory=list)
    hypotheses: list[dict[str, object]] = Field(default_factory=list)
    self_assessment: dict[str, object] | None = None
    blocked_action_definitions: list[dict[str, object]] = Field(default_factory=list)
    allowed_action_types: list[str] = Field(default_factory=lambda: [item.value for item in ActionType])

    @property
    def available_evidence_ids(self) -> set[str]:
        return {item.evidence_id for item in self.untrusted_evidence}


class ProviderIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Literal["deterministic", "openai"]
    model: str
    mode: Literal["local", "external"]
    implementation_version: str
    schema_version: str = REASONING_SCHEMA_VERSION
    configured: bool = True
    available: bool = True
    reason: str | None = None


T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ProviderCallResult(Generic[T]):
    value: T
    duration_ms: int
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None and self.output_tokens is None:
            return None
        return (self.input_tokens or 0) + (self.output_tokens or 0)


class LLMProvider(ABC):
    @property
    @abstractmethod
    def identity(self) -> ProviderIdentity: ...

    @abstractmethod
    def classify(self, context: ProviderContext) -> ProviderCallResult[ProviderClassification]: ...

    @abstractmethod
    def hypothesize(self, context: ProviderContext) -> ProviderCallResult[ProviderHypotheses]: ...

    @abstractmethod
    def assess(self, context: ProviderContext) -> ProviderCallResult[ProviderAssessment]: ...

    @abstractmethod
    def recommend(self, context: ProviderContext) -> ProviderCallResult[ProviderRecommendation]: ...


def validate_evidence_references(
    context: ProviderContext,
    *,
    hypotheses: Sequence[ProviderHypothesis] = (),
    actions: Sequence[ProposedAction] = (),
) -> None:
    available = context.available_evidence_ids
    references = [ref for item in hypotheses for ref in item.supporting_evidence]
    references.extend(ref for item in actions for ref in item.supporting_evidence_ids)
    if unknown := set(references) - available:
        from app.agent.providers.errors import ProviderInvalidOutputError

        raise ProviderInvalidOutputError(f"Unknown or cross-run evidence references: {sorted(unknown)!r}")
