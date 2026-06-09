from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeAlias
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

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


@dataclass(frozen=True)
class ToolExecutionResult:
    status: str
    tool_name: str
    trust_level: str
    requires_human_approval: bool
    output: ToolResult
    error: str | None
    created_at: datetime


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    trust_level: str
    allowed_use: tuple[str, ...]
    blocked_use: tuple[str, ...]
    requires_human_approval: bool
    is_destructive: bool
    handler: ToolHandler
