from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas.demo import DemoSeedRequest, DemoSeedResponse
from app.services.demo_seed import seed_demo_data

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed", response_model=DemoSeedResponse)
def seed_demo_dataset(
    request: DemoSeedRequest,
    settings: Settings = Depends(get_settings),
) -> DemoSeedResponse:
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding is disabled in production.",
        )

    summary = seed_demo_data(reset=request.reset)
    return DemoSeedResponse(
        status="ok",
        message="demo data seeded",
        summary=summary,
    )
