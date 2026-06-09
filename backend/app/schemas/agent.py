from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class AgentRunBase(SchemaModel):
    alert_id: UUID
    status: str
    llm_provider: str
    model_version: str | None = None
    total_steps: int = 0
    total_tool_calls: int = 0
    total_tokens_used: int | None = None
    evidence_grounding_score: float | None = None
    risk_level: str
    approval_status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    is_demo: bool = False


class AgentRunRead(AgentRunBase, IDSchema):
    pass


class AgentStepBase(SchemaModel):
    agent_run_id: UUID
    step_index: int
    node_name: str
    status: str
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    error: str | None = None


class AgentStepRead(AgentStepBase, IDSchema, CreatedAtSchema):
    pass
