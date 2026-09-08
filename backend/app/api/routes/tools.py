from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from uuid import UUID
import json
from pydantic import ValidationError
from sqlmodel import Session, select
from app.models import ToolExecutionAudit
from app.models.base import utcnow
from app.tools.hygiene import snapshot

from app.db.session import get_session
from app.schemas.tools import ToolExecuteRequest, ToolExecuteResponse, ToolListItem, ToolListResponse
from app.tools import ToolExecutionContext, UnknownToolError, execute_tool, list_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
def list_tool_definitions() -> ToolListResponse:
    items = [
        ToolListItem(
            name=definition.name,
            description=definition.description,
            trust_level=definition.trust_level,
            allowed_use=list(definition.allowed_use),
            blocked_use=list(definition.blocked_use),
            requires_human_approval=definition.requires_human_approval,
            is_destructive=definition.is_destructive,
            executable=definition.executable,
            input_schema=definition.input_schema.model_json_schema(),
            output_schema=definition.output_schema.model_json_schema(),
        )
        for definition in list_tools()
    ]
    return ToolListResponse(status="ok", items=items)


@router.post("/{tool_name}/execute", response_model=ToolExecuteResponse,
    openapi_extra={"requestBody": {"required": True, "content": {"application/json": {"schema": ToolExecuteRequest.model_json_schema()}}}})
async def execute_tool_route(
    tool_name: str,
    request: Request,
    session: Session = Depends(get_session),
) -> ToolExecuteResponse:
    try:
        body = await request.body()
        if len(body) > 65536:
            raise ValueError("Request too large")
        raw = json.loads(body)
        envelope = ToolExecuteRequest.model_validate(raw)
    except (ValueError, ValidationError):
        # Preserve a parseable envelope identity even if its input is malformed;
        # never consult an inner payload for ownership.
        requested_run_id = None
        if "raw" in locals() and isinstance(raw, dict):
            try:
                requested_run_id = UUID(str(raw.get("agent_run_id")))
            except (ValueError, TypeError):
                pass
        audit = ToolExecutionAudit(tool_name=tool_name[:100], origin="api", outcome="denied",
            agent_run_id=requested_run_id,
            input_snapshot=snapshot(raw) if "raw" in locals() else {"malformed_request": True},
            error_code="malformed_request", user_error="Invalid tool request envelope.", completed_at=utcnow())
        with Session(session.get_bind()) as audit_session:
            audit_session.add(audit)
            audit_session.commit()
            audit_session.refresh(audit)
            audit_id = audit.id
        raise HTTPException(status_code=422, detail={"message": "Invalid tool request envelope.", "tool_call_id": str(audit_id), "outcome": "denied", "handler_invoked": False})
    try:
        result = execute_tool(
            tool_name,
            envelope.input,
            session,
            ToolExecutionContext(agent_run_id=envelope.agent_run_id),
        )
    except UnknownToolError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Requested tool is not registered.", "tool_call_id": str(exc.tool_call_id), "outcome": "denied", "handler_invoked": False},
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Tool input failed validation.", "tool_call_id": str(exc.tool_call_id), "outcome": "denied", "handler_invoked": False, "errors": exc.errors(include_input=False, include_context=False)},
        ) from exc

    return ToolExecuteResponse(
        handler_invoked=result.handler_invoked,
        error_code=result.error_code,
        status=result.status,
        outcome=result.outcome,
        tool_call_id=result.tool_call_id,
        tool_name=result.tool_name,
        trust_level=result.trust_level,
        requires_human_approval=result.requires_human_approval,
        output=result.output,
        error=result.error,
        created_at=result.created_at,
    )


@router.get("/attempts")
def list_tool_attempts(agent_run_id: UUID | None = None, session: Session = Depends(get_session)):
    query = select(ToolExecutionAudit)
    if agent_run_id is not None:
        query = query.where(ToolExecutionAudit.agent_run_id == agent_run_id)
    return {"items": session.exec(query.order_by(ToolExecutionAudit.requested_at.desc()).limit(100)).all()}
