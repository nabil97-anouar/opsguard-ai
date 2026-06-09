from __future__ import annotations

from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class SelfAssessment(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "self_assessments"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    step_id: UUID = Field(foreign_key="agent_steps.id", index=True)
    capability_area: str = Field(max_length=100)
    confidence_score: float
    uncertainty_level: str = Field(default="medium", max_length=20, index=True)
    what_agent_knows: list[str] = Field(default_factory=list, sa_column=json_column())
    missing_evidence: list[str] = Field(default_factory=list, sa_column=json_column())
    within_capability: bool = True
    decision: str = Field(default="continue", max_length=30)
    rationale: str
    overridden_by_policy: bool = False
