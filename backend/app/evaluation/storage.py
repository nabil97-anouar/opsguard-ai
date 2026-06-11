from __future__ import annotations

from sqlmodel import Session, select

from app.evaluation.schemas import EvaluationSummary
from app.models import AgentRun, EvaluationScore


def create_evaluation_score(
    session: Session,
    *,
    summary: EvaluationSummary,
    report_type: str = "full",
) -> EvaluationScore:
    agent_run_id = summary.latest_agent_run_id
    if agent_run_id is None:
        latest_agent_run = session.exec(select(AgentRun).order_by(AgentRun.started_at.desc())).first()
        if latest_agent_run is None:
            raise ValueError("Cannot persist an evaluation score without at least one agent run.")
        agent_run_id = latest_agent_run.id

    average_response_time = session.exec(select(AgentRun).order_by(AgentRun.started_at.desc())).all()
    durations = [run.duration_seconds for run in average_response_time if run.duration_seconds is not None]
    mean_duration = round(sum(durations) / len(durations), 3) if durations else 0.0

    prompt_ratio = (
        summary.prompt_injection_resistance.prompt_injection_scenarios_passed
        / summary.prompt_injection_resistance.prompt_injection_scenarios_total
        if summary.prompt_injection_resistance.prompt_injection_scenarios_total
        else 0.0
    )

    evaluation_score = EvaluationScore(
        agent_run_id=agent_run_id,
        report_type=report_type,
        evidence_grounding=summary.scorecard.grounding_score,
        correctness=summary.harness_performance.pass_rate,
        non_speculativeness=max(0.0, 100.0 - (summary.grounding_evidence.runs_missing_citations * 10.0)),
        incident_focus=min(100.0, summary.watchdog_coverage.require_human_approval_decisions * 10.0),
        actionability=min(100.0, summary.agent_quality.runs_with_ticket_draft * 10.0),
        safety_score=summary.scorecard.safety_score,
        response_time_seconds=mean_duration,
        safety_violations_blocked=(
            summary.watchdog_coverage.block_decisions + summary.tool_safety.blocked_tool_calls
        ),
        prompt_injection_resistance=round(prompt_ratio * 100, 1),
        tool_misuse_resistance=summary.scorecard.tool_safety_score,
        uncertainty_calibration=max(
            0.0,
            min(
                100.0,
                round(
                    (
                        summary.agent_quality.runs_with_self_assessment
                        / max(summary.agent_quality.total_agent_runs, 1)
                    )
                    * 100,
                    1,
                ),
            ),
        ),
        human_approval_usefulness=round(
            (
                summary.human_approval_enforcement.runs_requiring_human_approval
                / max(summary.agent_quality.total_agent_runs, 1)
            )
            * 100,
            1,
        )
        if summary.agent_quality.total_agent_runs
        else None,
        overall_score=summary.scorecard.overall_score,
        summary_payload=summary.model_dump(mode="json"),
    )
    session.add(evaluation_score)
    session.commit()
    session.refresh(evaluation_score)
    return evaluation_score


def list_evaluation_scores(session: Session, *, limit: int = 20) -> list[EvaluationScore]:
    return session.exec(
        select(EvaluationScore).order_by(EvaluationScore.created_at.desc()).limit(limit)
    ).all()


def latest_evaluation_score(session: Session) -> EvaluationScore | None:
    return session.exec(select(EvaluationScore).order_by(EvaluationScore.created_at.desc())).first()


def summary_from_evaluation_score(score: EvaluationScore) -> EvaluationSummary | None:
    if not score.summary_payload:
        return None
    return EvaluationSummary.model_validate(score.summary_payload)
