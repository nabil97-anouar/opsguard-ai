from fastapi import APIRouter, Depends

from app.agent.providers import provider_status
from app.core.config import Settings, get_settings
from app.schemas.runtime import ReasoningRuntimeResponse

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/reasoning", response_model=ReasoningRuntimeResponse)
def read_reasoning_runtime(settings: Settings = Depends(get_settings)) -> ReasoningRuntimeResponse:
    """Return provider identity and configuration state without credentials."""
    return ReasoningRuntimeResponse.model_validate(provider_status(settings), from_attributes=True)
