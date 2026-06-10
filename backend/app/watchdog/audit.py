from __future__ import annotations

from sqlmodel import Session, select

from app.models import SafetyEvent
from app.watchdog.schemas import WatchdogDecision


def record_watchdog_decision(
    session: Session,
    *,
    agent_run_id,
    decision: WatchdogDecision,
) -> list[SafetyEvent]:
    if agent_run_id is None:
        return []

    existing_events = session.exec(
        select(SafetyEvent).where(
            SafetyEvent.agent_run_id == agent_run_id,
            SafetyEvent.source == "watchdog",
        )
    ).all()
    existing_policy_ids = {
        str((event.details or {}).get("policy_id"))
        for event in existing_events
        if (event.details or {}).get("policy_id")
    }

    created_events: list[SafetyEvent] = []
    for finding in decision.findings:
        if finding.severity == "info" or finding.policy_id in existing_policy_ids:
            continue

        event = SafetyEvent(
            agent_run_id=agent_run_id,
            harness_result_id=None,
            event_type="watchdog_policy_warning" if finding.status == "warning" else "watchdog_policy_violation",
            severity=finding.severity.value,
            source="watchdog",
            affected_component=finding.policy_id,
            details={
                "policy_id": finding.policy_id,
                "decision_status": finding.status,
                "reason": finding.reason,
                "evidence_refs": finding.evidence_refs,
                "remediation": finding.remediation,
                "metadata": finding.metadata,
            },
            pattern_matched=finding.policy_id,
            resolved=False,
        )
        session.add(event)
        created_events.append(event)
        existing_policy_ids.add(finding.policy_id)

    session.flush()
    return created_events
