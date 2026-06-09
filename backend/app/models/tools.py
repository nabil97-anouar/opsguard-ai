from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class ToolCall(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "tool_calls"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    step_id: UUID = Field(foreign_key="agent_steps.id", index=True)
    tool_name: str = Field(max_length=100)
    input_args: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    output: Any | None = Field(default=None, sa_column=json_column(nullable=True))
    trust_level: str = Field(default="untrusted", max_length=20, index=True)
    duration_ms: int | None = None
    status: str = Field(default="success", max_length=20, index=True)
    error_message: str | None = None
    injection_scan_result: str = Field(default="pending", max_length=20)
