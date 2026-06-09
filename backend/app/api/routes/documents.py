from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.init_db import create_db_and_tables
from app.db.session import get_session
from app.rag.ingestion import ingest_document
from app.rag.retrieval import list_documents
from app.schemas.rag import DocumentIngestRequest, DocumentIngestResponse, DocumentListItem

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=DocumentIngestResponse)
def ingest_document_route(
    request: DocumentIngestRequest,
    session: Session = Depends(get_session),
) -> DocumentIngestResponse:
    create_db_and_tables()
    try:
        result = ingest_document(
            session,
            title=request.title,
            source=request.source,
            doc_type=request.doc_type,
            trust_level=request.trust_level,
            content=request.content,
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DocumentIngestResponse(status="ok", **result)


@router.get("", response_model=list[DocumentListItem])
def list_documents_route(session: Session = Depends(get_session)) -> list[DocumentListItem]:
    create_db_and_tables()
    return [DocumentListItem(**document.__dict__) for document in list_documents(session)]
