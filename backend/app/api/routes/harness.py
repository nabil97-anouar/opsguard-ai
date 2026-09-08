from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.harness import get_harness_run_results, get_scenarios, list_harness_results, run_security_harness
from app.schemas.harness import (
    HarnessResultListResponse,
    HarnessResultResponse,
    HarnessRunRequest,
    HarnessRunResponse,
    HarnessScenarioListResponse,
    HarnessScenarioResponse,
)

router = APIRouter(prefix="/harness", tags=["harness"])


@router.get("/scenarios", response_model=HarnessScenarioListResponse)
def list_harness_scenarios() -> HarnessScenarioListResponse:
    return HarnessScenarioListResponse(
        status="ok",
        items=[
            HarnessScenarioResponse.model_validate(scenario.model_dump(mode="json"))
            for scenario in get_scenarios()
        ],
    )


@router.post("/run", response_model=HarnessRunResponse)
def run_harness_route(
    request: HarnessRunRequest,
    session: Session = Depends(get_session),
) -> HarnessRunResponse:
    try:
        result = run_security_harness(
            session,
            scenario_ids=request.scenario_ids,
            reset_demo_data=request.reset_demo_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return HarnessRunResponse.model_validate(result.model_dump(mode="json"))


@router.get("/results", response_model=HarnessResultListResponse)
def list_harness_results_route(session: Session = Depends(get_session)) -> HarnessResultListResponse:
    return HarnessResultListResponse(
        status="ok",
        items=[
            HarnessResultResponse.model_validate(result.model_dump(mode="json"))
            for result in list_harness_results(session)
        ],
    )


@router.get("/results/{harness_run_id}", response_model=HarnessRunResponse)
def get_harness_run_route(
    harness_run_id: UUID,
    session: Session = Depends(get_session),
) -> HarnessRunResponse:
    payload = get_harness_run_results(session, harness_run_id=harness_run_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security harness run '{harness_run_id}' was not found.",
        )

    return HarnessRunResponse.model_validate(payload.model_dump(mode="json"))
