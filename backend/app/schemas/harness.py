from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel


class SecurityHarnessTestBase(SchemaModel):
    test_id: str
    category: str
    name: str
    description: str
    injection_point: str
    attack_payload: dict[str, Any] = Field(default_factory=dict)
    expected_behavior: str
    detection_logic: str
    max_score: int = 10
    weight: float = 1.0
    active: bool = True


class SecurityHarnessTestRead(SecurityHarnessTestBase, IDSchema):
    pass


class SecurityHarnessResultBase(SchemaModel):
    harness_run_id: UUID
    test_id: UUID
    score: int = 0
    max_score: int = 10
    passed: bool = False
    actual_behavior: str
    injection_detected: bool = False
    action_blocked: bool = False
    safety_event_id: UUID | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SecurityHarnessResultRead(SecurityHarnessResultBase, IDSchema, CreatedAtSchema):
    pass
