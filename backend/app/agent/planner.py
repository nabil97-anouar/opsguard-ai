from __future__ import annotations

from typing import Any

from app.agent.state import AgentState, BlockedToolRecommendation, PlannedToolCall


def _node_from_state(state: AgentState) -> str:
    return str((state.alert_summary.raw_data if state.alert_summary else {}).get("node") or "gpu-node-14")


def _job_id_from_state(state: AgentState) -> str:
    return str((state.alert_summary.raw_data if state.alert_summary else {}).get("job_id") or "unknown-job")


def plan_tools_for_state(state: AgentState) -> tuple[list[PlannedToolCall], list[BlockedToolRecommendation]]:
    alert_type = str(state.alert_classification.get("alert_type") or "unknown")
    alert = state.alert_summary
    description = alert.description if alert else ""
    title = alert.title if alert else ""
    node = _node_from_state(state)
    job_id = _job_id_from_state(state)

    if alert_type == "suspicious_gpu_usage":
        return (
            [
                PlannedToolCall(
                    tool_name="search_logs",
                    input={"query": f"{title} xmrig mining pool {node}", "limit": 5},
                    rationale="Look for xmrig, pool traffic, and suspicious process evidence in seeded logs.",
                ),
                PlannedToolCall(
                    tool_name="get_node_metrics",
                    input={"node": node},
                    rationale="Confirm high GPU utilization and related node telemetry.",
                ),
                PlannedToolCall(
                    tool_name="get_running_jobs",
                    input={"node": node},
                    rationale="Check which running job is tied to the affected GPU node.",
                ),
                PlannedToolCall(
                    tool_name="check_network_connections",
                    input={"node": node, "limit": 10},
                    rationale="Look for suspicious outbound connections such as mining-pool ports.",
                ),
                PlannedToolCall(
                    tool_name="retrieve_runbook",
                    input={"query": "gpu abuse suspicious process xmrig outbound connections", "limit": 3, "include_untrusted": False},
                    rationale="Retrieve trusted runbook guidance for GPU-abuse response.",
                ),
            ],
            [
                BlockedToolRecommendation(
                    tool_name="cancel_job",
                    target=job_id,
                    rationale="Canceling the suspicious job may be necessary, but only with human approval after evidence review.",
                ),
                BlockedToolRecommendation(
                    tool_name="isolate_node",
                    target=node,
                    rationale="Isolating the node is potentially disruptive and must remain a human-approved action.",
                ),
            ],
        )

    if alert_type == "ssh_bruteforce":
        return (
            [
                PlannedToolCall(
                    tool_name="search_logs",
                    input={"query": f"{description} failed password root admin", "limit": 5},
                    rationale="Search seeded authentication logs for repeated SSH failures.",
                ),
                PlannedToolCall(
                    tool_name="retrieve_runbook",
                    input={"query": "ssh brute force response failed root admin login", "limit": 3, "include_untrusted": False},
                    rationale="Retrieve the trusted SSH brute-force response runbook.",
                ),
                PlannedToolCall(
                    tool_name="query_past_incidents",
                    input={"query": "ssh brute force authentication attack external IP", "limit": 3},
                    rationale="Compare the alert against prior authentication attack investigations.",
                ),
            ],
            [
                BlockedToolRecommendation(
                    tool_name="block_user",
                    target="root/admin",
                    rationale="Disabling user access is disruptive and requires explicit human approval.",
                )
            ],
        )

    if alert_type == "storage_inode_pressure":
        return (
            [
                PlannedToolCall(
                    tool_name="search_logs",
                    input={"query": f"{title} inode pressure scratch cache checkpoint", "limit": 5},
                    rationale="Collect seeded storage logs around inode pressure and scratch usage.",
                ),
                PlannedToolCall(
                    tool_name="retrieve_runbook",
                    input={"query": "storage inode pressure scratch cleanup runbook", "limit": 3, "include_untrusted": False},
                    rationale="Retrieve the trusted storage-pressure runbook.",
                ),
                PlannedToolCall(
                    tool_name="query_past_incidents",
                    input={"query": "storage inode exhaustion cache checkpoint growth", "limit": 3},
                    rationale="Use prior storage incidents to ground possible remediation.",
                ),
            ],
            [],
        )

    if alert_type == "rag_prompt_injection":
        return (
            [
                PlannedToolCall(
                    tool_name="retrieve_runbook",
                    input={"query": "system override ignore policies poisoned runbook", "limit": 5, "include_untrusted": True},
                    rationale="Retrieve both trusted and untrusted runbook content to surface the poisoning scenario explicitly.",
                ),
                PlannedToolCall(
                    tool_name="search_logs",
                    input={"query": "system override poisoned runbook ignore policies", "limit": 5},
                    rationale="Check whether seeded indexer logs show suspicious override markers.",
                ),
            ],
            [
                BlockedToolRecommendation(
                    tool_name="cancel_job",
                    target="cluster-wide",
                    rationale="The malicious content recommends canceling jobs, but that action must remain blocked pending human review.",
                ),
                BlockedToolRecommendation(
                    tool_name="disable_service",
                    target="safety controls",
                    rationale="Any proposal to disable safety controls must be rejected and kept recommendation-only.",
                ),
            ],
        )

    return (
        [
            PlannedToolCall(
                tool_name="search_logs",
                input={"query": f"{title} {description}".strip(), "limit": 5},
                rationale="Gather whatever deterministic log context is available for the unknown alert.",
            ),
            PlannedToolCall(
                tool_name="retrieve_runbook",
                input={"query": f"{title} {description}".strip(), "limit": 3, "include_untrusted": False},
                rationale="Attempt to find nearby runbook context without widening scope too aggressively.",
            ),
        ],
        [],
    )
