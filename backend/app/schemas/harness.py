from __future__ import annotations

from pydantic import Field
from typing import Literal

from app.schemas.common import SchemaModel
from app.harness.schemas import HarnessScenarioDefinition, HarnessScenarioResult, HarnessRunResult


class HarnessRunRequest(SchemaModel):
    scenario_ids: list[str] | None = None
    reset_demo_data: bool = False


class HarnessScenarioResponse(HarnessScenarioDefinition):
    pass


class HarnessResultResponse(HarnessScenarioResult):
    pass


class HarnessRunResponse(HarnessRunResult):
    pass


class HarnessScenarioListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[HarnessScenarioResponse] = Field(default_factory=list)


class HarnessResultListResponse(SchemaModel):
    status: Literal["ok"]
    items: list[HarnessResultResponse] = Field(default_factory=list)
