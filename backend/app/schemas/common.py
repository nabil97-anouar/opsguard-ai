from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SchemaModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDSchema(SchemaModel):
    id: UUID


class CreatedAtSchema(SchemaModel):
    created_at: datetime


class UpdatedAtSchema(CreatedAtSchema):
    updated_at: datetime
