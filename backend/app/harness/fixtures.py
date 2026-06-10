from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

from sqlmodel import Session, select

from app.agent.runner import create_agent_run
from app.models import AgentRun, Alert, SafetyEvent, ToolCall
from app.models.base import utcnow
from app.watchdog.schemas import WatchdogInput

HARNESS_NAMESPACE = UUID("a3fef4d2-2420-46de-87ae-18341494739f")
HARNESS_MODEL_VERSION = "security-harness-v1"


def harness_uuid(name: str) -> UUID:
    return uuid5(HARNESS_NAMESPACE, name)


def base_watchdog_input(**overrides: Any) -> WatchdogInput:
    payload = {
        "alert": {"severity": "warning", "title": "Safe operational note"},
        "retrieved_context": [],
        "tool_results": [],
        "hypotheses": [
            {
                "title": "Benign hypothesis",
                "summary": "This looks like a bounded operational issue.",
                "supporting_evidence": ["EVIDENCE-1"],
            }
        ],
        "evidence_items": [
            {
                "summary": "Trusted runbook excerpt",
                "citation": "Runbook A chunk 1",
                "trust_level": "trusted",
                "suspicious": False,
            }
        ],
        "planned_tools": [],
        "blocked_tools": [],
        "self_assessment": {
            "confidence_score": 0.9,
            "missing_evidence": [],
            "uncertainty_level": "low",
        },
        "final_recommendation": {
            "summary": "Review the trusted runbook and continue with human oversight.",
            "evidence": [
                {
                    "summary": "Trusted runbook excerpt",
                    "citation": "Runbook A chunk 1",
                    "trust_level": "trusted",
                    "suspicious": False,
                }
            ],
            "citations": ["Runbook A chunk 1"],
            "recommended_next_steps": ["Open a draft ticket for follow-up."],
            "blocked_actions_requiring_human_approval": [],
            "missing_evidence": [],
            "notes": [],
        },
    }
    payload.update(overrides)
    return WatchdogInput.model_validate(payload)


def create_harness_agent_run(
    session: Session,
    *,
    harness_run_id: UUID,
    scenario_id: str,
    title: str,
    description: str,
    severity: str = "warning",
    infrastructure_type: str = "security",
    source: str = "security-harness",
    raw_data: dict[str, Any] | None = None,
) -> AgentRun:
    alert_id = harness_uuid(f"{harness_run_id}:alert:{scenario_id}")
    alert = Alert(
        id=alert_id,
        title=title,
        severity=severity,
        source=source,
        infrastructure_type=infrastructure_type,
        raw_data={
            "description": description,
            "scenario_id": scenario_id,
            "harness_run_id": str(harness_run_id),
            **(raw_data or {}),
        },
        status="new",
        agent_run_id=None,
        tags=["security-harness", scenario_id],
        is_demo=False,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)

    agent_run = create_agent_run(session, alert_id=alert.id)
    agent_run.model_version = HARNESS_MODEL_VERSION
    agent_run.is_demo = False
    session.add(agent_run)
    session.commit()
    session.refresh(agent_run)
    return agent_run


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def finalize_harness_agent_run(
    session: Session,
    agent_run: AgentRun,
    *,
    status: str = "waiting_for_human",
    risk_level: str | None = None,
    approval_status: str = "pending",
    error_message: str | None = None,
) -> AgentRun:
    agent_run.status = status
    agent_run.approval_status = approval_status
    if risk_level is not None:
        agent_run.risk_level = risk_level
    agent_run.error_message = error_message
    completed_at = utcnow()
    agent_run.completed_at = completed_at
    agent_run.duration_seconds = round((completed_at - _ensure_aware(agent_run.started_at)).total_seconds(), 2)
    session.add(agent_run)
    session.commit()
    session.refresh(agent_run)
    return agent_run


def list_safety_events(session: Session, *, agent_run_id: UUID) -> list[SafetyEvent]:
    return session.exec(
        select(SafetyEvent)
        .where(SafetyEvent.agent_run_id == agent_run_id)
        .order_by(SafetyEvent.created_at)
    ).all()


def list_tool_calls(session: Session, *, agent_run_id: UUID) -> list[ToolCall]:
    return session.exec(
        select(ToolCall)
        .where(ToolCall.agent_run_id == agent_run_id)
        .order_by(ToolCall.created_at)
    ).all()


def serialize_safety_event(event: SafetyEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "agent_run_id": str(event.agent_run_id) if event.agent_run_id is not None else None,
        "harness_result_id": str(event.harness_result_id) if event.harness_result_id is not None else None,
        "event_type": event.event_type,
        "severity": event.severity,
        "source": event.source,
        "affected_component": event.affected_component,
        "details": event.details,
        "pattern_matched": event.pattern_matched,
        "resolved": event.resolved,
        "created_at": event.created_at.isoformat(),
    }


def serialize_tool_call(tool_call: ToolCall) -> dict[str, Any]:
    return {
        "id": str(tool_call.id),
        "tool_name": tool_call.tool_name,
        "status": tool_call.status,
        "trust_level": tool_call.trust_level,
        "input_args": tool_call.input_args,
        "output": tool_call.output,
        "injection_scan_result": tool_call.injection_scan_result,
        "created_at": tool_call.created_at.isoformat(),
    }
