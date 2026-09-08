from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal, TypeAlias, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from app.rag.trust import TrustLevel

if TYPE_CHECKING:
    from app.watchdog.schemas import WatchdogDecision

ToolInput: TypeAlias = dict[str, Any]
ToolResult: TypeAlias = dict[str, Any]
ToolHandler: TypeAlias = Callable[[BaseModel, Session, "ToolExecutionContext"], ToolResult]


class UnknownToolError(LookupError):
    """Raised when a requested tool is not present in the immutable registry."""


@dataclass(frozen=True)
class ToolExecutionContext:
    agent_run_id: UUID | None = None
    step_id: UUID | None = None
    invocation_source: str = "api"
    policy_decision: WatchdogDecision | None = None


@dataclass(frozen=True)
class ToolExecutionResult:
    status: Literal["executed", "failed", "blocked"]
    tool_name: str
    trust_level: TrustLevel
    requires_human_approval: bool
    output: ToolResult
    error: str | None
    created_at: datetime
    tool_call_id: UUID | None = None
    handler_invoked: bool = False
    error_code: str | None = None

    @property
    def outcome(self) -> Literal["succeeded", "failed", "denied"]:
        return {"executed": "succeeded", "blocked": "denied", "failed": "failed"}[self.status]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    trust_level: TrustLevel
    allowed_use: tuple[str, ...]
    blocked_use: tuple[str, ...]
    requires_human_approval: bool
    is_destructive: bool
    handler: ToolHandler | None

    @property
    def executable(self) -> bool:
        return self.handler is not None and not self.is_destructive and not self.requires_human_approval
