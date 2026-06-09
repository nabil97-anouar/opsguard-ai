from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class HumanFeedback(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "human_feedback"

    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    decision: str = Field(max_length=20, index=True)
    reviewer_id: str = Field(max_length=100, index=True)
    reason: str | None = None
    modified_actions: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=json_column(nullable=True),
    )
