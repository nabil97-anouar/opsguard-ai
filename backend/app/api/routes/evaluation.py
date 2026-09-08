from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.db.init_db import create_db_and_tables
from app.db.session import get_session
from app.evaluation import (calculate_evaluation_summary, create_evaluation_report,
    generate_json_report, generate_markdown_report, get_evaluation_report,
    latest_executed_harness_run, list_evaluation_reports)
from app.evaluation.schemas import EvaluationSummary
from app.harness import run_security_harness
from app.schemas.evaluation import (EvaluationReportResponse, EvaluationRunRequest,
    EvaluationRunResponse, EvaluationScoreListResponse, EvaluationSummaryResponse)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _stored_report(session: Session, evaluation_run_id: UUID | None):
    report = get_evaluation_report(session, evaluation_run_id)
    if evaluation_run_id is not None and report is None:
        raise HTTPException(status_code=404, detail="Stored evaluation report not found.")
    return report


@router.post("/run", response_model=EvaluationRunResponse)
def run_evaluation(request: EvaluationRunRequest, session: Session = Depends(get_session)) -> EvaluationRunResponse:
    create_db_and_tables(session.get_bind())
    selected_id = request.harness_run_id
    if selected_id is None:
        execution = latest_executed_harness_run(session)
        if execution is not None:
            selected_id = execution.id
        elif request.run_harness_if_empty:
            selected_id = run_security_harness(session, reset_demo_data=False).harness_run_id
    try:
        summary = calculate_evaluation_summary(session, harness_run_id=selected_id, report_type=request.report_type)
        report = create_evaluation_report(session, summary=summary) if selected_id is not None else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EvaluationRunResponse(status="ok", persisted=report is not None,
        evaluation_run_id=report.id if report else None, summary=summary.model_dump(mode="json"))


@router.get("/summary", response_model=EvaluationSummaryResponse)
def get_evaluation_summary(evaluation_run_id: UUID | None = None, session: Session = Depends(get_session)):
    create_db_and_tables(session.get_bind())
    stored = _stored_report(session, evaluation_run_id)
    if stored is not None:
        return stored.summary_payload
    # A preview is explicitly labeled and never written implicitly by a GET.
    return calculate_evaluation_summary(session)


@router.get("/report.md")
def get_evaluation_markdown_report(evaluation_run_id: UUID | None = None, session: Session = Depends(get_session)) -> Response:
    create_db_and_tables(session.get_bind())
    stored = _stored_report(session, evaluation_run_id)
    markdown = stored.markdown_report if stored else generate_markdown_report(calculate_evaluation_summary(session))
    return Response(content=markdown, media_type="text/markdown")


@router.get("/report.json", response_model=EvaluationReportResponse)
def get_evaluation_json_report(evaluation_run_id: UUID | None = None, session: Session = Depends(get_session)):
    create_db_and_tables(session.get_bind())
    stored = _stored_report(session, evaluation_run_id)
    return stored.summary_payload if stored else generate_json_report(calculate_evaluation_summary(session))


@router.get("/scores", response_model=EvaluationScoreListResponse)
def get_evaluation_scores(session: Session = Depends(get_session)) -> EvaluationScoreListResponse:
    create_db_and_tables(session.get_bind())
    return EvaluationScoreListResponse(status="ok", items=list_evaluation_reports(session))
