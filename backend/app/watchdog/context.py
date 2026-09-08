"""Load the source ledger for API policy previews; supplied evidence is not authority."""
from sqlmodel import Session, select
from app.models import AgentRun, AgentStep, ToolCall
from app.watchdog.schemas import WatchdogInput


def persisted_watchdog_context(session: Session, candidate: WatchdogInput) -> WatchdogInput:
    data = candidate.model_dump(mode="python")
    ledger = []
    observations = []
    if candidate.agent_run_id and session.get(AgentRun, candidate.agent_run_id):
        steps = session.exec(select(AgentStep).where(AgentStep.agent_run_id == candidate.agent_run_id,
            AgentStep.status == "completed").order_by(AgentStep.step_index)).all()
        calls = session.exec(select(ToolCall).where(ToolCall.agent_run_id == candidate.agent_run_id)).all()
        calls_by_id = {str(call.id): call for call in calls}
        for step in steps:
            if step.node_name not in {"ingest_alert", "retrieve_context", "execute_safe_tools"}:
                continue
            for item in (step.output_snapshot or {}).get("evidence_items", []):
                item = dict(item)
                if item.get("kind") == "tool_output":
                    call = calls_by_id.get(str(item.get("tool_call_id")))
                    if call is None or call.status != "executed" or call.handler_invoked is not True or call.output != item.get("content"):
                        item["observation_status"] = "invalid"
                ledger.append(item)
        observations = [{"tool_call_id": str(call.id), "tool_name": call.tool_name,
            "status": call.status, "output": call.output, "trust_level": call.trust_level,
            "injection_scan_result": call.injection_scan_result} for call in calls]
    data["evidence_items"] = ledger
    # Supplied observations still undergo pattern screening. Only persisted calls
    # may validate a tool reference (last observation for an ID is authoritative).
    data["tool_results"] = [{**item, "status": "unverified"} for item in candidate.tool_results] + observations
    return WatchdogInput.model_validate(data)
