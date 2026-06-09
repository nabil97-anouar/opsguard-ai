from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class SelfAssessmentBase(SchemaModel):
    agent_run_id: UUID
    step_id: UUID
    capability_area: str
    confidence_score: float
    uncertainty_level: str
    what_agent_knows: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    within_capability: bool = True
    decision: str
    rationale: str
    overridden_by_policy: bool = False


class SelfAssessmentRead(SelfAssessmentBase, IDSchema, CreatedAtSchema):
    pass
