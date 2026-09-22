from __future__ import annotations

from app.agent.providers.base import LLMProvider, ProviderIdentity
from app.agent.providers.deterministic import DeterministicProvider
from app.agent.providers.errors import ProviderConfigurationError
from app.agent.providers.openai_provider import OpenAIProvider
from app.agent.providers.anthropic_provider import AnthropicProvider, ANTHROPIC_IMPLEMENTATION_VERSION
from app.agent.providers.ollama_provider import OllamaProvider, OLLAMA_IMPLEMENTATION_VERSION, ollama_mode
from app.agent.providers.institutional import (
    InstitutionalProvider, INSTITUTIONAL_IMPLEMENTATION_VERSION, model_options,
)
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
    if settings.llm_provider == "institutional":
        key = settings.institutional_llm_api_key.get_secret_value() if settings.institutional_llm_api_key else ""
        if not key.strip() or not settings.institutional_llm_base_url or not settings.institutional_llm_model:
            raise ProviderConfigurationError("Institutional provider requires a key, base URL and chat model.")
        return InstitutionalProvider(
            api_key=key, base_url=settings.institutional_llm_base_url,
            model=settings.institutional_llm_model,
            timeout_seconds=settings.institutional_llm_timeout_seconds or settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
            response_format=settings.institutional_llm_response_format,
        )
    if settings.llm_provider == "anthropic":
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else ""
        if not key.strip() or not settings.anthropic_model:
            raise ProviderConfigurationError("Anthropic requires a key and model.")
        return AnthropicProvider(
            api_key=key, model=settings.anthropic_model, base_url=settings.anthropic_base_url,
            timeout_seconds=settings.anthropic_timeout_seconds or settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    if settings.llm_provider == "ollama":
        if not settings.ollama_model:
            raise ProviderConfigurationError("Ollama requires an installed chat model.")
        return OllamaProvider(
            model=settings.ollama_model, base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key.get_secret_value() if settings.ollama_api_key else None,
            timeout_seconds=settings.ollama_timeout_seconds or settings.llm_timeout_seconds,
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
            connectivity="not_checked" if configured else "not_configured",
            reason=None if configured else "OPENAI_API_KEY and OPENAI_MODEL are required.",
        )
    if settings.llm_provider == "institutional":
        configured = bool(
            settings.institutional_llm_api_key
            and settings.institutional_llm_api_key.get_secret_value().strip()
            and settings.institutional_llm_base_url and settings.institutional_llm_model
        )
        return ProviderIdentity(
            provider="institutional", model=settings.institutional_llm_model or "not-configured",
            mode="external", implementation_version=INSTITUTIONAL_IMPLEMENTATION_VERSION,
            configured=configured, available=configured,
            connectivity="not_checked" if configured else "not_configured",
            response_format=settings.institutional_llm_response_format,
            model_options=model_options(),
            reason=("Remote connectivity is not checked by this endpoint." if configured else
                    "INSTITUTIONAL_LLM_API_KEY, INSTITUTIONAL_LLM_BASE_URL and INSTITUTIONAL_LLM_MODEL are required."),
        )
    if settings.llm_provider == "anthropic":
        configured = bool(settings.anthropic_api_key and settings.anthropic_api_key.get_secret_value().strip()
                          and settings.anthropic_model)
        return ProviderIdentity(
            provider="anthropic", model=settings.anthropic_model or "not-configured", mode="external",
            implementation_version=ANTHROPIC_IMPLEMENTATION_VERSION,
            configured=configured, available=configured,
            connectivity="not_checked" if configured else "not_configured", response_format="json_schema",
            reason=("Remote connectivity is not checked by this endpoint." if configured else
                    "ANTHROPIC_API_KEY and ANTHROPIC_MODEL are required."),
        )
    if settings.llm_provider == "ollama":
        configured = bool(settings.ollama_model)
        return ProviderIdentity(
            provider="ollama", model=settings.ollama_model or "not-configured", mode=ollama_mode(settings.ollama_base_url),
            implementation_version=OLLAMA_IMPLEMENTATION_VERSION,
            configured=configured, available=configured,
            connectivity="not_checked" if configured else "not_configured", response_format="json_schema",
            reason=("Ollama connectivity and model installation are not checked by this endpoint." if configured else
                    "OLLAMA_MODEL must name a chat model installed on the configured Ollama server."),
        )
    raise ProviderConfigurationError("Unsupported reasoning provider.")
