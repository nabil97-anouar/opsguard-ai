from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlmodel import Session

from app.db.init_db import create_db_and_tables
from app.db.session import get_session
from app.schemas.tools import ToolExecuteRequest, ToolExecuteResponse, ToolListItem, ToolListResponse
from app.tools import ToolExecutionContext, UnknownToolError, execute_tool, list_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
def list_tool_definitions() -> ToolListResponse:
    create_db_and_tables()
    items = [
        ToolListItem(
            name=definition.name,
            description=definition.description,
            trust_level=definition.trust_level,
            allowed_use=list(definition.allowed_use),
            blocked_use=list(definition.blocked_use),
            requires_human_approval=definition.requires_human_approval,
            is_destructive=definition.is_destructive,
            input_schema=definition.input_schema.model_json_schema(),
            output_schema=definition.output_schema.model_json_schema(),
        )
        for definition in list_tools()
    ]
    return ToolListResponse(status="ok", items=items)


@router.post("/{tool_name}/execute", response_model=ToolExecuteResponse)
def execute_tool_route(
    tool_name: str,
    request: ToolExecuteRequest,
    session: Session = Depends(get_session),
) -> ToolExecuteResponse:
    create_db_and_tables()
    try:
        result = execute_tool(
            tool_name,
            request.input,
            session,
            ToolExecutionContext(agent_run_id=request.agent_run_id),
        )
    except UnknownToolError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    return ToolExecuteResponse(
        status=result.status,
        tool_name=result.tool_name,
        trust_level=result.trust_level,
        requires_human_approval=result.requires_human_approval,
        output=result.output,
        error=result.error,
        created_at=result.created_at,
    )
