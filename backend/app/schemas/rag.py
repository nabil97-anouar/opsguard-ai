from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.rag.trust import TrustLevel, ingestion_trust


class DocumentIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=500)
    doc_type: str = Field(min_length=1, max_length=50)
    trust_level: Literal[TrustLevel.UNTRUSTED, TrustLevel.QUARANTINED] = TrustLevel.UNTRUSTED
    content: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_public_trust(self) -> DocumentIngestRequest:
        ingestion_trust(self.trust_level, self.metadata)
        return self


class DocumentIngestResponse(BaseModel):
    status: Literal["ok"]
    document_id: UUID
    created: bool
    updated: bool
    skipped: bool
    chunk_count: int


class DocumentListItem(BaseModel):
    id: UUID
    title: str
    source: str
    doc_type: str
    trust_level: TrustLevel
    created_at: datetime


class RagRetrieveRequest(BaseModel):
    query: str = Field(max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    trust_filter: TrustLevel | None = None
    include_untrusted: bool = True


class RetrievalChunk(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    source: str
    chunk_index: int
    trust_level: TrustLevel
    doc_type: str
    score: float
    content_excerpt: str
    is_suspicious: bool
    matched_patterns: list[str]
    risk_level: str
    citation: str


class RagRetrieveResponse(BaseModel):
    status: Literal["ok"]
    query: str
    results: list[RetrievalChunk]
