from __future__ import annotations

import json
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlmodel import Session, select

from app.models import AgentRun, AgentStep, SafetyEvent, ToolCall
from app.models.base import utcnow
from app.rag.injection import detect_prompt_injection


def start_timer() -> float:
    return perf_counter()


def elapsed_ms(started_at: float) -> int:
    return int(round((perf_counter() - started_at) * 1000))


def scan_tool_output(payload: Any) -> dict[str, Any]:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return detect_prompt_injection(serialized)


def _get_agent_run(session: Session, agent_run_id: UUID) -> AgentRun:
    agent_run = session.get(AgentRun, agent_run_id)
    if agent_run is None:
        raise ValueError(f"Agent run '{agent_run_id}' was not found.")
    return agent_run


def _resolve_step_id(session: Session, agent_run_id: UUID) -> UUID:
    agent_run = _get_agent_run(session, agent_run_id)

    execute_safe_tools_step = session.exec(
        select(AgentStep)
        .where(
            AgentStep.agent_run_id == agent_run_id,
            AgentStep.node_name == "execute_safe_tools",
        )
        .order_by(desc(AgentStep.step_index))
    ).first()
    if execute_safe_tools_step is not None:
        return execute_safe_tools_step.id

    latest_step = session.exec(
        select(AgentStep)
        .where(AgentStep.agent_run_id == agent_run_id)
        .order_by(desc(AgentStep.step_index))
    ).first()
    if latest_step is not None:
        return latest_step.id

    synthetic_step = AgentStep(
        agent_run_id=agent_run_id,
        step_index=max(agent_run.total_steps, 0) + 1,
        node_name="tool_registry_manual_execution",
        status="completed",
        input_snapshot={"source": "tool_registry"},
        output_snapshot={"status": "attached_for_audit"},
        duration_ms=0,
        error=None,
    )
    session.add(synthetic_step)
    agent_run.total_steps = max(agent_run.total_steps, synthetic_step.step_index)
    session.add(agent_run)
    session.flush()
    return synthetic_step.id


def record_tool_call(
    session: Session,
    *,
    agent_run_id: UUID | None,
    step_id: UUID | None = None,
    tool_name: str,
    input_args: dict[str, Any],
    output: Any,
    trust_level: str,
    status: str,
    duration_ms: int,
    error_message: str | None = None,
) -> ToolCall | None:
    if agent_run_id is None:
        return None

    resolved_step_id = step_id or _resolve_step_id(session, agent_run_id)
    scan_result = scan_tool_output(output)
    tool_call = ToolCall(
        agent_run_id=agent_run_id,
        step_id=resolved_step_id,
        tool_name=tool_name,
        input_args=input_args,
        output=output,
        trust_level=trust_level,
        duration_ms=duration_ms,
        status=status,
        error_message=error_message,
        injection_scan_result="flagged" if scan_result["is_suspicious"] else "clean",
    )
    session.add(tool_call)

    agent_run = _get_agent_run(session, agent_run_id)
    agent_run.total_tool_calls = (agent_run.total_tool_calls or 0) + 1
    session.add(agent_run)
    session.flush()
    return tool_call


def record_dangerous_tool_attempt(
    session: Session,
    *,
    tool_name: str,
    input_args: dict[str, Any],
    agent_run_id: UUID | None,
) -> SafetyEvent:
    event = SafetyEvent(
        agent_run_id=agent_run_id,
        harness_result_id=None,
        event_type="dangerous_tool_blocked",
        severity="error",
        source="tool_registry",
        affected_component=tool_name,
        details={
            "tool_name": tool_name,
            "input": input_args,
            "reason": "Dangerous infrastructure action requires human approval and is not executable by this tool registry.",
            "requires_human_approval": True,
            "recorded_at": utcnow().isoformat(),
        },
        pattern_matched=tool_name,
        resolved=True,
    )
    session.add(event)
    session.flush()
    return event
