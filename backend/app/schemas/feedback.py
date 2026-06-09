from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class HumanFeedbackBase(SchemaModel):
    agent_run_id: UUID
    decision: str
    reviewer_id: str
    reason: str | None = None
    modified_actions: list[dict[str, Any]] | None = Field(default=None)


class HumanFeedbackRead(HumanFeedbackBase, IDSchema, CreatedAtSchema):
    pass
