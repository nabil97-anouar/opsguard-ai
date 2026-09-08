from __future__ import annotations

from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.evaluation.reporter import generate_json_report, generate_markdown_report
from app.evaluation.schemas import EvaluationSummary
from app.models import EvaluationReport, EvaluationScore


def create_evaluation_report(session: Session, *, summary: EvaluationSummary) -> EvaluationReport:
    if summary.cohort.provenance != "executed" or summary.cohort.harness_run_id is None:
        raise ValueError("A stored evaluation requires an explicit executed cohort.")
    if summary.evaluation_run_id is not None:
        raise ValueError("This evaluation already has an identity; stored reports cannot be overwritten.")
    evaluation_id = uuid4()
    summary.evaluation_run_id = evaluation_id
    summary.report_kind = "stored"
    report = EvaluationReport(id=evaluation_id, harness_run_id=summary.cohort.harness_run_id,
        provenance=summary.cohort.provenance, schema_version=summary.schema_version,
        summary_payload=generate_json_report(summary), markdown_report=generate_markdown_report(summary))
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def get_evaluation_report(session: Session, evaluation_run_id: UUID | None = None) -> EvaluationReport | None:
    if evaluation_run_id is not None:
        return session.get(EvaluationReport, evaluation_run_id)
    return session.exec(select(EvaluationReport).order_by(EvaluationReport.created_at.desc(), EvaluationReport.id.desc())).first()


def list_evaluation_reports(session: Session, *, limit: int = 20) -> list[dict]:
    reports = session.exec(select(EvaluationReport).order_by(EvaluationReport.created_at.desc()).limit(limit)).all()
    legacy = session.exec(select(EvaluationScore).order_by(EvaluationScore.created_at.desc()).limit(limit)).all()
    items = [{"id": row.id, "created_at": row.created_at, "provenance": row.provenance,
              "report_kind": "stored", "summary_payload": row.summary_payload} for row in reports]
    # Legacy content is kept verbatim in an explicitly labeled historical archive,
    # never validated as current metrics or used to satisfy an execution requirement.
    items += [{"id": row.id, "created_at": row.created_at, "provenance": "legacy_unknown",
               "report_kind": "legacy_archive", "summary_payload": row.model_dump(mode="json")} for row in legacy]
    return sorted(items, key=lambda row: str(row["created_at"]), reverse=True)[:limit]
