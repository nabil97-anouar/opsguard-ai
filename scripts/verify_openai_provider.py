#!/usr/bin/env python3
"""One explicit, bounded OpenAI structured-output check; never run by CI."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.providers.base import ProviderContext, ProviderEvidence
from app.agent.providers.factory import create_provider
from app.core.config import Settings


def main() -> int:
    if os.getenv("LLM_PROVIDER") != "openai":
        print("Set LLM_PROVIDER=openai, OPENAI_API_KEY, and OPENAI_MODEL to run this manual check.", file=sys.stderr)
        return 2

    try:
        settings = Settings(_env_file=None)
        provider = create_provider(settings)
        result = provider.classify(ProviderContext(
            agent_run_id="manual-provider-check",
            task="classification",
            alert={
                "title": "Bounded verification alert",
                "severity": "warning",
                "source": "manual-check",
                "infrastructure_type": "test",
                "description": "A service emitted repeated errors; classify for human triage.",
            },
            untrusted_evidence=[ProviderEvidence(
                evidence_id="manual-provider-check:alert:1",
                source_type="alert",
                trust_level="untrusted",
                observation_status="valid",
                source="manual-check",
                title="Bounded verification alert",
                summary="Repeated service errors require investigation.",
                content="Repeated service errors require investigation.",
            )],
        ))
    except Exception as exc:
        print(f"Provider verification failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    print(json.dumps({
        "provider": provider.identity.provider,
        "model": provider.identity.model,
        "implementation_version": provider.identity.implementation_version,
        "schema_version": provider.identity.schema_version,
        "request_id": result.request_id,
        "duration_ms": result.duration_ms,
        "token_usage": {"input": result.input_tokens, "output": result.output_tokens},
        "structured_output_valid": True,
        "classification": result.value.model_dump(mode="json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
