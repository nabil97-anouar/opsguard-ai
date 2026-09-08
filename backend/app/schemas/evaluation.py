from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.evaluation.schemas import EvaluationSummary
from app.schemas.common import SchemaModel


class EvaluationSummaryResponse(EvaluationSummary):
    pass


class EvaluationRunRequest(SchemaModel):
    harness_run_id: UUID | None = None
    run_harness_if_empty: bool = True
    report_type: str = "full"


class EvaluationRunResponse(SchemaModel):
    status: Literal["ok"]
    persisted: bool
    evaluation_run_id: UUID | None = None
    summary: EvaluationSummaryResponse


class EvaluationReportResponse(EvaluationSummaryResponse):
    title: str


class EvaluationScoreResponse(SchemaModel):
    """Historical archive envelope; legacy payloads are not current measurements."""
    id: UUID
    created_at: datetime
    provenance: str
    report_kind: Literal["stored", "legacy_archive"]
    summary_payload: dict[str, Any]


class EvaluationScoreListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[EvaluationScoreResponse] = Field(default_factory=list)
