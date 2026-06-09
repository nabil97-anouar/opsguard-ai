from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from sqlmodel import Session, select

from app.models import Document, DocumentChunk
from app.rag.injection import detect_prompt_injection
from app.rag.schemas import ListedDocument, RetrievalResult


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _build_metadata_text(document: Document, chunk: DocumentChunk) -> str:
    metadata = chunk.chunk_metadata or {}
    values: list[str] = [
        document.title,
        document.file_path or "",
        document.source_type,
        metadata.get("section") or "",
        metadata.get("doc_type") or "",
    ]
    return " ".join(values)


def _score_chunk(query: str, document: Document, chunk: DocumentChunk) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    query_counter = Counter(query_tokens)
    content_counter = Counter(_tokenize(chunk.content))
    metadata_counter = Counter(_tokenize(_build_metadata_text(document, chunk)))

    content_score = sum(query_counter[token] * min(content_counter[token], 3) for token in query_counter)
    metadata_score = sum(query_counter[token] * min(metadata_counter[token], 2) for token in query_counter)
    unique_overlap = len(
        {token for token in query_counter if content_counter[token] > 0 or metadata_counter[token] > 0}
    )
    phrase_boost = 0.0

    normalized_query = " ".join(query_tokens)
    haystacks = [
        " ".join(_tokenize(chunk.content)),
        " ".join(_tokenize(document.title)),
        " ".join(_tokenize(document.file_path or "")),
    ]
    if any(normalized_query and normalized_query in haystack for haystack in haystacks):
        phrase_boost = 1.5

    trust_boost = 0.15 if document.trust_level == "trusted" else 0.0
    length_penalty = math.sqrt(max(len(content_counter), 1))
    score = (content_score + metadata_score * 0.75 + unique_overlap * 0.5 + phrase_boost + trust_boost) / length_penalty
    return round(score, 4)


def _build_excerpt(content: str, query: str, max_chars: int = 280) -> str:
    normalized_content = " ".join(content.split())
    if len(normalized_content) <= max_chars:
        return normalized_content

    query_tokens = _tokenize(query)
    lower_content = normalized_content.lower()
    match_index = -1
    for token in query_tokens:
        match_index = lower_content.find(token)
        if match_index >= 0:
            break

    if match_index < 0:
        return f"{normalized_content[: max_chars - 3].rstrip()}..."

    start = max(match_index - max_chars // 3, 0)
    end = min(start + max_chars, len(normalized_content))
    excerpt = normalized_content[start:end].strip()
    if start > 0:
        excerpt = f"...{excerpt}"
    if end < len(normalized_content):
        excerpt = f"{excerpt}..."
    return excerpt


def _effective_scan(chunk: DocumentChunk) -> dict[str, Any]:
    metadata = chunk.chunk_metadata or {}
    matched_patterns = metadata.get("matched_patterns")
    risk_level = metadata.get("risk_level")
    injection_scan_result = metadata.get("injection_scan_result")

    if matched_patterns is not None and risk_level is not None and injection_scan_result is not None:
        return {
            "is_suspicious": injection_scan_result == "flagged",
            "matched_patterns": list(matched_patterns),
            "risk_level": str(risk_level),
        }

    return detect_prompt_injection(chunk.content)


def list_documents(session: Session) -> list[ListedDocument]:
    documents = session.exec(select(Document).order_by(Document.created_at.desc())).all()
    return [
        ListedDocument(
            id=document.id,
            title=document.title,
            source=document.file_path or "",
            doc_type=document.source_type,
            trust_level=document.trust_level,
            created_at=document.created_at,
        )
        for document in documents
    ]


def retrieve_chunks(
    session: Session,
    *,
    query: str,
    limit: int = 5,
    trust_filter: str | None = None,
    include_untrusted: bool = True,
) -> list[RetrievalResult]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    statement = select(DocumentChunk, Document).join(Document, Document.id == DocumentChunk.document_id)
    rows = session.exec(statement).all()
    results: list[RetrievalResult] = []

    for chunk, document in rows:
        effective_trust = chunk.trust_level or document.trust_level
        if document.trust_level == "quarantined" or effective_trust == "quarantined":
            continue
        if trust_filter and document.trust_level != trust_filter and effective_trust != trust_filter:
            continue
        if not include_untrusted and (document.trust_level != "trusted" or effective_trust != "trusted"):
            continue

        score = _score_chunk(normalized_query, document, chunk)
        if score <= 0:
            continue

        scan_result = _effective_scan(chunk)
        results.append(
            RetrievalResult(
                document_id=document.id,
                chunk_id=chunk.id,
                title=document.title,
                source=document.file_path or "",
                chunk_index=chunk.chunk_index,
                trust_level=effective_trust,
                doc_type=(chunk.chunk_metadata or {}).get("doc_type", document.source_type),
                score=score,
                content_excerpt=_build_excerpt(chunk.content, normalized_query),
                is_suspicious=bool(scan_result["is_suspicious"]),
                matched_patterns=list(scan_result["matched_patterns"]),
                risk_level=str(scan_result["risk_level"]),
                citation=f"{document.title} ({document.file_path or 'unknown source'}) chunk {chunk.chunk_index}",
            )
        )

    results.sort(
        key=lambda item: (
            -item.score,
            item.trust_level != "trusted",
            item.title.lower(),
            item.chunk_index,
        )
    )
    return results[:limit]
