from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    check: Literal["liveness"] = "liveness"
    version: str
    environment: str
    reasoner: Literal["deterministic-mock-v2"] = "deterministic-mock-v2"
    timestamp: datetime


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    check: Literal["readiness"] = "readiness"
    database: Literal["ready", "unavailable", "schema_missing"]
    reason: str | None = None
    timestamp: datetime
