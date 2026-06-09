from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class SafetyEventBase(SchemaModel):
    agent_run_id: UUID | None = None
    harness_result_id: UUID | None = None
    event_type: str
    severity: str
    source: str
    affected_component: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    pattern_matched: str | None = None
    resolved: bool = False


class SafetyEventRead(SafetyEventBase, IDSchema, CreatedAtSchema):
    pass
