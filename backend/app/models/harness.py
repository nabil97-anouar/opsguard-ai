from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, json_column, timestamp_column, utcnow


class SecurityHarnessRun(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "security_harness_runs"

    provenance: str = Field(default="legacy_unknown", max_length=30)
    status: str = Field(default="running", max_length=30)
    started_at: datetime = Field(default_factory=utcnow, sa_column=timestamp_column())
    completed_at: datetime | None = Field(default=None, sa_column=timestamp_column(nullable=True))
    scenario_manifest: list[dict[str, Any]] = Field(default_factory=list, sa_column=json_column())
    expected_case_count: int = 0
    completed_case_count: int = 0
    provider_version: str | None = None
    policy_version: str | None = None


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
    provenance: str = Field(default="legacy_unknown", max_length=30)
    test_level: str = Field(default="unknown", max_length=30)
    scenario_version: str = Field(default="unknown", max_length=50)
    test_id: UUID = Field(foreign_key="security_harness_tests.id", index=True)
    score: int = 0
    max_score: int = 10
    passed: bool = False
    actual_behavior: str
    injection_detected: bool = False
    action_blocked: bool = False
    safety_event_id: UUID | None = Field(default=None, foreign_key="safety_events.id", index=True)
    details: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
