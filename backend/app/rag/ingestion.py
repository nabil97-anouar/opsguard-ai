from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import delete
from sqlmodel import Session, select

from app.models import Document, DocumentChunk
from app.rag.chunking import chunk_text, split_sections
from app.rag.injection import detect_prompt_injection
from app.rag.schemas import IngestionResult

CHUNK_NAMESPACE = UUID("e1cbdfc5-45ca-4fd9-ac91-c038ce8e319d")


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _estimate_token_count(content: str) -> int:
    return max(1, int(len(content.split()) * 1.3))


def _stable_chunk_id(document_id: UUID, chunk_index: int, content_hash: str) -> UUID:
    return uuid5(CHUNK_NAMESPACE, f"{document_id}:{chunk_index}:{content_hash}")


def _section_chunks(content: str) -> list[tuple[str | None, str]]:
    sections = split_sections(content)
    chunk_records: list[tuple[str | None, str]] = []

    for heading, section_text in sections:
        for chunk in chunk_text(section_text):
            chunk_records.append((heading, chunk))

    if not chunk_records:
        return [(None, chunk) for chunk in chunk_text(content)]
    return chunk_records


def ingest_document(
    session: Session,
    *,
    title: str,
    source: str,
    doc_type: str,
    trust_level: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, object]:
    normalized_title = title.strip()
    normalized_source = source.strip()
    normalized_doc_type = doc_type.strip()
    normalized_content = content.strip()
    metadata = metadata or {}

    if not normalized_title or not normalized_source or not normalized_doc_type:
        raise ValueError("title, source, and doc_type are required.")
    if not normalized_content:
        raise ValueError("content cannot be empty.")

    existing_document = session.exec(
        select(Document).where(
            Document.title == normalized_title,
            Document.file_path == normalized_source,
        )
    ).first()

    content_hash = _hash_text(normalized_content)
    tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
    infrastructure_type = metadata.get("infrastructure_type")
    version = metadata.get("version")
    is_demo = bool(metadata.get("is_demo", False))

    created = existing_document is None
    updated = False
    skipped = False
    content_changed = created

    if existing_document is None:
        document = Document(
            title=normalized_title,
            source_type=normalized_doc_type,
            file_path=normalized_source,
            content_hash=content_hash,
            trust_level=trust_level,
            tags=[str(tag) for tag in tags],
            infrastructure_type=str(infrastructure_type) if infrastructure_type else None,
            version=str(version) if version else None,
            is_demo=is_demo,
            chunk_count=0,
            injection_scan_result="pending",
        )
        session.add(document)
        session.flush()
    else:
        document = existing_document
        content_changed = document.content_hash != content_hash
        if (
            document.content_hash == content_hash
            and document.source_type == normalized_doc_type
            and document.trust_level == trust_level
            and document.file_path == normalized_source
            and document.tags == [str(tag) for tag in tags]
            and document.infrastructure_type == (str(infrastructure_type) if infrastructure_type else None)
            and document.version == (str(version) if version else None)
        ):
            skipped = True
            return IngestionResult(
                document_id=document.id,
                created=False,
                updated=False,
                skipped=True,
                chunk_count=document.chunk_count,
            ).__dict__

        updated = True
        document.source_type = normalized_doc_type
        document.file_path = normalized_source
        document.trust_level = trust_level
        document.tags = [str(tag) for tag in tags]
        document.infrastructure_type = str(infrastructure_type) if infrastructure_type else None
        document.version = str(version) if version else None
        document.is_demo = is_demo

        if content_changed:
            session.exec(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

        document.content_hash = content_hash

    should_rechunk = created or content_changed or document.chunk_count == 0

    if should_rechunk:
        section_chunks = _section_chunks(normalized_content)
        chunk_models: list[DocumentChunk] = []
        document_risk_levels: list[str] = []

        for chunk_index, (section_heading, chunk_content) in enumerate(section_chunks, start=1):
            scan_result = detect_prompt_injection(chunk_content)
            document_risk_levels.append(str(scan_result["risk_level"]))
            chunk_hash = _hash_text(chunk_content)

            chunk_models.append(
                DocumentChunk(
                    id=_stable_chunk_id(document.id, chunk_index, chunk_hash),
                    document_id=document.id,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    content_hash=chunk_hash,
                    token_count=_estimate_token_count(chunk_content),
                    chunk_metadata={
                        "source": normalized_source,
                        "doc_type": normalized_doc_type,
                        "trust_level": trust_level,
                        "section": section_heading,
                        "injection_scan_result": "flagged"
                        if scan_result["is_suspicious"]
                        else "clean",
                        "matched_patterns": scan_result["matched_patterns"],
                        "risk_level": scan_result["risk_level"],
                        "document_metadata": metadata,
                    },
                    trust_level=trust_level,
                    injection_scan_result="flagged"
                    if scan_result["is_suspicious"]
                    else "clean",
                )
            )

        for chunk_model in chunk_models:
            session.add(chunk_model)

        document.chunk_count = len(chunk_models)
        document.injection_scan_result = (
            "flagged" if "high" in document_risk_levels or "medium" in document_risk_levels else "clean"
        )

    session.add(document)
    session.commit()
    session.refresh(document)

    return IngestionResult(
        document_id=document.id,
        created=created,
        updated=updated,
        skipped=skipped,
        chunk_count=document.chunk_count,
    ).__dict__
