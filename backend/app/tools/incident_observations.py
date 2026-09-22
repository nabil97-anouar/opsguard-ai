"""Read one bounded observation from a run's already-persisted bundle."""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from app.services.incident_schema import IncidentObservation
from app.services.incident_bundles import recorded_bundle_for_run
from app.tools.base import ToolExecutionContext


class ReadIncidentObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_id: UUID


class ReadIncidentObservationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bundle_id: UUID
    observation_id: UUID
    content_sha256: str
    observation: IncidentObservation
    trust_level: Literal["untrusted"] = "untrusted"


def read_incident_observation_handler(
    validated_input: ReadIncidentObservationInput, session: Session, context: ToolExecutionContext,
) -> dict[str, Any]:
    if context.agent_run_id is None:
        raise ValueError("A recorded incident run is required.")
    bundle = recorded_bundle_for_run(session, context.agent_run_id)
    for record in bundle["observations"]:
        if record["observation_id"] == str(validated_input.observation_id):
            return {"bundle_id": bundle["bundle_id"], **record, "trust_level": "untrusted"}
    raise ValueError("Observation does not belong to this run's recorded incident bundle.")
