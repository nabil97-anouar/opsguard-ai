"""Bounded native HTTP transports with shared application output validation."""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypeVar

import httpx2 as httpx
from pydantic import BaseModel, ValidationError

from app.agent.providers.base import (
    LLMProvider, ProviderAssessment, ProviderCallResult, ProviderClassification,
    ProviderContext, ProviderHypotheses, ProviderRecommendation, validate_evidence_references,
)
from app.agent.providers.errors import (
    ProviderAuthenticationError, ProviderError, ProviderInvalidOutputError, ProviderRateLimitError,
    ProviderRequestError, ProviderTimeoutError, ProviderUnavailableError,
)
from app.agent.providers.response_guard import reject_credential_echo

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class NativeReply:
    content: str
    model: str | None = None
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


def optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def optional_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


class HTTPStructuredProvider(LLMProvider):
    """No SDK dependency in business logic and no implicit repairs or retries."""

    def __init__(
        self, *, base_url: str, model: str, timeout_seconds: float, max_output_tokens: int,
        headers: dict[str, str] | None = None, api_key: str | None = None, client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._headers = headers or {}
        self._api_key = api_key
        # An injected transport is for isolated contract tests; normal calls close
        # their own client so an investigation does not leave socket pools behind.
        self._client = client

    def classify(self, context: ProviderContext) -> ProviderCallResult[ProviderClassification]:
        return self._call(context, ProviderClassification)

    def hypothesize(self, context: ProviderContext) -> ProviderCallResult[ProviderHypotheses]:
        result = self._call(context, ProviderHypotheses)
        validate_evidence_references(context, hypotheses=result.value.hypotheses)
        return result

    def assess(self, context: ProviderContext) -> ProviderCallResult[ProviderAssessment]:
        return self._call(context, ProviderAssessment)

    def recommend(self, context: ProviderContext) -> ProviderCallResult[ProviderRecommendation]:
        result = self._call(context, ProviderRecommendation)
        validate_evidence_references(context, actions=result.value.proposed_actions)
        return result

    @abstractmethod
    def _generate(self, context: ProviderContext, schema: dict[str, Any]) -> NativeReply: ...

    def _call(self, context: ProviderContext, output_type: type[T]) -> ProviderCallResult[T]:
        started = perf_counter()
        try:
            reply = self._generate(context, output_type.model_json_schema())
            reject_credential_echo(self._api_key, reply.content, reply.model, reply.request_id)
            value = output_type.model_validate_json(reply.content, strict=True)
            reject_credential_echo(self._api_key, value)
        except ProviderError:
            raise
        except ValidationError:
            raise ProviderInvalidOutputError("JSON did not satisfy the application schema.") from None
        return ProviderCallResult(
            value=value, duration_ms=max(0, int(round((perf_counter() - started) * 1000))),
            request_id=reply.request_id, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
            requested_model=self._model, served_model=reply.model,
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Keep an explicitly configured reverse-proxy path rather than replacing it.
        url = self._base_url + path
        try:
            if self._client is None:
                with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False) as client:
                    response = client.post(url, json=payload, headers=self._headers)
            else:
                response = self._client.post(
                    url, json=payload, headers=self._headers,
                    timeout=self._timeout_seconds, follow_redirects=False,
                )
        except httpx.TimeoutException:
            raise ProviderTimeoutError() from None
        except httpx.RequestError:
            raise ProviderUnavailableError() from None
        except Exception:
            # A transport exception may include headers or response text.
            raise ProviderUnavailableError() from None
        if response.status_code in {401, 403}:
            raise ProviderAuthenticationError()
        if response.status_code == 429:
            raise ProviderRateLimitError()
        if response.status_code >= 500:
            raise ProviderUnavailableError()
        if response.status_code != 200:
            raise ProviderRequestError()
        try:
            body = response.json()
        except ValueError:
            raise ProviderInvalidOutputError("Response body was not JSON.") from None
        if not isinstance(body, dict):
            raise ProviderInvalidOutputError("Response envelope must be a JSON object.")
        return body
