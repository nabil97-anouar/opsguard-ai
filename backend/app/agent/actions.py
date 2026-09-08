"""Structured proposals, not executable instructions or semantic-support claims."""
from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_intent(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Cf")
    return " ".join(re.findall(r"[a-z0-9]+", value))


class ActionType(str, Enum):
    REVIEW_EVIDENCE = "review_evidence"
    COLLECT_EVIDENCE = "collect_evidence"
    INVESTIGATE = "investigate"
    CREATE_TICKET_DRAFT = "create_ticket_draft"
    CANCEL_JOB = "cancel_job"
    DRAIN_NODE = "drain_node"
    BLOCK_USER = "block_user"
    ISOLATE_NODE = "isolate_node"
    DISABLE_SERVICE = "disable_service"
    DELETE = "delete"
    KILL_PROCESS = "kill_process"
    REVOKE_ACCESS = "revoke_access"
    SHUTDOWN = "shutdown"
    QUARANTINE_NODE = "quarantine_node"


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationState(str, Enum):
    CANDIDATE = "candidate"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    BLOCKED = "blocked"


class ProposedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=100)
    action_type: ActionType
    target: str | None = Field(default=None, max_length=500)
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_level: ActionRisk = ActionRisk.MEDIUM
    requires_approval: bool = True
    supporting_evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    rationale: str = Field(min_length=1, max_length=5000)

    @field_validator("action_type", mode="before")
    @classmethod
    def canonical_action(cls, value):
        if isinstance(value, str):
            compact = normalize_intent(value).replace(" ", "")
            for action in ActionType:
                canonical = action.value.replace("_", "")
                if compact in {canonical, canonical + "s"}:
                    return action.value
        return value
