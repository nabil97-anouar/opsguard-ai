"""Canonical trust labels and restrictive resolution at the retrieval boundary."""

from __future__ import annotations

from enum import Enum
from typing import Any


class TrustLevel(str, Enum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    QUARANTINED = "quarantined"


_RESTRICTION = {
    TrustLevel.TRUSTED: 0,
    TrustLevel.UNTRUSTED: 1,
    TrustLevel.QUARANTINED: 2,
}


def resolve_effective_trust(*levels: object) -> TrustLevel:
    """Use the most restrictive label; malformed persisted labels fail closed."""
    if not levels:
        return TrustLevel.UNTRUSTED
    resolved: list[TrustLevel] = []
    for level in levels:
        try:
            resolved.append(TrustLevel(level))
        except (ValueError, TypeError):
            return TrustLevel.QUARANTINED
    return max(resolved, key=_RESTRICTION.__getitem__)


def _metadata_trust_levels(metadata: dict[str, Any]) -> list[object]:
    levels = [metadata["trust_level"]] if "trust_level" in metadata else []
    document_metadata = metadata.get("document_metadata")
    if isinstance(document_metadata, dict):
        levels.extend(_metadata_trust_levels(document_metadata))
    return levels


def effective_chunk_trust(
    document_trust: object, chunk_trust: object, metadata: dict[str, Any] | None
) -> TrustLevel:
    """Document, chunk, and legacy metadata labels can restrict, never promote."""
    return resolve_effective_trust(
        document_trust, chunk_trust, *_metadata_trust_levels(metadata or {})
    )


def ingestion_trust(
    requested: TrustLevel | str,
    metadata: dict[str, Any] | None,
    *,
    allow_trusted: bool = False,
) -> TrustLevel:
    """Validate declarations; trusted authority requires an internal opt-in.

    This does not grant permission to promote an existing source. Ingestion
    separately combines this request with that source's existing restrictions.
    Injection-screening results deliberately play no role in trust assignment.
    """
    try:
        levels = [TrustLevel(level) for level in [requested, *_metadata_trust_levels(metadata or {})]]
    except (ValueError, TypeError) as exc:
        raise ValueError("trust_level must be trusted, untrusted, or quarantined.") from exc
    if not allow_trusted and TrustLevel.TRUSTED in levels:
        raise ValueError("Public ingestion cannot assign trusted authority.")
    return resolve_effective_trust(*levels)
