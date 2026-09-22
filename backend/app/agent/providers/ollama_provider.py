"""Ollama native chat with an explicit schema and no tool execution."""
from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx2 as httpx

from app.agent.providers.base import ProviderContext, ProviderIdentity
from app.agent.providers.errors import ProviderInvalidOutputError, ProviderRefusalError, ProviderTruncatedOutputError
from app.agent.providers.http_structured import HTTPStructuredProvider, NativeReply, optional_count, optional_text
from app.agent.providers.prompts import SYSTEM_AUTHORITY, reasoning_prompt

OLLAMA_IMPLEMENTATION_VERSION = "ollama-chat-v1"


def ollama_mode(base_url: str) -> Literal["local", "external"]:
    return "local" if urlsplit(base_url).hostname in {"localhost", "127.0.0.1", "::1"} else "external"


class OllamaProvider(HTTPStructuredProvider):
    def __init__(
        self, *, model: str, base_url: str, timeout_seconds: float,
        max_output_tokens: int, api_key: str | None = None, client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url, model=model, timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens, client=client, api_key=api_key,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider="ollama", model=self._model, mode=ollama_mode(self._base_url),
            implementation_version=OLLAMA_IMPLEMENTATION_VERSION,
            connectivity="not_checked", response_format="json_schema",
        )

    def _generate(self, context: ProviderContext, schema: dict[str, Any]) -> NativeReply:
        body = self._post("/api/chat", {
            "model": self._model, "stream": False, "format": schema,
            "options": {"num_predict": self._max_output_tokens, "temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_AUTHORITY},
                {"role": "user", "content": reasoning_prompt(context) +
                 "\n\nOUTPUT JSON SCHEMA\n" + json.dumps(schema) + "\nReturn one JSON object."},
            ],
        })
        if body.get("done_reason") == "length":
            raise ProviderTruncatedOutputError()
        if body.get("done_reason") == "refusal":
            raise ProviderRefusalError()
        if body.get("done") is not True or body.get("done_reason") != "stop":
            raise ProviderInvalidOutputError("Expected a completed nonstreaming response.")
        message = body.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant" or message.get("tool_calls"):
            raise ProviderInvalidOutputError("Only assistant content is accepted; no tool calls.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderInvalidOutputError("No JSON content was returned.")
        return NativeReply(
            content=content, model=optional_text(body.get("model")),
            # Native Ollama does not guarantee a provider request ID. Do not invent one.
            request_id=None, input_tokens=optional_count(body.get("prompt_eval_count")),
            output_tokens=optional_count(body.get("eval_count")),
        )
