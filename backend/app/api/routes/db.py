from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.db.init_db import create_db_and_tables
from app.db.session import check_database_connection
from app.schemas.db import CreateTablesResponse, DatabaseHealthResponse

router = APIRouter(prefix="/db", tags=["database"])


@router.get("/health", response_model=DatabaseHealthResponse)
def read_database_health() -> DatabaseHealthResponse:
    try:
        latency_ms = check_database_connection()
    except Exception as exc:  # pragma: no cover - exercised by integration failures
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return DatabaseHealthResponse(
        status="healthy",
        latency_ms=latency_ms,
        timestamp=datetime.now(UTC),
    )


@router.post("/create-tables", response_model=CreateTablesResponse)
def create_tables(settings: Settings = Depends(get_settings)) -> CreateTablesResponse:
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Table creation endpoint is disabled in production.",
        )

    tables = create_db_and_tables()
    return CreateTablesResponse(
        status="created",
        environment=settings.environment,
        tables=tables,
    )
