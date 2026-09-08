from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column, timestamp_column, utcnow


class AgentRun(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "agent_runs"

    alert_id: UUID = Field(foreign_key="alerts.id", index=True)
    provenance: str = Field(default="legacy_unknown", max_length=30)
    execution_kind: str = Field(default="unknown", max_length=30)
    provider_version: str | None = None
    policy_version: str | None = None
    status: str = Field(default="running", max_length=30, index=True)
    llm_provider: str = Field(default="mock", max_length=50)
    model_version: str | None = Field(default=None, max_length=50)
    total_steps: int = 0
    total_tool_calls: int = 0
    total_tokens_used: int | None = None
    evidence_grounding_score: float | None = None
    risk_level: str = Field(default="medium", max_length=20, index=True)
    approval_status: str = Field(default="not_required", max_length=20, index=True)
    started_at: datetime = Field(
        default_factory=utcnow,
        sa_column=timestamp_column(index=True),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=timestamp_column(nullable=True),
    )
    duration_seconds: float | None = None
    error_message: str | None = None
    is_demo: bool = Field(default=False, index=True)


class AgentStep(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "agent_steps"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    step_index: int = Field(index=True)
    node_name: str = Field(max_length=100)
    status: str = Field(default="running", max_length=20, index=True)
    input_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    output_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    duration_ms: int | None = None
    error: str | None = None
