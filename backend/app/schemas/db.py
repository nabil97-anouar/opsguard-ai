from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    status: Literal["healthy"]
    latency_ms: float
    timestamp: datetime


class CreateTablesResponse(BaseModel):
    status: Literal["created"]
    environment: str
    tables: list[str]
