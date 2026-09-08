from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class TicketDraft(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "ticket_drafts"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    alert_id: UUID = Field(foreign_key="alerts.id", index=True)
    title: str = Field(max_length=500)
    severity: str = Field(default="info", max_length=20, index=True)
    description: str
    steps_to_reproduce: list[str] = Field(default_factory=list, sa_column=json_column())
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list, sa_column=json_column())
    evidence_links: list[str] = Field(default_factory=list, sa_column=json_column())
    kill_chain_stage: str | None = Field(default=None, max_length=100)
    assigned_team: str = Field(max_length=100)
    sla_target: str = Field(max_length=50)
    lifecycle_state: str = Field(default="candidate", max_length=40)
    policy_validation: str = Field(default="not_evaluated", max_length=40)
    policy_version: str | None = None
    exported: bool = False
