"""Shared bounded incident contracts, independent of API schema package exports."""
from __future__ import annotations

import json
from ipaddress import ip_address
from typing import Annotated, ClassVar, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_INCIDENT_BODY_BYTES = 1024 * 1024
MAX_OBSERVATIONS = 32


class BundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    snapshot_budget: ClassVar[int] = 12000

    @field_validator("*", mode="after")
    @classmethod
    def reject_blank_strings(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("Supplied strings must not be blank.")
        return value

    @model_validator(mode="after")
    def bounded_snapshot(self):
        if len(json.dumps(self.model_dump(mode="json"), ensure_ascii=True).encode()) > self.snapshot_budget:
            raise ValueError(f"Input exceeds its {self.snapshot_budget}-byte serialized snapshot budget.")
        return self


class IncidentInput(BundleModel):
    # Incident metadata is repeated in the existing alert evidence envelope.
    # Reserve enough of its 16 KiB provider snapshot budget for both copies.
    snapshot_budget: ClassVar[int] = 4000
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=2000)
    severity: Literal["info", "warning", "high", "critical"]
    source: str = Field(min_length=1, max_length=100)
    observed_at: AwareDatetime | None = None
    infrastructure_type: str = Field(default="unknown", min_length=1, max_length=50)
    node: str | None = Field(default=None, min_length=1, max_length=100)
    job_id: str | None = Field(default=None, min_length=1, max_length=100)
    user: str | None = Field(default=None, min_length=1, max_length=100)


class ObservationBase(BundleModel):
    source: str = Field(min_length=1, max_length=100)
    observed_at: AwareDatetime | None = None
    node: str | None = Field(default=None, min_length=1, max_length=100)


class LogObservation(ObservationBase):
    kind: Literal["log"]
    message: str = Field(min_length=1, max_length=2000)
    severity: Literal["debug", "info", "warning", "error", "critical"] = "info"


class MetricObservation(ObservationBase):
    kind: Literal["metric"]
    name: str = Field(min_length=1, max_length=100)
    value: float = Field(strict=True, allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=40)


class JobObservation(ObservationBase):
    kind: Literal["job"]
    job_id: str = Field(min_length=1, max_length=100)
    user: str = Field(min_length=1, max_length=100)
    command: str = Field(min_length=1, max_length=2000)
    status: str = Field(min_length=1, max_length=50)


class NetworkObservation(ObservationBase):
    kind: Literal["network"]
    remote_ip: str = Field(min_length=1, max_length=45)
    remote_port: int = Field(strict=True, ge=1, le=65535)
    process: str | None = Field(default=None, max_length=200)

    @field_validator("remote_ip")
    @classmethod
    def valid_ip(cls, value: str) -> str:
        try:
            ip_address(value)
        except ValueError:
            raise ValueError("remote_ip must be an IPv4 or IPv6 address.") from None
        return value


IncidentObservation = Annotated[
    LogObservation | MetricObservation | JobObservation | NetworkObservation,
    Field(discriminator="kind"),
]


class IncidentBundleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal["incident-bundle-v1"]
    incident: IncidentInput
    observations: list[IncidentObservation] = Field(default_factory=list, max_length=MAX_OBSERVATIONS)


class IncidentImportResponse(BaseModel):
    status: Literal["imported"] = "imported"
    bundle_id: str
    alert_id: str
    observation_count: int
    trust_level: Literal["untrusted"] = "untrusted"
    imported_at: AwareDatetime
