from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class EvaluationReport(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    """Immutable application snapshot; independent of legacy score columns and agent FKs."""

    __tablename__ = "evaluation_reports"

    harness_run_id: UUID | None = Field(default=None, index=True)
    provenance: str = Field(max_length=30)
    schema_version: str = Field(max_length=50)
    summary_payload: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    markdown_report: str


class EvaluationScore(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    """Legacy archive only. New evaluations use EvaluationReport."""
    __tablename__ = "evaluation_scores"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    report_type: str = Field(default="full", max_length=50, index=True)
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
    summary_payload: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
