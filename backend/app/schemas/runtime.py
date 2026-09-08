from typing import Literal

from pydantic import BaseModel


class ReasoningRuntimeResponse(BaseModel):
    provider: Literal["deterministic", "openai"]
    model: str
    mode: Literal["local", "external"]
    implementation_version: str
    schema_version: str
    configured: bool
    available: bool
    reason: str | None = None
