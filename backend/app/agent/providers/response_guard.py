"""Reject the configured credential if a provider echoes it in accepted output."""
from __future__ import annotations

from pydantic import BaseModel

from app.agent.providers.errors import ProviderInvalidOutputError


def reject_credential_echo(api_key: str | None, *values: object) -> None:
    """Inspect response fields without logging, masking, or retaining their values.

    This is an exact configured-key check, not a general-purpose secret detector.
    Checking decoded values also catches JSON escaping of the credential.
    """
    if not api_key:
        return
    pending = list(values)
    while pending:
        value = pending.pop()
        if isinstance(value, str):
            if api_key in value:
                raise ProviderInvalidOutputError("Response contained the configured provider credential.")
        elif isinstance(value, BaseModel):
            pending.append(value.model_dump(mode="python"))
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (list, tuple)):
            pending.extend(value)
