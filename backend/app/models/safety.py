from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class SafetyEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "safety_events"

    agent_run_id: UUID | None = Field(default=None, foreign_key="agent_runs.id", index=True)
    harness_result_id: UUID | None = Field(
        default=None,
        foreign_key="security_harness_results.id",
        index=True,
    )
    event_type: str = Field(max_length=100, index=True)
    severity: str = Field(default="warning", max_length=20, index=True)
    source: str = Field(max_length=100)
    affected_component: str | None = Field(default=None, max_length=100)
    details: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    pattern_matched: str | None = None
    resolved: bool = False
