"""Anthropic Messages API with constrained output and full local validation."""
from __future__ import annotations

import json
from typing import Any

import httpx2 as httpx

from app.agent.providers.base import ProviderContext, ProviderIdentity
from app.agent.providers.errors import ProviderInvalidOutputError, ProviderRefusalError, ProviderTruncatedOutputError
from app.agent.providers.http_structured import HTTPStructuredProvider, NativeReply, optional_count, optional_text
from app.agent.providers.prompts import SYSTEM_AUTHORITY, reasoning_prompt

ANTHROPIC_IMPLEMENTATION_VERSION = "anthropic-messages-v1"


def anthropic_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Translate unsupported constraints; the original schema remains authoritative.

    Anthropic requires closed objects and does not support numeric/length bounds.
    Free-form action parameter maps are restricted to empty objects for this adapter;
    candidate details can still be stated in rationale for human review.
    """
    unsupported = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
                   "minLength", "maxLength", "minItems", "maxItems"}

    def transform(value: Any) -> Any:
        if isinstance(value, list):
            return [transform(item) for item in value]
        if not isinstance(value, dict):
            return value
        output = {key: transform(item) for key, item in value.items() if key not in unsupported}
        constraints = {key: item for key, item in value.items() if key in unsupported}
        if constraints:
            output["description"] = (str(output.get("description", "")) +
                                     " Application validates: " + json.dumps(constraints)).strip()
        if value.get("type") == "object":
            output["additionalProperties"] = False
            output.setdefault("properties", {})
        return output

    return transform(schema)


class AnthropicProvider(HTTPStructuredProvider):
    def __init__(
        self, *, api_key: str, model: str, base_url: str, timeout_seconds: float,
        max_output_tokens: int, client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url, model=model, timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens, client=client, api_key=api_key,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider="anthropic", model=self._model, mode="external",
            implementation_version=ANTHROPIC_IMPLEMENTATION_VERSION,
            connectivity="not_checked", response_format="json_schema",
        )

    def _generate(self, context: ProviderContext, schema: dict[str, Any]) -> NativeReply:
        body = self._post("/v1/messages", {
            "model": self._model, "max_tokens": self._max_output_tokens, "stream": False,
            "system": SYSTEM_AUTHORITY,
            "messages": [{"role": "user", "content": reasoning_prompt(context) +
                          "\n\nOUTPUT JSON SCHEMA\n" + json.dumps(schema) +
                          "\nReturn one JSON object. Keep free-form action parameters empty; describe details in rationale."}],
            "output_config": {"format": {"type": "json_schema", "schema": anthropic_schema(schema)}},
        })
        if body.get("stop_reason") == "refusal":
            raise ProviderRefusalError()
        if body.get("stop_reason") == "max_tokens":
            raise ProviderTruncatedOutputError()
        if body.get("type") != "message" or body.get("role") != "assistant" or body.get("stop_reason") != "end_turn":
            raise ProviderInvalidOutputError("Expected a completed assistant message, not a tool request.")
        blocks = body.get("content")
        if not isinstance(blocks, list) or not blocks:
            raise ProviderInvalidOutputError("Assistant content blocks are missing.")
        text_parts = []
        for block in blocks:
            if not isinstance(block, dict):
                raise ProviderInvalidOutputError("Malformed assistant content block.")
            if block.get("type") in {"thinking", "redacted_thinking"}:
                continue  # Never persist or use private thinking as evidence.
            if block.get("type") != "text" or not isinstance(block.get("text"), str):
                raise ProviderInvalidOutputError("Only text output is accepted; no tool calls.")
            text_parts.append(block["text"])
        content = "".join(text_parts)
        if not content.strip():
            raise ProviderInvalidOutputError("No JSON content was returned.")
        raw_usage = body.get("usage")
        usage = raw_usage if isinstance(raw_usage, dict) else {}
        return NativeReply(
            content=content, model=optional_text(body.get("model")), request_id=optional_text(body.get("id")),
            input_tokens=optional_count(usage.get("input_tokens")),
            output_tokens=optional_count(usage.get("output_tokens")),
        )
