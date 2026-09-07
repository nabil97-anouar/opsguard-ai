from __future__ import annotations

import re
from collections import Counter
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from app.models import AgentRun, Alert, Incident, TicketDraft
from app.rag.retrieval import retrieve_chunks
from app.rag.trust import TrustLevel
from app.tools.base import ToolExecutionContext
from app.tools.mock_data import (
    MOCK_LOG_ENTRIES,
    MOCK_NETWORK_CONNECTIONS,
    MOCK_NODE_METRICS,
    MOCK_RUNNING_JOBS,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(value: str) -> list[str]:
    return TOKEN_PATTERN.findall(value.lower())


def _score_text(query: str, *fields: str) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    haystack = " ".join(fields)
    haystack_tokens = _tokenize(haystack)
    if not haystack_tokens:
        return 0.0

    query_counter = Counter(query_tokens)
    haystack_counter = Counter(haystack_tokens)
    weighted_overlap = sum(query_counter[token] * min(haystack_counter[token], 3) for token in query_counter)
    unique_overlap = len({token for token in query_counter if haystack_counter[token] > 0})
    phrase = " ".join(query_tokens)
    phrase_boost = 1.5 if phrase and phrase in " ".join(haystack_tokens) else 0.0
    return round(weighted_overlap + unique_overlap * 0.35 + phrase_boost, 4)


def _truncate(value: str, max_chars: int = 280) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."


def _assigned_team_for_alert(alert: Alert) -> str:
    if alert.infrastructure_type == "security":
        return "Security Operations"
    if alert.infrastructure_type == "gpu_cluster":
        return "Platform Security"
    if alert.infrastructure_type == "hpc":
        return "HPC Operations"
    return "Ops Team"


def _sla_target_for_severity(severity: str) -> str:
    return {
        "critical": "P1 within 15 minutes",
        "high": "P1 within 30 minutes",
        "warning": "P2 within 4 hours",
        "info": "P3 within 1 business day",
    }.get(severity, "P2 within 4 hours")


class SearchLogsInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class SearchLogMatch(BaseModel):
    timestamp: str
    source: str
    host: str
    message: str
    severity: str


class SearchLogsOutput(BaseModel):
    matches: list[SearchLogMatch]
    total: int


def search_logs_handler(
    validated_input: SearchLogsInput,
    _: Session,
    __: ToolExecutionContext,
) -> dict[str, Any]:
    scored_matches: list[tuple[float, dict[str, str]]] = []
    for entry in MOCK_LOG_ENTRIES:
        score = _score_text(
            validated_input.query,
            entry["message"],
            entry["source"],
            entry["host"],
            entry["severity"],
        )
        if score <= 0:
            continue
        scored_matches.append((score, entry))

    scored_matches.sort(key=lambda item: (-item[0], item[1]["timestamp"]), reverse=False)
    matches = [
        {
            "timestamp": entry["timestamp"],
            "source": entry["source"],
            "host": entry["host"],
            "message": entry["message"],
            "severity": entry["severity"],
        }
        for _, entry in scored_matches[: validated_input.limit]
    ]
    return {"matches": matches, "total": len(scored_matches)}


class GetNodeMetricsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    node: str = Field(min_length=1, max_length=100)


class GetNodeMetricsOutput(BaseModel):
    node: str
    gpu_utilization: float
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    cpu_load: float
    network_tx_mb_s: float
    network_rx_mb_s: float
    timestamp: str


def get_node_metrics_handler(
    validated_input: GetNodeMetricsInput,
    _: Session,
    __: ToolExecutionContext,
) -> dict[str, Any]:
    metrics = MOCK_NODE_METRICS.get(validated_input.node)
    if metrics is None:
        raise ValueError(f"No mock metrics are available for node '{validated_input.node}'.")
    return dict(metrics)


class GetRunningJobsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    node: str | None = Field(default=None, min_length=1, max_length=100)
    user: str | None = Field(default=None, min_length=1, max_length=100)


class RunningJob(BaseModel):
    job_id: str
    user: str
    node: str
    command: str
    gpu_count: int
    runtime_minutes: int
    status: str


class GetRunningJobsOutput(BaseModel):
    jobs: list[RunningJob]
    total: int


def get_running_jobs_handler(
    validated_input: GetRunningJobsInput,
    _: Session,
    __: ToolExecutionContext,
) -> dict[str, Any]:
    jobs = [
        job
        for job in MOCK_RUNNING_JOBS
        if (validated_input.node is None or job["node"] == validated_input.node)
        and (validated_input.user is None or job["user"] == validated_input.user)
    ]
    return {"jobs": [dict(job) for job in jobs], "total": len(jobs)}


class CheckNetworkConnectionsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    node: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=20, ge=1, le=100)


class NetworkConnection(BaseModel):
    remote_ip: str
    remote_port: int
    process: str
    risk: str
    reason: str


class CheckNetworkConnectionsOutput(BaseModel):
    connections: list[NetworkConnection]
    total: int


