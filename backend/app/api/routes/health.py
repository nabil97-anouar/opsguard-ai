from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import inspect

from app.core.config import Settings, get_settings
from app.db import session as db_session
from app.db.init_db import get_registered_table_names
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Process liveness only: no dependency connection, credentials or DDL."""
    return HealthResponse(status="healthy", version=settings.project_version,
        environment=settings.environment, timestamp=datetime.now(UTC))


@router.get("/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}})
def read_readiness(response: Response) -> ReadinessResponse:
    """Only SQL is required by the deterministic runtime. Never initializes it."""
    state = "ready"
    reason = None
    try:
        db_session.check_database_connection()
        inspector = inspect(db_session.engine)
        if set(get_registered_table_names()) - set(inspector.get_table_names()):
            state, reason = "schema_missing", "Database schema is incomplete; run the explicit initialization command."
        else:
            # Detect missing additive compatibility columns, without DDL privileges.
            from sqlmodel import SQLModel
            for name, table in SQLModel.metadata.tables.items():
                if set(table.columns.keys()) - {column["name"] for column in inspector.get_columns(name)}:
                    state, reason = "schema_missing", "Database schema needs the explicit compatibility initialization command."
                    break
    except Exception:
        state, reason = "unavailable", "Database is unavailable. Check connectivity and server-side configuration."
    if state != "ready":
        response.status_code = 503
    return ReadinessResponse(status="ready" if state == "ready" else "not_ready",
        database=state, reason=reason, timestamp=datetime.now(UTC))
