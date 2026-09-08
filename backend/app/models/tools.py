from __future__ import annotations

from typing import Any
from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column, timestamp_column, utcnow


class ToolCall(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "tool_calls"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    step_id: UUID = Field(foreign_key="agent_steps.id", index=True)
    tool_name: str = Field(max_length=100)
    handler_invoked: bool | None = None
    outcome: str = Field(default="legacy_unknown", max_length=30)
    origin: str = Field(default="legacy_unknown", max_length=100)
    input_args: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    output: Any | None = Field(default=None, sa_column=json_column(nullable=True))
    trust_level: str = Field(default="untrusted", max_length=20, index=True)
    duration_ms: int | None = None
    status: str = Field(default="success", max_length=20, index=True)
    error_message: str | None = None
    injection_scan_result: str = Field(default="pending", max_length=20)


class ToolExecutionAudit(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    """Authoritative attempt identity, including requests with no existing run.

    Run/step IDs are logical request references, deliberately without foreign keys:
    invalid context must be auditable too. Validation happens before dispatch.
    """
    __tablename__ = "tool_execution_audits"

    agent_run_id: UUID | None = Field(default=None, index=True)
    step_id: UUID | None = None
    tool_name: str = Field(max_length=100)
    origin: str = Field(default="api", max_length=100)
    input_snapshot: Any = Field(default_factory=dict, sa_column=json_column())
    validated_target: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    outcome: str = Field(default="requested", max_length=30)
    validated: bool = False
    handler_invoked: bool = False
    requested_at: datetime = Field(default_factory=utcnow, sa_column=timestamp_column())
    invoked_at: datetime | None = Field(default=None, sa_column=timestamp_column(nullable=True))
    completed_at: datetime | None = Field(default=None, sa_column=timestamp_column(nullable=True))
    output_snapshot: Any = Field(default_factory=dict, sa_column=json_column())
    error_code: str | None = None
    user_error: str | None = None
    diagnostic: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
