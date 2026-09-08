from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import SchemaModel
from app.watchdog.schemas import WatchdogDecision, WatchdogFinding


from app.watchdog.schemas import WatchdogInput


class WatchdogEvaluateRequest(WatchdogInput):
    pass

class WatchdogPolicyItem(SchemaModel):
    policy_id: str
    title: str
    description: str


class WatchdogPoliciesResponse(SchemaModel):
    status: str
    items: list[WatchdogPolicyItem] = Field(default_factory=list)


class WatchdogEvaluateResponse(WatchdogDecision):
    pass


class WatchdogFindingResponse(WatchdogFinding):
    pass
