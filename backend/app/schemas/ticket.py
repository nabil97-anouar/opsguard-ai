from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class TicketDraftBase(SchemaModel):
    agent_run_id: UUID
    alert_id: UUID
    title: str
    severity: str
    description: str
    steps_to_reproduce: list[str] = Field(default_factory=list)
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_links: list[str] = Field(default_factory=list)
    kill_chain_stage: str | None = None
    assigned_team: str
    sla_target: str
    exported: bool = False


class TicketDraftRead(TicketDraftBase, IDSchema, CreatedAtSchema):
    pass
