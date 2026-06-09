from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DependencyHealth(BaseModel):
    postgres: str
    qdrant: str
    llm_provider: str


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    version: str
    environment: str
    dependencies: DependencyHealth
    timestamp: datetime
