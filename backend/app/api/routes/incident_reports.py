from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlmodel import Session

from app.db.session import get_session
from app.services.incident_reports import build_incident_report, render_incident_markdown

router = APIRouter(prefix="/agent/runs", tags=["agent"])


def historical_report(session: Session, agent_run_id: UUID) -> dict:
    try:
        report = build_incident_report(session, agent_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    if report is None:
        raise HTTPException(status_code=404, detail="Agent run was not found.")
    return report


@router.get("/{agent_run_id}/report.json")
def incident_report_json(agent_run_id: UUID, session: Session = Depends(get_session)) -> JSONResponse:
    return JSONResponse(historical_report(session, agent_run_id), headers={
        "Content-Disposition": f'attachment; filename="opsguard-incident-{agent_run_id}.json"',
    })


@router.get("/{agent_run_id}/report.md")
def incident_report_markdown(agent_run_id: UUID, session: Session = Depends(get_session)) -> Response:
    return Response(render_incident_markdown(historical_report(session, agent_run_id)), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="opsguard-incident-{agent_run_id}.md"'})
