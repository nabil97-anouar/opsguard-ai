from __future__ import annotations

from uuid import UUID

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class EvaluationScoreBase(SchemaModel):
    agent_run_id: UUID
    evidence_grounding: float = 0.0
    correctness: float = 0.0
    non_speculativeness: float = 0.0
    incident_focus: float = 0.0
    actionability: float = 0.0
    safety_score: float = 0.0
    response_time_seconds: float = 0.0
    safety_violations_blocked: int = 0
    prompt_injection_resistance: float = 0.0
    tool_misuse_resistance: float = 0.0
    uncertainty_calibration: float = 0.0
    human_approval_usefulness: float | None = None
    overall_score: float = 0.0


class EvaluationScoreRead(EvaluationScoreBase, IDSchema, CreatedAtSchema):
    pass
