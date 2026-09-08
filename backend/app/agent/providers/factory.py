from __future__ import annotations

from app.agent.providers.base import LLMProvider, ProviderIdentity
from app.agent.providers.deterministic import DeterministicProvider
from app.agent.providers.errors import ProviderConfigurationError
from app.agent.providers.openai_provider import OpenAIProvider
from app.core.config import Settings, get_settings


def create_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "deterministic":
        return DeterministicProvider()
    if settings.llm_provider == "openai":
        key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
        if not key or not settings.openai_model:
            raise ProviderConfigurationError("OpenAI requires a key and model.")
        return OpenAIProvider(
            api_key=key,
            model=settings.openai_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    raise ProviderConfigurationError("Unsupported reasoning provider.")


def provider_status(settings: Settings | None = None) -> ProviderIdentity:
    settings = settings or get_settings()
    if settings.llm_provider == "deterministic":
        return DeterministicProvider().identity
    if settings.llm_provider == "openai":
        configured = bool(settings.openai_api_key and settings.openai_model)
        return ProviderIdentity(
            provider="openai",
            model=settings.openai_model or "not-configured",
            mode="external",
            implementation_version="openai-responses-v1",
            configured=configured,
            available=configured,
            reason=None if configured else "OPENAI_API_KEY and OPENAI_MODEL are required.",
        )
    raise ProviderConfigurationError("Unsupported reasoning provider.")
