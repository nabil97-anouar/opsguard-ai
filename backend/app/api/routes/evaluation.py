from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session, select

from app.db.init_db import create_db_and_tables
from app.db.session import get_session
from app.evaluation import (
    calculate_evaluation_summary,
    create_evaluation_score,
    generate_json_report,
    generate_markdown_report,
    latest_evaluation_score,
    list_evaluation_scores,
    summary_from_evaluation_score,
)
from app.harness import run_security_harness
from app.models import SecurityHarnessResult
from app.schemas.evaluation import (
    EvaluationReportResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationScoreListResponse,
    EvaluationScoreResponse,
    EvaluationSummaryResponse,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _resolve_summary(session: Session) -> EvaluationSummaryResponse:
    stored_score = latest_evaluation_score(session)
    if stored_score is not None:
        stored_summary = summary_from_evaluation_score(stored_score)
        if stored_summary is not None:
            return EvaluationSummaryResponse.model_validate(stored_summary.model_dump(mode="json"))

    calculated = calculate_evaluation_summary(session)
    return EvaluationSummaryResponse.model_validate(calculated.model_dump(mode="json"))


@router.post("/run", response_model=EvaluationRunResponse)
def run_evaluation(
    request: EvaluationRunRequest,
    session: Session = Depends(get_session),
) -> EvaluationRunResponse:
    create_db_and_tables()

    has_harness_results = session.exec(select(SecurityHarnessResult.id).limit(1)).first() is not None
    if not has_harness_results and request.run_harness_if_empty:
        run_security_harness(session, reset_demo_data=True)

    summary = calculate_evaluation_summary(session, report_type=request.report_type)
    evaluation_score = None
    persisted = False
    try:
        evaluation_score = create_evaluation_score(
            session,
            summary=summary,
            report_type=request.report_type,
        )
        persisted = True
    except ValueError:
        persisted = False

    return EvaluationRunResponse(
        status="ok",
        persisted=persisted,
        evaluation_score_id=evaluation_score.id if evaluation_score is not None else None,
        summary=EvaluationSummaryResponse.model_validate(summary.model_dump(mode="json")),
        scorecard=summary.scorecard,
    )


@router.get("/summary", response_model=EvaluationSummaryResponse)
def get_evaluation_summary(session: Session = Depends(get_session)) -> EvaluationSummaryResponse:
    create_db_and_tables()
    return _resolve_summary(session)


@router.get("/report.md")
def get_evaluation_markdown_report(session: Session = Depends(get_session)) -> Response:
    create_db_and_tables()
    summary = _resolve_summary(session)
    markdown = generate_markdown_report(summary)
    return Response(content=markdown, media_type="text/markdown")


@router.get("/report.json", response_model=EvaluationReportResponse)
def get_evaluation_json_report(session: Session = Depends(get_session)) -> EvaluationReportResponse:
    create_db_and_tables()
    summary = _resolve_summary(session)
    return EvaluationReportResponse.model_validate(generate_json_report(summary))


@router.get("/scores", response_model=EvaluationScoreListResponse)
def get_evaluation_scores(session: Session = Depends(get_session)) -> EvaluationScoreListResponse:
    create_db_and_tables()
    rows = list_evaluation_scores(session)
    return EvaluationScoreListResponse(
        status="ok",
        items=[EvaluationScoreResponse.model_validate(row) for row in rows],
    )
