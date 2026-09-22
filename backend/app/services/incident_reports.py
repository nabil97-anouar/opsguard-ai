"""Historical investigation exports; never retrieve current operational context."""
from __future__ import annotations

import html
import json
import re
from uuid import UUID

from sqlmodel import Session, select

from app.models import AgentRun, AgentStep, ToolExecutionAudit


def build_incident_report(session: Session, run_id: UUID) -> dict | None:
    run = session.get(AgentRun, run_id)
    if run is None:
        return None
    if run.status == "running" or run.completed_at is None:
        raise ValueError("The investigation must finish before exporting its historical report.")
    steps = session.exec(select(AgentStep).where(AgentStep.agent_run_id == run_id,
                                               AgentStep.created_at <= run.completed_at)
                         .order_by(AgentStep.step_index, AgentStep.id)).all()
    evidence = {}
    incident = None
    source_bundle = None
    recommendation = None
    assessment = None
    hypotheses = []
    gaps = []
    for step in steps:
        output = step.output_snapshot or {}
        if step.node_name == "ingest_alert":
            incident = output.get("alert")
            source_bundle = output.get("incident_bundle")
        if step.node_name in {"ingest_alert", "retrieve_context", "execute_safe_tools"}:
            for item in output.get("evidence_items", []):
                if isinstance(item, dict) and item.get("evidence_id"):
                    evidence[item["evidence_id"]] = item
        if step.node_name == "synthesize_hypotheses":
            hypotheses = output.get("hypotheses", [])
        if step.node_name == "metacognitive_self_assessment":
            assessment = output
        if step.node_name == "generate_recommendation" and output.get("summary"):
            recommendation = output
        if isinstance(output.get("final_recommendation"), dict):
            recommendation = output["final_recommendation"]
        gaps.extend(str(gap) for gap in output.get("missing_evidence", []))
    gaps.extend((recommendation or {}).get("missing_evidence", []))
    # Later standalone API attempts against this run are audit history, not part
    # of its finished investigation. Do not let them rewrite a historical report.
    attempts = session.exec(select(ToolExecutionAudit).where(
        ToolExecutionAudit.agent_run_id == run_id, ToolExecutionAudit.origin == "agent_runner",
        ToolExecutionAudit.requested_at <= run.completed_at,
    ).order_by(ToolExecutionAudit.requested_at, ToolExecutionAudit.id)).all()
    run_snapshot = run.model_dump(mode="json")
    # The runtime counter also includes later API attempts; this export's count
    # covers only the original workflow attempts included in this report.
    run_snapshot["total_tool_calls"] = len(attempts)
    run_snapshot["total_steps"] = len(steps)
    return {
        "schema_version": "incident-report-v1", "agent_run_id": str(run.id),
        "run": run_snapshot, "incident": incident, "source_bundle": source_bundle,
        "evidence": list(evidence.values()), "hypotheses": hypotheses, "self_assessment": assessment,
        "final_recommendation": recommendation, "missing_evidence": list(dict.fromkeys(gaps)),
        "tool_attempts": [row.model_dump(mode="json") for row in attempts],
        "steps": [row.model_dump(mode="json") for row in steps],
        "limitations": [
            "This report uses only persisted run input, steps, evidence and original workflow attempts.",
            "Imported observations remain untrusted; content snapshots are not authenticated or tamper-proof.",
            "Evidence references establish identity, not semantic support or root-cause correctness.",
            "Human review is terminal. No infrastructure action or live connector is implied.",
            "Credential-like strings are redacted by the bounded snapshot serializer; this is not comprehensive data-loss prevention.",
        ],
    }


def _text(value: object) -> str:
    return re.sub(r"([\\`*{}\[\]()#+.!|>_-])", r"\\\1", html.escape(str(value)))


def _json_block(value: object) -> str:
    content = json.dumps(value, indent=2, ensure_ascii=False)
    fence = "`" * max(3, 1 + max((len(match) for match in re.findall(r"`+", content)), default=0))
    return f"{fence}json\n{content}\n{fence}"


def render_incident_markdown(report: dict) -> str:
    run = report["run"]
    recommendation = report["final_recommendation"] or {}
    incident = report["incident"] or {}
    lines = ["# OpsGuard incident report", "", f"Run: `{report['agent_run_id']}`", "",
             f"Incident: {_text(incident.get('title', 'No recorded incident snapshot'))}", "",
             f"Status: {_text(run['status'])}", "",
             f"Reasoning: {_text(run['llm_provider'])} / {_text(run.get('model_version'))}", "",
             f"Policy version: {_text(run.get('policy_version'))}", "",
             "## Recorded recommendation", "", _text(recommendation.get("summary", "No recommendation was recorded.")), "",
             f"Lifecycle: {_text(recommendation.get('lifecycle_state', 'not recorded'))}", "",
             f"Watchdog: {_text(recommendation.get('watchdog_status', 'not recorded'))}", "",
             "## Missing evidence", ""]
    lines.extend(f"- {_text(gap)}" for gap in report["missing_evidence"])
    if not report["missing_evidence"]:
        lines.append("No missing-evidence entries were recorded; this does not establish completeness.")
    lines.extend(["", "## Recorded evidence", ""])
    if not report["evidence"]:
        lines.append("No supporting evidence was persisted for this run. No fresh retrieval was performed.")
    for item in report["evidence"]:
        time_label = {
            "source_observation": "Observed at source",
            "recorded": "Recorded by OpsGuard (source event time unknown)",
        }.get(item.get("timestamp_basis"), "Stored timestamp (basis not recorded)")
        lines.extend([f"### {_text(item['evidence_id'])}", "", f"Source: {_text(item.get('source'))}", "",
                      f"{time_label}: {_text(item.get('observed_at'))} · Trust: {_text(item.get('trust_level'))}", "",
                      _json_block(item), ""])
    lines.extend(["## Structured findings and actions", "", _json_block(recommendation), "",
                  "## Original workflow tool attempts", "", _json_block(report["tool_attempts"]), "",
                  "## Limitations", ""])
    lines.extend(f"- {_text(item)}" for item in report["limitations"])
    return "\n".join(lines) + "\n"
