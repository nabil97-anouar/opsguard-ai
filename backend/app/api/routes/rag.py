from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.init_db import create_db_and_tables
from app.db.session import get_session
from app.rag.retrieval import retrieve_chunks
from app.schemas.rag import RagRetrieveRequest, RagRetrieveResponse, RetrievalChunk

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/retrieve", response_model=RagRetrieveResponse)
def retrieve_rag_chunks(
    request: RagRetrieveRequest,
    session: Session = Depends(get_session),
) -> RagRetrieveResponse:
    create_db_and_tables()
    results = retrieve_chunks(
        session,
        query=request.query,
        limit=request.limit,
        trust_filter=request.trust_filter,
        include_untrusted=request.include_untrusted,
    )
    return RagRetrieveResponse(
        status="ok",
        query=request.query,
        results=[RetrievalChunk(**result.__dict__) for result in results],
    )
