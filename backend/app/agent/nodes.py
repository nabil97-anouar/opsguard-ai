from __future__ import annotations

from datetime import UTC, datetime
import json
from time import perf_counter
from typing import Any, Callable

from sqlmodel import Session

from app.agent.mock_llm import assess_confidence, classify_alert, generate_final_recommendation, generate_hypotheses
from app.agent.planner import plan_tools_for_state
from app.agent.schemas import StepExecutionSummary
from app.agent.state import (
    AgentState,
    AlertSummary,
    AssessmentSnapshot,
    EvidenceItem,
    FinalRecommendation,
    HypothesisItem,
    RetrievedContextItem,
    ToolResultItem,
)
from app.models import AgentRun, AgentStep, Alert, SafetyEvent, SelfAssessment
from app.models.base import utcnow
from app.rag.injection import detect_prompt_injection
from app.rag.retrieval import retrieve_chunks
from app.tools import ToolExecutionContext, execute_tool
from app.watchdog import WatchdogInput, evaluate_watchdog, record_watchdog_decision

NodeHandler = Callable[[AgentStep], dict[str, Any]]
NODE_ORDER = (
    "ingest_alert",
    "classify_alert",
    "retrieve_context",
    "plan_tool_calls",
    "execute_safe_tools",
    "synthesize_hypotheses",
    "metacognitive_self_assessment",
    "generate_recommendation",
    "watchdog_policy_check",
    "wait_for_human_approval",
)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_step_summary(step: AgentStep) -> StepExecutionSummary:
    return StepExecutionSummary(
        id=step.id,
        step_index=step.step_index,
        node_name=step.node_name,
        status=step.status,
        input_snapshot=step.input_snapshot,
        output_snapshot=step.output_snapshot,
        duration_ms=step.duration_ms,
        error=step.error,
        created_at=step.created_at,
    )


def _append_missing_evidence(state: AgentState, items: list[str]) -> None:
    for item in items:
        if item and item not in state.missing_evidence:
            state.missing_evidence.append(item)


def _record_safety_event(
    session: Session,
    *,
    agent_run_id,
    event_type: str,
    severity: str,
    source: str,
    affected_component: str,
    details: dict[str, Any],
    pattern_matched: str | None = None,
    resolved: bool = False,
) -> None:
    session.add(
        SafetyEvent(
            agent_run_id=agent_run_id,
            harness_result_id=None,
            event_type=event_type,
            severity=severity,
            source=source,
            affected_component=affected_component,
            details=details,
            pattern_matched=pattern_matched,
            resolved=resolved,
        )
    )


def _run_node(
    session: Session,
    agent_run: AgentRun,
    state: AgentState,
    node_name: str,
    input_snapshot: dict[str, Any],
    handler: NodeHandler,
    *,
    commit_started_step: bool = False,
) -> AgentState:
    started_at = utcnow()
    started_perf = perf_counter()
    step = AgentStep(
        agent_run_id=agent_run.id,
        step_index=len(state.steps) + 1,
        node_name=node_name,
        status="running",
        input_snapshot={**input_snapshot, "started_at": started_at.isoformat()},
        output_snapshot={},
        duration_ms=None,
        error=None,
    )
    session.add(step)
    agent_run.total_steps = max(agent_run.total_steps, step.step_index)
    session.add(agent_run)
    session.flush()

    if commit_started_step:
        session.commit()
        session.refresh(step)

    try:
        output_snapshot = handler(step)
    except Exception as exc:
        completed_at = utcnow()
        step.status = "failed"
        step.duration_ms = int(round((perf_counter() - started_perf) * 1000))
        step.error = str(exc)
        step.output_snapshot = {
            "completed_at": completed_at.isoformat(),
            "error": str(exc),
        }
        agent_run.error_message = str(exc)
        session.add(step)
        session.add(agent_run)
        session.commit()
        session.refresh(step)
        state.steps.append(_to_step_summary(step).model_dump(mode="json"))
        state.errors.append(str(exc))
        state.status = "failed"
        raise

    completed_at = utcnow()
    step.status = "completed"
    step.duration_ms = int(round((perf_counter() - started_perf) * 1000))
    step.output_snapshot = {
        **output_snapshot,
        "completed_at": completed_at.isoformat(),
    }
    session.add(step)
    session.add(agent_run)
    session.commit()
    session.refresh(step)
    state.steps.append(_to_step_summary(step).model_dump(mode="json"))
    return state


