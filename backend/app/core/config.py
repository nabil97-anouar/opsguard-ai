from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
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

    llm_provider: Literal["deterministic", "openai", "institutional", "anthropic", "ollama"] = "deterministic"
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    institutional_llm_base_url: str | None = None
    institutional_llm_api_key: SecretStr | None = None
    institutional_llm_model: str | None = None
    institutional_llm_response_format: Literal["json_object", "json_schema"] = "json_object"
    institutional_llm_timeout_seconds: float | None = Field(default=None, ge=1, le=120)
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_timeout_seconds: float | None = Field(default=None, ge=1, le=120)
    ollama_model: str | None = None
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_api_key: SecretStr | None = None
    ollama_timeout_seconds: float | None = Field(default=None, ge=1, le=120)
    llm_timeout_seconds: float = Field(default=30.0, ge=1, le=120)
    llm_max_output_tokens: int = Field(default=1800, ge=256, le=8000)

    database_url: str = (
        "postgresql+psycopg://opsguard:opsguard@localhost:5432/opsguard_ai"
    )
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    @field_validator("institutional_llm_base_url", "anthropic_base_url", "ollama_base_url")
    @classmethod
    def validate_provider_base_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        # Accessing port validates malformed or out-of-range port strings too.
        port = parsed.port
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or "\\" in value or port == 0 or any(character.isspace() for character in value)):
            raise ValueError("Provider base URL must be an http(s) URL without credentials, query or fragment")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Provider base URL requires HTTPS except for loopback testing")
        # Keep the operator's path. API-compatible deployments do not all use /v1.
        return value

    @field_validator("anthropic_base_url", "ollama_base_url")
    @classmethod
    def require_native_base_url(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Provider base URL cannot be empty")
        return value

    @field_validator("anthropic_model", "ollama_model")
    @classmethod
    def validate_native_model(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if value != value.strip() or len(value) > 200 or any(ord(character) < 32 for character in value):
            raise ValueError("Chat model must be a nonempty deployment identifier")
        return value

    @field_validator("institutional_llm_model")
    @classmethod
    def validate_institutional_model(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if value != value.strip() or len(value) > 200 or any(ord(character) < 32 for character in value):
            raise ValueError("Institutional chat model must be a nonempty deployment identifier")
        if value == "gte-Qwen2-1.5B-instruct":
            raise ValueError("gte-Qwen2-1.5B-instruct is an embedding deployment, not a chat model")
        return value

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
