from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    project_name: str = "OpsGuard AI"
    project_description: str = (
        "Incident triage with evidence retrieval, typed local tools, and safety-policy checks."
    )
    project_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str = (
        "postgresql+psycopg://opsguard:opsguard@localhost:5432/opsguard_ai"
    )
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if value is None:
            return value

        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return []
            if candidate.startswith("["):
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in candidate.split(",") if item.strip()]

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        from sqlalchemy.engine import make_url
        try:
            url = make_url(value)
        except Exception:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy database URL") from None
        if url.drivername not in {"sqlite", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL supports sqlite or postgresql+psycopg only")
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/") or "?" in value or "#" in value:
            raise ValueError("API_V1_PREFIX must begin with / and have no trailing slash, query or fragment")
        return value

    @field_validator("backend_cors_origins")
    @classmethod
    def validate_origins(cls, value: list[str]) -> list[str]:
        from urllib.parse import urlsplit
        for origin in value:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                raise ValueError("CORS origins must be explicit http(s) origins without credentials or paths")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
