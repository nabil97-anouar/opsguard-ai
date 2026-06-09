from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.state import AssessmentSnapshot, FinalRecommendation


class StepExecutionSummary(BaseModel):
    id: UUID
    step_index: int
    node_name: str
    status: str
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    error: str | None = None
    created_at: datetime


class AgentRunResult(BaseModel):
    agent_run_id: UUID
    alert_id: UUID
    status: str
    steps: list[StepExecutionSummary] = Field(default_factory=list)
    self_assessment: AssessmentSnapshot | None = None
    final_recommendation: FinalRecommendation | None = None
    error: str | None = None
