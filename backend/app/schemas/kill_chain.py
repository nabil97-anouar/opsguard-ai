from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class KillChainMappingBase(SchemaModel):
    agent_run_id: UUID
    stages_detected: list[str] = Field(default_factory=list)
    primary_stage: str | None = None
    stage_confidence: dict[str, float] = Field(default_factory=dict)
    stage_indicators: dict[str, Any] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    rationale: str


class KillChainMappingRead(KillChainMappingBase, IDSchema, CreatedAtSchema):
    pass
