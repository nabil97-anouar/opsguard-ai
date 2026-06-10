from __future__ import annotations

from app.watchdog.policies import iter_policy_handlers
from app.watchdog.schemas import PolicyDecisionStatus, PolicySeverity, WatchdogDecision, WatchdogFinding, WatchdogInput


def _severity_sort_value(severity: PolicySeverity) -> int:
    return {
        PolicySeverity.CRITICAL: 0,
        PolicySeverity.HIGH: 1,
        PolicySeverity.WARNING: 2,
        PolicySeverity.INFO: 3,
    }[severity]


def evaluate_watchdog(input: WatchdogInput) -> WatchdogDecision:
    findings: list[WatchdogFinding] = []

    for policy in iter_policy_handlers():
        findings.extend(policy.handler(input))

    findings.sort(key=lambda item: (_severity_sort_value(item.severity), item.policy_id))

    if any(item.status == "block" for item in findings):
        status = PolicyDecisionStatus.BLOCK
    elif any(item.status == "require_human_approval" for item in findings):
        status = PolicyDecisionStatus.REQUIRE_HUMAN_APPROVAL
    elif any(item.status == "warning" for item in findings):
        status = PolicyDecisionStatus.ALLOW_WITH_WARNINGS
    else:
        status = PolicyDecisionStatus.ALLOW

    if not findings:
        summary = "Watchdog found no policy violations."
    else:
        summary = (
            f"Watchdog status {status.value} with {len(findings)} finding(s): "
            + ", ".join(item.policy_id for item in findings)
        )

    return WatchdogDecision(status=status, summary=summary, findings=findings)
