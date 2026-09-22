"""Server-owned bundle identity and access to immutable run input snapshots."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.models import AgentRun, AgentStep, Alert
from app.models.base import utcnow
from app.services.incident_schema import IncidentBundleInput, IncidentImportResponse

IMPORTED_EXECUTION_KIND = "incident_investigation"


def content_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def import_incident_bundle(session: Session, payload: IncidentBundleInput) -> IncidentImportResponse:
    from app.tools.hygiene import snapshot
    imported_at = utcnow()
    bundle_id = str(uuid4())
    incident = snapshot(payload.incident.model_dump(mode="json"))
    observations = []
    for item in payload.observations:
        observation = snapshot(item.model_dump(mode="json"))
        observations.append({"observation_id": str(uuid4()), "content_sha256": content_hash(observation),
                             "observation": observation})
    # Redaction can expand a short credential-like value. Validate the exact
    # persisted form before committing, so every accepted bundle remains usable.
    IncidentBundleInput.model_validate({"schema_version": payload.schema_version, "incident": incident,
                                      "observations": [row["observation"] for row in observations]})
    bundle = {"schema_version": payload.schema_version, "bundle_id": bundle_id,
              "imported_at": imported_at.isoformat(), "incident": incident, "observations": observations}
    alert = Alert(title=incident["title"], severity=incident["severity"],
                  source=incident["source"], infrastructure_type=incident["infrastructure_type"],
                  raw_data={"origin": "incident_bundle", "bundle": bundle,
                            "description": incident["description"]}, is_demo=False, tags=["imported-incident"])
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return IncidentImportResponse(bundle_id=bundle_id, alert_id=str(alert.id),
                                  observation_count=len(observations), imported_at=imported_at)


def validate_stored_bundle(value: dict) -> dict:
    """Fail closed on malformed persisted input; this is not tamper-proof storage."""
    UUID(value["bundle_id"])
    incident = value["incident"]
    rows = value["observations"]
    IncidentBundleInput.model_validate({"schema_version": value["schema_version"], "incident": incident,
                                      "observations": [row["observation"] for row in rows]})
    identities = set()
    for row in rows:
        identity = UUID(row["observation_id"])
        if identity in identities or content_hash(row["observation"]) != row["content_sha256"]:
            raise ValueError("Stored incident observation identity or content digest is inconsistent.")
        identities.add(identity)
    return deepcopy(value)


def recorded_bundle_for_run(session: Session, run_id: UUID) -> dict:
    run = session.get(AgentRun, run_id)
    if run is None or run.execution_kind != IMPORTED_EXECUTION_KIND:
        raise ValueError("An imported incident run is required.")
    step = session.exec(select(AgentStep).where(AgentStep.agent_run_id == run_id,
                                               AgentStep.node_name == "ingest_alert").order_by(AgentStep.step_index)).first()
    if step is None or not isinstance(step.output_snapshot.get("incident_bundle"), dict):
        raise ValueError("The run has no recorded incident bundle.")
    return validate_stored_bundle(step.output_snapshot["incident_bundle"])
