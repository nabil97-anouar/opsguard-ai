from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.rag.trust import TrustLevel
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


class ToolListItem(SchemaModel):
    name: str
    description: str
    trust_level: TrustLevel
    allowed_use: list[str] = Field(default_factory=list)
    blocked_use: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
    is_destructive: bool = False
    executable: bool
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class ToolListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[ToolListItem] = Field(default_factory=list)


class ToolExecuteRequest(SchemaModel):
    input: dict[str, Any] = Field(default_factory=dict)
    agent_run_id: UUID | None = None


class ToolExecuteResponse(SchemaModel):
    status: Literal["executed", "blocked", "failed"]
    outcome: Literal["succeeded", "blocked", "failed"]
    tool_call_id: UUID | None = None
    tool_name: str
    trust_level: TrustLevel
    requires_human_approval: bool = False
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
