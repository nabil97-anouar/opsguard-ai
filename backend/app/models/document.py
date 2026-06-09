from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin, json_column


class Document(UUIDPrimaryKeyMixin, UpdatedAtMixin, table=True):
    __tablename__ = "documents"

    title: str = Field(max_length=500)
    source_type: str = Field(max_length=50, index=True)
    file_path: str | None = Field(default=None, max_length=500)
    content_hash: str | None = Field(default=None, max_length=64, index=True)
    trust_level: str = Field(default="untrusted", max_length=20, index=True)
    tags: list[str] = Field(default_factory=list, sa_column=json_column())
    infrastructure_type: str | None = Field(default=None, max_length=50, index=True)
    version: str | None = Field(default=None, max_length=20)
    is_demo: bool = Field(default=False, index=True)
    chunk_count: int = 0
    injection_scan_result: str = Field(default="pending", max_length=20, index=True)


class DocumentChunk(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    __tablename__ = "document_chunks"

    document_id: UUID = Field(foreign_key="documents.id", index=True)
    chunk_index: int = Field(index=True)
    content: str
    content_hash: str | None = Field(default=None, max_length=64, index=True)
    token_count: int = 0
    chunk_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=json_column(name="metadata"),
    )
    trust_level: str = Field(default="untrusted", max_length=20, index=True)
    injection_scan_result: str = Field(default="pending", max_length=20)
