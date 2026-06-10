from __future__ import annotations

from fastapi import APIRouter

from app.schemas.watchdog import (
    WatchdogEvaluateRequest,
    WatchdogEvaluateResponse,
    WatchdogPoliciesResponse,
    WatchdogPolicyItem,
)
from app.watchdog import WatchdogInput, evaluate_watchdog, list_policy_definitions

router = APIRouter(prefix="/watchdog", tags=["watchdog"])


@router.post("/evaluate", response_model=WatchdogEvaluateResponse)
def evaluate_watchdog_route(request: WatchdogEvaluateRequest) -> WatchdogEvaluateResponse:
    decision = evaluate_watchdog(WatchdogInput.model_validate(request.model_dump(mode="json")))
    return WatchdogEvaluateResponse.model_validate(decision.model_dump(mode="json"))


@router.get("/policies", response_model=WatchdogPoliciesResponse)
def list_watchdog_policies() -> WatchdogPoliciesResponse:
    return WatchdogPoliciesResponse(
        status="ok",
        items=[
            WatchdogPolicyItem(
                policy_id=policy.policy_id,
                title=policy.title,
                description=policy.description,
            )
            for policy in list_policy_definitions()
        ],
    )
