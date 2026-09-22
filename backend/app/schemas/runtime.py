from typing import Literal

from pydantic import BaseModel, Field

from app.agent.providers.base import ProviderModelOption


class ReasoningRuntimeResponse(BaseModel):
    provider: Literal["deterministic", "openai", "institutional", "anthropic", "ollama"]
    model: str
    mode: Literal["local", "external"]
    implementation_version: str
    schema_version: str
    configured: bool
    available: bool
    connectivity: Literal["local", "not_checked", "not_configured"]
    response_format: Literal["json_object", "json_schema"] | None = None
    model_options: list[ProviderModelOption] = Field(default_factory=list)
    reason: str | None = None