def check_network_connections_handler(
    validated_input: CheckNetworkConnectionsInput,
    _: Session,
    __: ToolExecutionContext,
) -> dict[str, Any]:
    connections = list(MOCK_NETWORK_CONNECTIONS.get(validated_input.node, ()))
    return {
        "connections": [dict(connection) for connection in connections[: validated_input.limit]],
        "total": len(connections),
    }


class QueryPastIncidentsInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=25)


class PastIncidentSummary(BaseModel):
    id: str
    title: str
    status: str
    summary: str
    root_cause: str


class QueryPastIncidentsOutput(BaseModel):
    incidents: list[PastIncidentSummary]
    total: int


def query_past_incidents_handler(
    validated_input: QueryPastIncidentsInput,
    session: Session,
    _: ToolExecutionContext,
) -> dict[str, Any]:
    incidents = session.exec(select(Incident).order_by(Incident.created_at.desc())).all()
    scored: list[tuple[float, Incident]] = []
    for incident in incidents:
        score = _score_text(
            validated_input.query,
            incident.title,
            incident.status,
            incident.root_cause,
            incident.resolution,
            incident.kill_chain_stage or "",
        )
        if score <= 0:
            continue
        scored.append((score, incident))

    scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
    results = [
        {
            "id": str(incident.id),
            "title": incident.title,
            "status": incident.status,
            "summary": _truncate(incident.resolution),
            "root_cause": incident.root_cause,
        }
        for _, incident in scored[: validated_input.limit]
    ]
    return {"incidents": results, "total": len(scored)}


class RetrieveRunbookInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    include_untrusted: bool = False


class RunbookRetrievalResult(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    source: str
    chunk_index: int
    trust_level: TrustLevel
    score: float
    content_excerpt: str
    is_suspicious: bool
    matched_patterns: list[str]
    risk_level: str
    citation: str


class RetrieveRunbookOutput(BaseModel):
    results: list[RunbookRetrievalResult]
    total: int


def retrieve_runbook_handler(
    validated_input: RetrieveRunbookInput,
    session: Session,
    _: ToolExecutionContext,
) -> dict[str, Any]:
    candidates = retrieve_chunks(
        session,
        query=validated_input.query,
        limit=max(validated_input.limit * 3, validated_input.limit),
        trust_filter=None,
        include_untrusted=validated_input.include_untrusted,
    )
    runbook_results = [result for result in candidates if result.doc_type == "runbook"]
    payload = [
        {
            "document_id": str(result.document_id),
            "chunk_id": str(result.chunk_id),
            "title": result.title,
            "source": result.source,
            "chunk_index": result.chunk_index,
            "trust_level": result.trust_level,
            "score": result.score,
            "content_excerpt": result.content_excerpt,
            "is_suspicious": result.is_suspicious,
            "matched_patterns": result.matched_patterns,
            "risk_level": result.risk_level,
            "citation": result.citation,
        }
        for result in runbook_results[: validated_input.limit]
    ]
    return {"results": payload, "total": len(runbook_results)}


class CreateTicketDraftInput(BaseModel):
    agent_run_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=5000)


class CreateTicketDraftOutput(BaseModel):
    ticket_draft_id: str
    status: str
    title: str


def create_ticket_draft_handler(
    validated_input: CreateTicketDraftInput,
    session: Session,
    _: ToolExecutionContext,
) -> dict[str, Any]:
    if validated_input.agent_run_id is None:
        raise ValueError("agent_run_id is required to persist a ticket draft with the current data model.")

    agent_run = session.get(AgentRun, validated_input.agent_run_id)
    if agent_run is None:
        raise ValueError(f"Agent run '{validated_input.agent_run_id}' was not found.")

    alert = session.get(Alert, agent_run.alert_id)
    if alert is None:
        raise ValueError(f"Alert '{agent_run.alert_id}' was not found for agent run '{agent_run.id}'.")

    ticket_draft = TicketDraft(
        agent_run_id=agent_run.id,
        alert_id=alert.id,
        title=validated_input.title,
        severity=alert.severity,
        description=validated_input.body,
        steps_to_reproduce=[
            f"Review alert {alert.id}",
            f"Review agent run {agent_run.id}",
        ],
        suggested_actions=[
            {"action": "review_ticket_draft", "approval_required": True},
        ],
        evidence_links=[
            f"alert://{alert.id}",
            f"agent-run://{agent_run.id}",
        ],
        kill_chain_stage=None,
        assigned_team=_assigned_team_for_alert(alert),
        sla_target=_sla_target_for_severity(alert.severity),
        exported=False,
    )
    session.add(ticket_draft)
    session.flush()

    return {
        "ticket_draft_id": str(ticket_draft.id),
        "status": "draft",
        "title": ticket_draft.title,
    }


class DangerousToolInput(BaseModel):
    model_config = ConfigDict(extra="allow")


class BlockedToolOutput(BaseModel):
    status: str
    reason: str
    requires_human_approval: bool


def blocked_tool_handler(
    _: DangerousToolInput,
    __: Session,
    ___: ToolExecutionContext,
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "Dangerous infrastructure action requires human approval and is not executable by this tool registry.",
        "requires_human_approval": True,
    }
