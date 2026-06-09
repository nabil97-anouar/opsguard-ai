from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class KillChainMapping(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "kill_chain_mappings"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    stages_detected: list[str] = Field(default_factory=list, sa_column=json_column())
    primary_stage: str | None = Field(default=None, max_length=100)
    stage_confidence: dict[str, float] = Field(default_factory=dict, sa_column=json_column())
    stage_indicators: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    overall_confidence: float = 0.0
    rationale: str
