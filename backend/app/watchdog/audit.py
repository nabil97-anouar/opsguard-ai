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
    existing_finding_ids = {
        str((event.details or {}).get("finding_id"))
        for event in existing_events
        if (event.details or {}).get("finding_id")
    }

    created_events: list[SafetyEvent] = []
    for finding in decision.findings:
        if finding.severity == "info" or finding.finding_id in existing_finding_ids:
            continue

        event = SafetyEvent(
            agent_run_id=agent_run_id,
            harness_result_id=None,
            event_type="watchdog_policy_warning" if finding.status == "warning" else "watchdog_policy_violation",
            severity=finding.severity.value,
            source="watchdog",
            affected_component=finding.policy_id,
            details={
                "finding_id": finding.finding_id,
                "finding_type": finding.finding_type,
                "affected_action_ids": finding.affected_action_ids,
                "blocking": finding.blocking,
                "mandatory_review": finding.mandatory_review,
                "verdict": decision.verdict.value,
                "policy_version": decision.policy_version,
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
        existing_finding_ids.add(finding.finding_id)

    session.flush()
    return created_events
