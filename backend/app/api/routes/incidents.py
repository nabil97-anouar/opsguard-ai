from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlmodel import Session

from app.db.session import get_session
from app.services.incident_schema import IncidentBundleInput, IncidentImportResponse, MAX_INCIDENT_BODY_BYTES
from app.services.incident_bundles import import_incident_bundle

router = APIRouter(prefix="/incidents", tags=["incidents"])


def request_schema() -> dict:
    # Inline local definitions so the manual streaming body limit still exposes
    # a valid self-contained OpenAPI request schema, without dangling $defs refs.
    schema = IncidentBundleInput.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(value):
        if isinstance(value, dict):
            if "$ref" in value:
                return inline(definitions[value["$ref"].split("/")[-1]])
            # Discriminator mapping references are redundant with oneOf+const
            # after inlining and would otherwise point outside this schema.
            return {key: inline(item) for key, item in value.items() if key != "discriminator"}
        if isinstance(value, list):
            return [inline(item) for item in value]
        return value

    return inline(schema)


@router.post("/import", response_model=IncidentImportResponse, status_code=201,
             openapi_extra={"requestBody": {"required": True, "content": {
                 "application/json": {"schema": request_schema()}}}})
async def import_incident(request: Request, session: Session = Depends(get_session)) -> IncidentImportResponse:
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(status_code=415, detail="Incident bundles must use application/json.")
    # Consume incrementally before JSON parsing, including chunked requests.
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_INCIDENT_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Incident bundle exceeds the 1 MiB limit.")
        body.extend(chunk)
    try:
        payload = IncidentBundleInput.model_validate_json(body)
        return import_incident_bundle(session, payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[
            {"loc": ["body"], "type": error["type"],
             "msg": "Invalid incident bundle field; consult the versioned schema."}
            for error in exc.errors(include_input=False, include_context=False)
        ]) from None
