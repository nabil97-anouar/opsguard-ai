from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel, UpdatedAtSchema


class AlertBase(SchemaModel):
    title: str
    severity: str
    source: str
    infrastructure_type: str
    raw_data: dict[str, Any] = Field(default_factory=dict)
    status: str
    agent_run_id: UUID | None = None
    resolved_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    is_demo: bool = False


class AlertRead(AlertBase, IDSchema, UpdatedAtSchema):
    pass


class IncidentBase(SchemaModel):
    alert_id: UUID
    agent_run_id: UUID | None = None
    title: str
    severity: str
    root_cause: str
    resolution: str
    kill_chain_stage: str | None = None
    status: str
    resolved_at: datetime | None = None
    is_demo: bool = False


class IncidentRead(IncidentBase, IDSchema, CreatedAtSchema):
    pass
