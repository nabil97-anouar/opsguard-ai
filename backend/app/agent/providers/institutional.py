"""Explicit Chat Completions adapter; compatibility is configured, never inferred."""
from __future__ import annotations

import json
from time import perf_counter
from typing import Literal, TypeVar

from pydantic import BaseModel, ValidationError

from app.agent.providers.base import (
    LLMProvider, ProviderAssessment, ProviderCallResult, ProviderClassification,
    ProviderContext, ProviderHypotheses, ProviderIdentity, ProviderModelOption,
    ProviderRecommendation, validate_evidence_references,
)
from app.agent.providers.errors import (
    ProviderAuthenticationError, ProviderError, ProviderInvalidOutputError,
    ProviderRateLimitError, ProviderRefusalError, ProviderRequestError,
    ProviderTimeoutError, ProviderTruncatedOutputError, ProviderUnavailableError,
)
from app.agent.providers.prompts import SYSTEM_AUTHORITY, reasoning_prompt
from app.agent.providers.response_guard import reject_credential_echo

INSTITUTIONAL_IMPLEMENTATION_VERSION = "institutional-chat-v1"
# User-supplied deployment identifiers, not discovery or verified capability claims.
INSTITUTIONAL_CHAT_MODELS = (
    "gpt-oss-120b", "gemma-4-31B-it", "Llama-3.1-70B-Instruct",
    "Kimi-K2.6", "Mistral-Medium-3.5-128B",
)
T = TypeVar("T", bound=BaseModel)


def model_options() -> list[ProviderModelOption]:
    return [ProviderModelOption(id=model) for model in INSTITUTIONAL_CHAT_MODELS]


class InstitutionalProvider(LLMProvider):
    def __init__(
        self, *, api_key: str, base_url: str, model: str, timeout_seconds: float,
        max_output_tokens: int, response_format: Literal["json_object", "json_schema"], client=None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._max_output_tokens = max_output_tokens
        self._response_format = response_format
        if client is None:
            from openai import DefaultHttpxClient, OpenAI

            # Never auto-retry a potentially billable generation or redirect credentials
            # to another host. The operator configures the exact API base path.
            client = OpenAI(
                api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=0,
                http_client=DefaultHttpxClient(follow_redirects=False, timeout=timeout_seconds),
            )
        self._client = client

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider="institutional", model=self._model, mode="external",
            implementation_version=INSTITUTIONAL_IMPLEMENTATION_VERSION,
            connectivity="not_checked", response_format=self._response_format,
            model_options=model_options(),
        )

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

    def _call(self, context: ProviderContext, output_type: type[T]) -> ProviderCallResult[T]:
        started = perf_counter()
        schema = output_type.model_json_schema()
        response_format: dict[str, object] = {"type": self._response_format}
        if self._response_format == "json_schema":
            # This asks the server to apply a schema; it does not claim a particular
            # deployment supports strict structured decoding. Validate locally either way.
            response_format["json_schema"] = {"name": output_type.__name__, "schema": schema}
        prompt = reasoning_prompt(context) + "\n\nOUTPUT JSON SCHEMA\n" + json.dumps(schema)
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_AUTHORITY + " Return one JSON object matching the output schema."},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_format,
                max_tokens=self._max_output_tokens,
                stream=False,
            )
            choices = getattr(response, "choices", None)
            if not isinstance(choices, list) or len(choices) != 1:
                raise ProviderInvalidOutputError("Expected exactly one completion choice.")
            choice = choices[0]
            message = getattr(choice, "message", None)
            finish_reason = getattr(choice, "finish_reason", None)
            if message is None:
                raise ProviderInvalidOutputError("Completion choice is missing its message.")
            if getattr(message, "refusal", None) or finish_reason == "content_filter":
                raise ProviderRefusalError()
            if finish_reason == "length":
                raise ProviderTruncatedOutputError()
            if finish_reason != "stop" or getattr(message, "tool_calls", None) or getattr(message, "function_call", None):
                raise ProviderInvalidOutputError("Only completed JSON observations are accepted; no tool calls.")
            content = getattr(message, "content", None)
            if not isinstance(content, str) or not content.strip():
                raise ProviderInvalidOutputError("No JSON content was returned.")
            reject_credential_echo(self._api_key, content, getattr(response, "id", None), getattr(response, "model", None))
            value = output_type.model_validate_json(content, strict=True)
            reject_credential_echo(self._api_key, value)
            usage = getattr(response, "usage", None)
            return ProviderCallResult(
                value=value, duration_ms=max(0, int(round((perf_counter() - started) * 1000))),
                request_id=getattr(response, "id", None),
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                requested_model=self._model, served_model=getattr(response, "model", None),
            )
        except ProviderError:
            raise
        except (ValidationError, json.JSONDecodeError):
            raise ProviderInvalidOutputError("JSON did not satisfy the application schema.") from None
        except Exception as exc:
            # Do not expose SDK messages, request bodies, URLs or credentials.
            error_name = type(exc).__name__.casefold()
            status = getattr(exc, "status_code", None)
            if status in {401, 403}:
                raise ProviderAuthenticationError() from None
            if status == 429:
                raise ProviderRateLimitError() from None
            if "timeout" in error_name:
                raise ProviderTimeoutError() from None
            if status is not None and 300 <= status < 500:
                raise ProviderRequestError() from None
            raise ProviderUnavailableError() from None
