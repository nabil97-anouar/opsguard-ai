from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column


class SecurityHarnessTest(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "security_harness_tests"

    test_id: str = Field(max_length=50, index=True)
    category: str = Field(max_length=50, index=True)
    name: str = Field(max_length=200)
    description: str
    injection_point: str = Field(max_length=100)
    attack_payload: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    expected_behavior: str
    detection_logic: str
    max_score: int = 10
    weight: float = 1.0
    active: bool = True


class SecurityHarnessResult(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "security_harness_results"

    harness_run_id: UUID = Field(index=True)
    test_id: UUID = Field(foreign_key="security_harness_tests.id", index=True)
    score: int = 0
    max_score: int = 10
    passed: bool = False
    actual_behavior: str
    injection_detected: bool = False
    action_blocked: bool = False
    safety_event_id: UUID | None = Field(default=None, foreign_key="safety_events.id", index=True)
    details: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
