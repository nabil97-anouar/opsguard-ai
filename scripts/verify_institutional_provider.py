#!/usr/bin/env python3
"""Opt-in, one-request synthetic Chat Completions check; never run live in CI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.providers.base import ProviderContext, ProviderEvidence
from app.agent.providers.errors import ProviderError
from app.agent.providers.factory import create_provider, provider_status
from app.core.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize one synthetic inference request using exported settings")
    arguments = parser.parse_args()
    try:
        # Deliberately do not discover local .env files or use real operational data.
        settings = Settings(_env_file=None)
        if settings.llm_provider != "institutional":
            print("Set LLM_PROVIDER=institutional and export INSTITUTIONAL_LLM_* settings.", file=sys.stderr)
            return 2
        status = provider_status(settings)
        if not status.configured:
            print(status.reason, file=sys.stderr)
            return 2
        if not arguments.live:
            print(json.dumps({
                "provider": status.provider, "requested_model": status.model,
                "response_format": status.response_format, "configured": True,
                "connectivity": "not_checked", "request_sent": False,
                "next_step": "Add --live to authorize one synthetic inference request.",
            }, indent=2))
            return 0

        provider = create_provider(settings)
        result = provider.classify(ProviderContext(
            agent_run_id="synthetic-institutional-check", task="classification",
            alert={
                "title": "Synthetic inference service latency alert", "severity": "warning",
                "source": "synthetic-check", "infrastructure_type": "test",
                "description": "Synthetic service latency increased. Root cause and affected target are unknown.",
            },
            untrusted_evidence=[ProviderEvidence(
                evidence_id="synthetic-institutional-check:alert:1", source_type="alert",
                trust_level="untrusted", observation_status="valid", source="synthetic-check",
                summary="Synthetic latency alert with insufficient evidence for a root cause.",
                content="Synthetic latency alert with insufficient evidence for a root cause.",
            )],
        ))
        print(json.dumps({
            "provider": provider.identity.provider, "requested_model": result.requested_model,
            "served_model": result.served_model, "request_id": result.request_id,
            "response_format": status.response_format, "request_sent": True,
            "structured_output_valid": True, "duration_ms": result.duration_ms,
            "token_usage": {"input": result.input_tokens, "output": result.output_tokens},
            "scope": "One synthetic classification; other tasks and security behavior are not certified.",
        }, indent=2))
        return 0
    except ProviderError as exc:
        print(f"Verification failed: {exc.public_message}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Pydantic/SDK exceptions can contain configuration or response details.
        print(f"Verification failed: {type(exc).__name__}; check backend configuration.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
