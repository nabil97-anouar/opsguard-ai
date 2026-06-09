from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class IngestionResult:
    document_id: UUID
    created: bool
    updated: bool
    skipped: bool
    chunk_count: int


@dataclass(frozen=True)
class RetrievalResult:
    document_id: UUID
    chunk_id: UUID
    title: str
    source: str
    chunk_index: int
    trust_level: str
    doc_type: str
    score: float
    content_excerpt: str
    is_suspicious: bool
    matched_patterns: list[str]
    risk_level: str
    citation: str


@dataclass(frozen=True)
class ListedDocument:
    id: UUID
    title: str
    source: str
    doc_type: str
    trust_level: str
    created_at: datetime
