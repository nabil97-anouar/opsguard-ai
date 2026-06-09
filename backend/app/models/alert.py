from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin, json_column, timestamp_column


class Alert(UUIDPrimaryKeyMixin, UpdatedAtMixin, table=True):
    __tablename__ = "alerts"

    title: str = Field(max_length=500)
    severity: str = Field(default="info", max_length=20, index=True)
    source: str = Field(max_length=100, index=True)
    infrastructure_type: str = Field(max_length=50, index=True)
    raw_data: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    status: str = Field(default="new", max_length=30, index=True)
    agent_run_id: UUID | None = Field(default=None, foreign_key="agent_runs.id", index=True)
    resolved_at: datetime | None = Field(
        default=None,
        sa_column=timestamp_column(nullable=True),
    )
    tags: list[str] = Field(default_factory=list, sa_column=json_column())
    is_demo: bool = Field(default=False, index=True)


class Incident(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "incidents"

    alert_id: UUID = Field(foreign_key="alerts.id", index=True)
    agent_run_id: UUID | None = Field(default=None, foreign_key="agent_runs.id", index=True)
    title: str = Field(max_length=500)
    severity: str = Field(default="info", max_length=20, index=True)
    root_cause: str
    resolution: str
    kill_chain_stage: str | None = Field(default=None, max_length=100)
    status: str = Field(default="open", max_length=30, index=True)
    resolved_at: datetime | None = Field(
        default=None,
        sa_column=timestamp_column(nullable=True),
    )
    is_demo: bool = Field(default=False, index=True)
