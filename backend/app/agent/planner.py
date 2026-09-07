from __future__ import annotations

from app.agent.state import AgentState, BlockedToolRecommendation, PlannedToolCall


def _target_from_state(state: AgentState, field: str) -> str | None:
    value = (state.alert_summary.raw_data if state.alert_summary else {}).get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if field == "job_id" and isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    gap = f"Alert does not identify a valid {field}; target-specific checks and actions were omitted."
    if field not in state.missing_targets:
        state.missing_targets.append(field)
    if gap not in state.missing_evidence:
        state.missing_evidence.append(gap)
    return None


def plan_tools_for_state(state: AgentState) -> tuple[list[PlannedToolCall], list[BlockedToolRecommendation]]:
    alert_type = str(state.alert_classification.get("alert_type") or "unknown")
    alert = state.alert_summary
    description = alert.description if alert else ""
    title = alert.title if alert else ""
    if alert_type == "suspicious_gpu_usage":
        node = _target_from_state(state, "node")
        job_id = _target_from_state(state, "job_id")
        tools = [
            PlannedToolCall(
                tool_name="search_logs",
                input={"query": f"{title} xmrig mining pool {node or ''}".strip(), "limit": 5},
                rationale="Look for xmrig, pool traffic, and suspicious process evidence in local logs.",
            ),
        ]
        if node is not None:
            tools.extend([
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
            ])
        tools.append(
            PlannedToolCall(
                tool_name="retrieve_runbook",
                input={"query": "gpu abuse suspicious process xmrig outbound connections", "limit": 3, "include_untrusted": False},
                rationale="Retrieve trusted runbook guidance for GPU-abuse response.",
            )
        )
        blocked: list[BlockedToolRecommendation] = []
        if job_id is not None:
            blocked.append(
                BlockedToolRecommendation(
                    tool_name="cancel_job",
                    target=job_id,
                    rationale="Canceling the suspicious job may be necessary, but only with human approval after evidence review.",
                )
            )
        if node is not None:
            blocked.append(
                BlockedToolRecommendation(
                    tool_name="isolate_node",
                    target=node,
                    rationale="Isolating the node is potentially disruptive and must remain a human-approved action.",
                )
            )
        return tools, blocked

    if alert_type == "ssh_bruteforce":
        user = _target_from_state(state, "user")
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
                    target=user,
                    rationale="Disabling user access is disruptive and requires explicit human approval.",
                )
            ] if user is not None else [],
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
            [],
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