def ingest_alert(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        alert = session.get(Alert, state.alert_id)
        if alert is None:
            raise ValueError(f"Alert '{state.alert_id}' was not found.")

        description = str(alert.raw_data.get("description") or alert.title)
        state.alert_summary = AlertSummary(
            id=alert.id,
            title=alert.title,
            severity=alert.severity,
            source=alert.source,
            infrastructure_type=alert.infrastructure_type,
            status=alert.status,
            description=description,
            raw_data=alert.raw_data,
            tags=alert.tags,
        )
        state.evidence_items.append(
            EvidenceItem(
                evidence_id="ALERT-1",
                kind="alert",
                summary=description,
                citation=f"alert://{alert.id}",
                trust_level="untrusted",
                suspicious=False,
                source=alert.source,
            )
        )
        alert.agent_run_id = agent_run.id
        if alert.status == "new":
            alert.status = "investigating"
            state.alert_summary.status = alert.status
        agent_run.status = "running"
        agent_run.approval_status = "pending"
        session.add(alert)
        session.add(agent_run)

        return {
            "alert": state.alert_summary.model_dump(mode="json"),
            "evidence_added": 1,
        }

    return _run_node(
        session,
        agent_run,
        state,
        "ingest_alert",
        {"alert_id": str(state.alert_id)},
        handler,
    )


def classify_alert_node(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        if state.alert_summary is None:
            raise ValueError("Alert summary is required before classification.")

        classification = classify_alert(state.alert_summary.model_dump(mode="json"))
        state.alert_classification = classification
        _append_missing_evidence(state, list(classification.get("initial_missing_evidence", [])))
        agent_run.risk_level = str(classification.get("risk_level") or agent_run.risk_level)

        return classification

    return _run_node(
        session,
        agent_run,
        state,
        "classify_alert",
        {"alert_summary": state.alert_summary.model_dump(mode="json") if state.alert_summary else {}},
        handler,
    )


def retrieve_context(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        if state.alert_summary is None:
            raise ValueError("Alert summary is required before context retrieval.")

        classification = state.alert_classification
        query = " ".join(
            [
                str(classification.get("query_hint") or "").strip(),
                state.alert_summary.title,
                state.alert_summary.description,
                state.alert_summary.source,
            ]
        ).strip()
        include_untrusted = classification.get("alert_type") == "rag_prompt_injection"
        results = retrieve_chunks(
            session,
            query=query,
            limit=5,
            trust_filter=None,
            include_untrusted=include_untrusted,
        )

        if not results:
            _append_missing_evidence(state, ["Relevant retrieval context for the alert scenario"])

        state.retrieved_context = [RetrievedContextItem(**result.__dict__) for result in results]
        evidence_start = len(state.evidence_items) + 1
        suspicious_count = 0

        for index, item in enumerate(state.retrieved_context, start=evidence_start):
            state.evidence_items.append(
                EvidenceItem(
                    evidence_id=f"EVIDENCE-{index}",
                    kind="retrieval",
                    summary=item.content_excerpt,
                    citation=item.citation,
                    trust_level=item.trust_level,
                    suspicious=item.is_suspicious or item.trust_level != "trusted",
                    source=item.source,
                )
            )

            if item.is_suspicious or item.trust_level != "trusted":
                suspicious_count += 1
                suspicious_entry = {
                    "category": "retrieved_context",
                    "title": item.title,
                    "citation": item.citation,
                    "trust_level": item.trust_level,
                    "is_suspicious": item.is_suspicious,
                    "matched_patterns": item.matched_patterns,
                    "risk_level": item.risk_level,
                }
                state.suspicious_items.append(suspicious_entry)

                if item.is_suspicious:
                    _record_safety_event(
                        session,
                        agent_run_id=agent_run.id,
                        event_type="prompt_injection_detected",
                        severity="critical",
                        source="agent_retrieval",
                        affected_component="retrieved_context",
                        details=suspicious_entry,
                        pattern_matched=", ".join(item.matched_patterns) or None,
                        resolved=False,
                    )
                else:
                    _record_safety_event(
                        session,
                        agent_run_id=agent_run.id,
                        event_type="untrusted_retrieved_context_warning",
                        severity="warning",
                        source="agent_retrieval",
                        affected_component="retrieved_context",
                        details=suspicious_entry,
                        resolved=False,
                    )

        return {
            "query": query,
            "results": [item.model_dump(mode="json") for item in state.retrieved_context],
            "citations": [item.citation for item in state.retrieved_context],
            "suspicious_count": suspicious_count,
        }

    return _run_node(
        session,
        agent_run,
        state,
        "retrieve_context",
        {
            "alert_type": state.alert_classification.get("alert_type"),
            "missing_evidence": state.missing_evidence,
        },
        handler,
    )


def plan_tool_calls(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        planned_tools, blocked_tools = plan_tools_for_state(state)
        state.planned_tools = planned_tools
        state.blocked_tools = blocked_tools

        return {
            "planned_tools": [tool.model_dump(mode="json") for tool in planned_tools],
            "blocked_tools": [tool.model_dump(mode="json") for tool in blocked_tools],
        }

    return _run_node(
        session,
        agent_run,
        state,
        "plan_tool_calls",
        {"alert_type": state.alert_classification.get("alert_type")},
        handler,
    )


def execute_safe_tools(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(step: AgentStep) -> dict[str, Any]:
        suspicious_outputs = 0

        for planned_tool in state.planned_tools:
            if not planned_tool.safe_to_execute:
                continue

            result = execute_tool(
                planned_tool.tool_name,
                planned_tool.input,
                session,
                ToolExecutionContext(
                    agent_run_id=agent_run.id,
                    step_id=step.id,
                    invocation_source="agent_runner",
                ),
            )
            output_payload = result.output
            scan_result = detect_prompt_injection(json.dumps(output_payload, sort_keys=True, default=str))
            is_suspicious = bool(scan_result["is_suspicious"])
            trust_level = result.trust_level

            tool_result = ToolResultItem(
                tool_name=result.tool_name,
                status=result.status,
                trust_level=trust_level,
                requires_human_approval=result.requires_human_approval,
                output=output_payload,
                error=result.error,
                is_suspicious=is_suspicious,
                matched_patterns=list(scan_result["matched_patterns"]),
                risk_level=str(scan_result["risk_level"]),
            )
            state.tool_results.append(tool_result)
            state.executed_tools.append(result.tool_name)

            if result.status != "executed":
                _append_missing_evidence(state, [f"Successful output from tool {result.tool_name}"])

            if trust_level != "trusted" or is_suspicious:
                suspicious_outputs += 1
                suspicious_entry = {
                    "category": "tool_output",
                    "tool_name": result.tool_name,
                    "trust_level": trust_level,
                    "is_suspicious": is_suspicious,
                    "matched_patterns": list(scan_result["matched_patterns"]),
                    "risk_level": str(scan_result["risk_level"]),
                }
                state.suspicious_items.append(suspicious_entry)

                _record_safety_event(
                    session,
                    agent_run_id=agent_run.id,
                    event_type="tool_output_injection_detected" if is_suspicious else "untrusted_tool_output_warning",
                    severity="error" if is_suspicious else "warning",
                    source="agent_tool_executor",
                    affected_component=result.tool_name,
                    details=suspicious_entry,
                    pattern_matched=", ".join(scan_result["matched_patterns"]) or None,
                    resolved=False,
                )

            evidence_id = f"EVIDENCE-{len(state.evidence_items) + 1}"
            summary = f"Tool {result.tool_name} returned structured output."
            if result.tool_name == "search_logs" and output_payload.get("matches"):
                summary = str(output_payload["matches"][0].get("message") or summary)
            elif result.tool_name == "get_node_metrics":
                summary = (
                    f"Node {output_payload.get('node')} reported GPU utilization "
                    f"{output_payload.get('gpu_utilization')} percent."
                )
            elif result.tool_name == "get_running_jobs" and output_payload.get("jobs"):
                first_job = output_payload["jobs"][0]
                summary = f"Running job {first_job.get('job_id')} by {first_job.get('user')} is active on {first_job.get('node')}."
            elif result.tool_name == "check_network_connections" and output_payload.get("connections"):
                first_connection = output_payload["connections"][0]
                summary = (
                    f"Outbound connection to {first_connection.get('remote_ip')}:{first_connection.get('remote_port')} "
                    f"was observed for process {first_connection.get('process')}."
                )
            elif result.tool_name == "query_past_incidents" and output_payload.get("incidents"):
                summary = str(output_payload["incidents"][0].get("summary") or summary)
            elif result.tool_name == "retrieve_runbook" and output_payload.get("results"):
                summary = str(output_payload["results"][0].get("content_excerpt") or summary)

            state.evidence_items.append(
                EvidenceItem(
                    evidence_id=evidence_id,
                    kind="tool_output",
                    summary=summary,
                    citation=f"tool://{result.tool_name}",
                    trust_level=trust_level,
                    suspicious=trust_level != "trusted" or is_suspicious,
                    source=result.tool_name,
                )
            )

        trusted_evidence = len([item for item in state.evidence_items if item.trust_level == "trusted"])
        total_evidence = max(len(state.evidence_items), 1)
        agent_run.evidence_grounding_score = round(trusted_evidence / total_evidence, 2)

        return {
            "executed_tools": [item.model_dump(mode="json") for item in state.tool_results],
            "suspicious_outputs": suspicious_outputs,
        }

    return _run_node(
        session,
        agent_run,
        state,
        "execute_safe_tools",
        {"planned_tools": [tool.model_dump(mode="json") for tool in state.planned_tools]},
        handler,
        commit_started_step=True,
    )


def synthesize_hypotheses(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        alert_payload = state.alert_summary.model_dump(mode="json") if state.alert_summary else {}
        alert_payload["classification"] = state.alert_classification
        hypotheses = generate_hypotheses(
            alert_payload,
            [item.model_dump(mode="json") for item in state.retrieved_context],
            [item.model_dump(mode="json") for item in state.tool_results],
        )
        state.hypotheses = [HypothesisItem(**item) for item in hypotheses]
        if not state.hypotheses:
            _append_missing_evidence(state, ["A coherent working hypothesis"])

        return {
            "hypotheses": [item.model_dump(mode="json") for item in state.hypotheses],
        }

    return _run_node(
        session,
        agent_run,
        state,
        "synthesize_hypotheses",
        {
            "retrieved_context_count": len(state.retrieved_context),
            "tool_result_count": len(state.tool_results),
        },
        handler,
    )


def metacognitive_self_assessment(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(step: AgentStep) -> dict[str, Any]:
        alert_payload = state.alert_summary.model_dump(mode="json") if state.alert_summary else {}
        alert_payload["classification"] = state.alert_classification
        assessment = assess_confidence(
            alert_payload,
            [item.model_dump(mode="json") for item in state.evidence_items],
            state.suspicious_items,
            state.missing_evidence,
        )
        state.self_assessment = AssessmentSnapshot(**assessment)
        state.requires_human_approval = True

        session.add(
            SelfAssessment(
                agent_run_id=agent_run.id,
                step_id=step.id,
                capability_area=state.self_assessment.capability_area,
                confidence_score=state.self_assessment.confidence_score,
                uncertainty_level=state.self_assessment.uncertainty_level,
                what_agent_knows=state.self_assessment.what_agent_knows,
                missing_evidence=state.self_assessment.missing_evidence,
                within_capability=state.self_assessment.within_capability,
                decision=state.self_assessment.decision,
                rationale=state.self_assessment.rationale,
                overridden_by_policy=state.self_assessment.overridden_by_policy,
            )
        )

        return state.self_assessment.model_dump(mode="json")

    return _run_node(
        session,
        agent_run,
        state,
        "metacognitive_self_assessment",
        {
            "evidence_count": len(state.evidence_items),
            "suspicious_count": len(state.suspicious_items),
            "missing_evidence": state.missing_evidence,
        },
        handler,
    )


def generate_recommendation(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(step: AgentStep) -> dict[str, Any]:
        recommendation_payload = generate_final_recommendation(state.model_dump(mode="json"))
        state.final_recommendation = FinalRecommendation(**recommendation_payload)

        alert_type = str(state.alert_classification.get("alert_type") or "unknown")
        if alert_type != "unknown":
            ticket_title = f"OpsGuard AI draft: {state.alert_summary.title if state.alert_summary else alert_type}"
            ticket_body = "\n".join(
                [
                    state.final_recommendation.summary,
                    "",
                    "Recommended next steps:",
                    *[f"- {item}" for item in state.final_recommendation.recommended_next_steps],
                    "",
                    "Uncertainty:",
                    state.final_recommendation.uncertainty,
                ]
            )
            ticket_result = execute_tool(
                "create_ticket_draft",
                {
                    "agent_run_id": agent_run.id,
                    "title": ticket_title,
                    "body": ticket_body,
                },
                session,
                ToolExecutionContext(
                    agent_run_id=agent_run.id,
                    step_id=step.id,
                    invocation_source="agent_runner",
                ),
            )
            if ticket_result.status == "executed":
                state.final_recommendation.ticket_draft_id = str(ticket_result.output.get("ticket_draft_id"))

        return state.final_recommendation.model_dump(mode="json")

    return _run_node(
        session,
        agent_run,
        state,
        "generate_recommendation",
        {
            "self_assessment": state.self_assessment.model_dump(mode="json") if state.self_assessment else {},
            "blocked_tools": [tool.model_dump(mode="json") for tool in state.blocked_tools],
        },
        handler,
        commit_started_step=True,
    )


def watchdog_policy_check(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        alert_payload = state.alert_summary.model_dump(mode="json") if state.alert_summary else {}
        if state.alert_classification:
            alert_payload["classification"] = state.alert_classification

        watchdog_input = WatchdogInput(
            alert=alert_payload,
            retrieved_context=[item.model_dump(mode="json") for item in state.retrieved_context],
            tool_results=[item.model_dump(mode="json") for item in state.tool_results],
            hypotheses=[item.model_dump(mode="json") for item in state.hypotheses],
            evidence_items=[item.model_dump(mode="json") for item in state.evidence_items],
            planned_tools=[item.model_dump(mode="json") for item in state.planned_tools],
            blocked_tools=[item.model_dump(mode="json") for item in state.blocked_tools],
            self_assessment=(
                state.self_assessment.model_dump(mode="json") if state.self_assessment is not None else None
            ),
            final_recommendation=(
                state.final_recommendation.model_dump(mode="json") if state.final_recommendation is not None else None
            ),
        )
        decision = evaluate_watchdog(watchdog_input)
        record_watchdog_decision(session, agent_run_id=agent_run.id, decision=decision)
        state.watchdog_decision = decision.model_dump(mode="json")

        if state.final_recommendation is not None:
            state.final_recommendation.watchdog_status = decision.status.value
            state.final_recommendation.watchdog_summary = decision.summary
            state.final_recommendation.watchdog_findings = [
                finding.model_dump(mode="json") for finding in decision.findings
            ]
            if decision.status.value == "block":
                state.final_recommendation.summary = (
                    f"Blocked by watchdog pending human review. {state.final_recommendation.summary}"
                )
                if "Blocked by watchdog pending human review." not in state.final_recommendation.notes:
                    state.final_recommendation.notes.append("Blocked by watchdog pending human review.")
            else:
                state.final_recommendation.notes.append(f"Watchdog status: {decision.status.value}.")
            state.final_recommendation.requires_human_approval = True

        state.requires_human_approval = True
        if decision.status.value in {"block", "require_human_approval"}:
            state.status = "waiting_for_human"

        return {
            "watchdog_status": decision.status.value,
            "watchdog_summary": decision.summary,
            "findings": [finding.model_dump(mode="json") for finding in decision.findings],
            "final_recommendation": (
                state.final_recommendation.model_dump(mode="json") if state.final_recommendation else None
            ),
        }

    return _run_node(
        session,
        agent_run,
        state,
        "watchdog_policy_check",
        {
            "final_recommendation": (
                state.final_recommendation.model_dump(mode="json") if state.final_recommendation else {}
            ),
            "self_assessment": state.self_assessment.model_dump(mode="json") if state.self_assessment else {},
        },
        handler,
    )


def wait_for_human_approval(session: Session, agent_run: AgentRun, state: AgentState) -> AgentState:
    def handler(_: AgentStep) -> dict[str, Any]:
        agent_run.status = "waiting_for_human"
        agent_run.approval_status = "pending"
        agent_run.completed_at = utcnow()
        agent_run.duration_seconds = round(
            (agent_run.completed_at - _ensure_aware(agent_run.started_at)).total_seconds(),
            2,
        )
        state.requires_human_approval = True
        state.status = "waiting_for_human"
        if state.final_recommendation is not None:
            state.final_recommendation.requires_human_approval = True

        return {
            "requires_human_approval": True,
            "status": state.status,
            "final_recommendation": (
                state.final_recommendation.model_dump(mode="json") if state.final_recommendation else None
            ),
        }

    return _run_node(
        session,
        agent_run,
        state,
        "wait_for_human_approval",
        {"final_recommendation_ready": state.final_recommendation is not None},
        handler,
    )
