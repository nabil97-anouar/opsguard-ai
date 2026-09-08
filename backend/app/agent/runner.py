from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.agent.nodes import (
    classify_alert_node,
    execute_safe_tools,
    generate_recommendation,
    ingest_alert,
    metacognitive_self_assessment,
    plan_tool_calls,
    retrieve_context,
    synthesize_hypotheses,
    wait_for_human_approval,
    watchdog_policy_check,
)
from app.agent.schemas import AgentRunResult, StepExecutionSummary
from app.agent.state import AgentState, AssessmentSnapshot, FinalRecommendation
from app.core.versions import POLICY_VERSION, PROVIDER_VERSION
from app.models import AgentRun, AgentStep, Alert, SelfAssessment, ToolCall
from app.models.base import utcnow

RUNNER_MODEL_VERSION = PROVIDER_VERSION


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _state_result(state: AgentState, agent_run: AgentRun) -> AgentRunResult:
    return AgentRunResult(
        provenance=agent_run.provenance,
        execution_kind=agent_run.execution_kind,
        provider_version=agent_run.provider_version,
        policy_version=agent_run.policy_version,
        agent_run_id=agent_run.id,
        alert_id=agent_run.alert_id,
        status=agent_run.status,
        steps=[StepExecutionSummary.model_validate(step) for step in state.steps],
        self_assessment=state.self_assessment,
        final_recommendation=state.final_recommendation,
        error=agent_run.error_message,
    )


def _latest_self_assessment(session: Session, agent_run_id: UUID) -> SelfAssessment | None:
    return session.exec(
        select(SelfAssessment)
        .where(SelfAssessment.agent_run_id == agent_run_id)
        .order_by(SelfAssessment.created_at.desc())
    ).first()


def _final_recommendation_from_steps(steps: list[AgentStep]) -> FinalRecommendation | None:
    for step in sorted(steps, key=lambda item: item.step_index, reverse=True):
        payload = step.output_snapshot or {}
        candidate = payload.get("final_recommendation", payload if step.node_name == "generate_recommendation" else None)
        if isinstance(candidate, dict) and candidate.get("summary"):
            return FinalRecommendation.model_validate(candidate)
    return None


def create_agent_run(session: Session, *, alert_id: UUID) -> AgentRun:
    alert = session.get(Alert, alert_id)
    if alert is None:
        raise ValueError(f"Alert '{alert_id}' was not found.")

    agent_run = AgentRun(
        alert_id=alert_id,
        provenance="executed",
        execution_kind="agent_workflow",
        provider_version=PROVIDER_VERSION,
        policy_version=POLICY_VERSION,
        status="running",
        llm_provider="mock",
        model_version=RUNNER_MODEL_VERSION,
        total_steps=0,
        total_tool_calls=0,
        total_tokens_used=0,
        evidence_grounding_score=0.0,
        risk_level="medium",
        approval_status="pending",
        error_message=None,
        is_demo=alert.is_demo,
    )
    session.add(agent_run)
    session.flush()

    alert.agent_run_id = agent_run.id
    if alert.status == "new":
        alert.status = "investigating"
    session.add(alert)
    session.add(agent_run)
    session.commit()
    session.refresh(agent_run)
    return agent_run


def run_agent_for_alert(session: Session, *, alert_id: UUID) -> AgentRunResult:
    agent_run = create_agent_run(session, alert_id=alert_id)
    state = AgentState(alert_id=alert_id, agent_run_id=agent_run.id)

    try:
        ingest_alert(session, agent_run, state)
        classify_alert_node(session, agent_run, state)
        retrieve_context(session, agent_run, state)
        plan_tool_calls(session, agent_run, state)
        execute_safe_tools(session, agent_run, state)
        synthesize_hypotheses(session, agent_run, state)
        metacognitive_self_assessment(session, agent_run, state)
        generate_recommendation(session, agent_run, state)
        watchdog_policy_check(session, agent_run, state)
        wait_for_human_approval(session, agent_run, state)
        session.refresh(agent_run)
        return _state_result(state, agent_run)
    except Exception as exc:
        agent_run.status = "failed"
        agent_run.error_message = str(exc)
        if agent_run.completed_at is None:
            agent_run.completed_at = utcnow()
            agent_run.duration_seconds = round(
                (agent_run.completed_at - _ensure_aware(agent_run.started_at)).total_seconds(),
                2,
            )
        session.add(agent_run)
        session.commit()
        session.refresh(agent_run)
        return _state_result(state, agent_run)


def get_agent_run_detail(session: Session, *, agent_run_id: UUID) -> dict[str, object] | None:
    agent_run = session.get(AgentRun, agent_run_id)
    if agent_run is None:
        return None

    steps = session.exec(
        select(AgentStep)
        .where(AgentStep.agent_run_id == agent_run_id)
        .order_by(AgentStep.step_index)
    ).all()
    latest_assessment = _latest_self_assessment(session, agent_run_id)
    tool_calls = session.exec(
        select(ToolCall)
        .where(ToolCall.agent_run_id == agent_run_id)
        .order_by(ToolCall.created_at)
    ).all()

    assessment_payload = None
    if latest_assessment is not None:
        risk_flags: list[str] = []
        if "prompt_injection" in latest_assessment.capability_area:
            risk_flags.append("suspicious_retrieved_context")
        if latest_assessment.missing_evidence:
            risk_flags.append("missing_evidence")
        assessment_payload = AssessmentSnapshot(
            capability_area=latest_assessment.capability_area,
            confidence_score=latest_assessment.confidence_score,
            uncertainty_level=latest_assessment.uncertainty_level,
            what_agent_knows=latest_assessment.what_agent_knows,
            missing_evidence=latest_assessment.missing_evidence,
            within_capability=latest_assessment.within_capability,
            decision=latest_assessment.decision,
            rationale=latest_assessment.rationale,
            risk_flags=risk_flags,
            overridden_by_policy=latest_assessment.overridden_by_policy,
        )

    return {
        "agent_run": agent_run,
        "steps": steps,
        "tool_calls": tool_calls,
        "self_assessment": assessment_payload,
        "final_recommendation": _final_recommendation_from_steps(steps),
    }


def list_agent_runs(session: Session, *, limit: int = 20) -> list[AgentRun]:
    return session.exec(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)).all()
