from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

JSON_SQL_TYPE = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


def json_column(*, nullable: bool = False, name: str | None = None) -> Column[Any]:
    if name is None:
        return Column(JSON_SQL_TYPE, nullable=nullable)
    return Column(name, JSON_SQL_TYPE, nullable=nullable)


def timestamp_column(
    *,
    nullable: bool = False,
    index: bool = False,
    onupdate: bool = False,
    name: str | None = None,
) -> Column[datetime]:
    column_kwargs: dict[str, Any] = {"nullable": nullable, "index": index}
    if onupdate:
        column_kwargs["onupdate"] = utcnow

    if name is None:
        return Column(DateTime(timezone=True), **column_kwargs)
    return Column(name, DateTime(timezone=True), **column_kwargs)


class UUIDPrimaryKeyMixin(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)


class CreatedAtMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": False, "index": True},
    )


class UpdatedAtMixin(CreatedAtMixin):
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"nullable": False, "onupdate": utcnow},
    )
