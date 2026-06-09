from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.agent.runner import (
    get_agent_run_detail,
    list_agent_runs as list_recent_agent_runs,
    run_agent_for_alert,
)
from app.db.init_db import create_db_and_tables
from app.db.session import get_session
from app.schemas.agent_run import (
    AgentAssessmentResponse,
    AgentRunCreateRequest,
    AgentRunDetailResponse,
    AgentRunListItem,
    AgentRunListResponse,
    AgentRunResponse,
    AgentStepResponse,
    FinalRecommendationResponse,
)
from app.schemas.tools import ToolCallRead

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/runs", response_model=AgentRunResponse)
def create_agent_run_route(
    request: AgentRunCreateRequest,
    session: Session = Depends(get_session),
) -> AgentRunResponse:
    create_db_and_tables()
    try:
        result = run_agent_for_alert(session, alert_id=request.alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return AgentRunResponse(
        status=result.status,
        agent_run_id=result.agent_run_id,
        alert_id=result.alert_id,
        steps=[AgentStepResponse.model_validate(step) for step in result.steps],
        self_assessment=(
            AgentAssessmentResponse.model_validate(result.self_assessment)
            if result.self_assessment is not None
            else None
        ),
        final_recommendation=(
            FinalRecommendationResponse.model_validate(result.final_recommendation)
            if result.final_recommendation is not None
            else None
        ),
    )


@router.get("/runs/{agent_run_id}", response_model=AgentRunDetailResponse)
def get_agent_run_route(agent_run_id: UUID, session: Session = Depends(get_session)) -> AgentRunDetailResponse:
    create_db_and_tables()
    payload = get_agent_run_detail(session, agent_run_id=agent_run_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent run '{agent_run_id}' was not found.",
        )

    agent_run = payload["agent_run"]
    steps = payload["steps"]
    tool_calls = payload["tool_calls"]
    self_assessment = payload["self_assessment"]
    final_recommendation = payload["final_recommendation"]

    return AgentRunDetailResponse(
        agent_run_id=agent_run.id,
        alert_id=agent_run.alert_id,
        status=agent_run.status,
        llm_provider=agent_run.llm_provider,
        model_version=agent_run.model_version,
        risk_level=agent_run.risk_level,
        approval_status=agent_run.approval_status,
        started_at=agent_run.started_at,
        completed_at=agent_run.completed_at,
        duration_seconds=agent_run.duration_seconds,
        error_message=agent_run.error_message,
        steps=[AgentStepResponse.model_validate(step) for step in steps],
        tool_calls=[ToolCallRead.model_validate(tool_call) for tool_call in tool_calls],
        self_assessment=(
            AgentAssessmentResponse.model_validate(self_assessment) if self_assessment is not None else None
        ),
        final_recommendation=(
            FinalRecommendationResponse.model_validate(final_recommendation)
            if final_recommendation is not None
            else None
        ),
    )


@router.get("/runs", response_model=AgentRunListResponse)
def list_agent_runs_route(session: Session = Depends(get_session)) -> AgentRunListResponse:
    create_db_and_tables()
    runs = list_recent_agent_runs(session)
    return AgentRunListResponse(
        status="ok",
        items=[
            AgentRunListItem(
                agent_run_id=run.id,
                alert_id=run.alert_id,
                status=run.status,
                risk_level=run.risk_level,
                approval_status=run.approval_status,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
            for run in runs
        ],
    )
