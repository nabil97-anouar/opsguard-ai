from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class ToolCallBase(SchemaModel):
    agent_run_id: UUID
    step_id: UUID
    tool_name: str
    input_args: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None
    trust_level: str
    duration_ms: int | None = None
    status: str
    error_message: str | None = None
    injection_scan_result: str


class ToolCallRead(ToolCallBase, IDSchema, CreatedAtSchema):
    pass
