from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import DependencyHealth, HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def read_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    provider_status = "mock" if settings.mock_llm else settings.llm_provider
    return HealthResponse(
        status="healthy",
        version=settings.project_version,
        environment=settings.environment,
        dependencies=DependencyHealth(
            postgres="configured",
            qdrant="configured",
            llm_provider=provider_status,
        ),
        timestamp=datetime.now(UTC),
    )
