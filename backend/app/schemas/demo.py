from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DemoSeedRequest(BaseModel):
    reset: bool = False


class DemoSeedSummary(BaseModel):
    status: Literal["ok"]
    created: dict[str, int] = Field(default_factory=dict)
    updated: dict[str, int] = Field(default_factory=dict)
    skipped: dict[str, int] = Field(default_factory=dict)


class DemoSeedResponse(BaseModel):
    status: Literal["ok"]
    message: str
    summary: DemoSeedSummary
