from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db.session import get_session
from app.db.init_db import create_db_and_tables
from app.watchdog.context import persisted_watchdog_context

from app.schemas.watchdog import (
    WatchdogEvaluateRequest,
    WatchdogEvaluateResponse,
    WatchdogPoliciesResponse,
    WatchdogPolicyItem,
)
from app.watchdog import evaluate_watchdog, list_policy_definitions

router = APIRouter(prefix="/watchdog", tags=["watchdog"])


@router.post("/evaluate", response_model=WatchdogEvaluateResponse)
def evaluate_watchdog_route(request: WatchdogEvaluateRequest, session: Session = Depends(get_session)) -> WatchdogEvaluateResponse:
    create_db_and_tables(session.get_bind())
    decision = evaluate_watchdog(persisted_watchdog_context(session, request))
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
