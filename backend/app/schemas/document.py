from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CreatedAtSchema, IDSchema, SchemaModel, UpdatedAtSchema


class DocumentBase(SchemaModel):
    title: str
    source_type: str
    file_path: str | None = None
    content_hash: str | None = None
    trust_level: str
    tags: list[str] = Field(default_factory=list)
    infrastructure_type: str | None = None
    version: str | None = None
    is_demo: bool = False
    chunk_count: int = 0
    injection_scan_result: str


class DocumentRead(DocumentBase, IDSchema, UpdatedAtSchema):
    pass


class DocumentChunkBase(SchemaModel):
    document_id: UUID
    chunk_index: int
    content: str
    content_hash: str | None = None
    token_count: int = 0
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)
    trust_level: str
    injection_scan_result: str


class DocumentChunkRead(DocumentChunkBase, IDSchema, CreatedAtSchema):
    pass
