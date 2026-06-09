from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "OpsGuard AI"
    project_description: str = (
        "Secure self-aware AI agents for incident triage and AI security testing."
    )
    project_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+psycopg://opsguard:opsguard@localhost:5432/opsguard_ai"
    )
    postgres_user: str = "opsguard"
    postgres_password: SecretStr = "opsguard"
    postgres_db: str = "opsguard_ai"
    qdrant_url: str = "http://localhost:6333"

    llm_provider: str = "mock"
    openai_api_key: SecretStr = ""
    anthropic_api_key: SecretStr = ""
    mock_llm: bool = True

    backend_cors_origins: list[str] = Field(
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
