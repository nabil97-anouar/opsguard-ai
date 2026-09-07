from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, select

from app.db import session as db_session
from app.main import app
from app.models import Document, DocumentChunk
from app.rag.ingestion import ingest_document
from app.rag.retrieval import list_documents, retrieve_chunks
from app.rag.trust import TrustLevel, effective_chunk_trust, resolve_effective_trust
from app.services.demo_seed import demo_uuid, seed_demo_data


@pytest.fixture
def session(monkeypatch) -> Generator[Session, None, None]:
    engine = db_session.build_engine("sqlite://")
    monkeypatch.setattr(db_session, "engine", engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _payload(**changes) -> dict:
    return {
        "title": "GPU ownership procedure",
        "source": "local://gpu-ownership",
        "doc_type": "runbook",
        "content": "Check GPU process ownership before proposing containment.",
        "trust_level": "untrusted",
        **changes,
    }


def _trusted_document(session: Session) -> Document:
    result = ingest_document(session, **_payload(trust_level="trusted"), allow_trusted=True)
    document = session.get(Document, result["document_id"])
    assert document is not None
    return document


def _chunks(session: Session, document_id: UUID) -> list[DocumentChunk]:
    return list(session.exec(select(DocumentChunk).where(DocumentChunk.document_id == document_id)).all())


def test_relevant_trusted_document_preserves_chunk_provenance(session: Session) -> None:
    document = _trusted_document(session)
    chunk = _chunks(session, document.id)[0]

    results = retrieve_chunks(session, query="GPU ownership", include_untrusted=False)

    assert len(results) == 1
    result = results[0]
    assert result.document_id == document.id
    assert result.chunk_id == chunk.id
    assert result.source == "local://gpu-ownership"
    assert result.doc_type == "runbook"
    assert result.content_excerpt == chunk.content
    assert result.trust_level == TrustLevel.TRUSTED
    assert result.score > 0
    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=False) == results


def test_equal_relevance_has_stable_identity_tie_breakers(session: Session) -> None:
    first = _trusted_document(session)
    second_result = ingest_document(
        session, **_payload(source="local://alternative", trust_level="trusted"), allow_trusted=True
    )
    # Deliberately use equal-score content-only terms and equal title/index.
    results = retrieve_chunks(session, query="containment")
    expected_ids = sorted([first.id, second_result["document_id"]], key=str)
    assert len(results) == 2
    assert results[0].score == results[1].score
    assert [result.document_id for result in results] == expected_ids
    assert retrieve_chunks(session, query="containment") == results


@pytest.mark.parametrize("query", ["cobalt orchard", "", "   ", "!!!", "the and of to", "not before any"])
def test_trust_cannot_create_relevance(session: Session, query: str) -> None:
    _trusted_document(session)
    assert retrieve_chunks(session, query=query) == []
    response = TestClient(app).post("/api/v1/rag/retrieve", json={"query": query})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_document_demotion_is_effective_even_with_stale_trusted_chunks(session: Session) -> None:
    document = _trusted_document(session)
    trusted_score = retrieve_chunks(session, query="GPU ownership")[0].score
    document.trust_level = "untrusted"
    session.add(document)
    session.commit()

    assert {chunk.trust_level for chunk in _chunks(session, document.id)} == {"trusted"}
    results = retrieve_chunks(session, query="GPU ownership")
    assert len(results) == 1
    assert results[0].trust_level == TrustLevel.UNTRUSTED
    assert results[0].score == trusted_score
    assert retrieve_chunks(session, query="GPU ownership", trust_filter="trusted") == []
    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=False) == []
    assert list_documents(session)[0].trust_level == TrustLevel.UNTRUSTED


def test_demotion_refreshes_trust_cached_by_a_different_session(session: Session) -> None:
    document = _trusted_document(session)
    assert len(retrieve_chunks(session, query="GPU ownership", include_untrusted=False)) == 1
    with Session(session.get_bind()) as writer:
        current_document = writer.get(Document, document.id)
        assert current_document is not None
        current_document.trust_level = "quarantined"
        writer.add(current_document)
        writer.commit()

    assert document.trust_level == "trusted"
    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=True) == []
    assert document.trust_level == "quarantined"
    assert list_documents(session)[0].trust_level == TrustLevel.QUARANTINED


@pytest.mark.parametrize("location", ["document", "chunk"])
def test_reingestion_cannot_overwrite_quarantine_from_another_session(
    session: Session, location: str
) -> None:
    document = _trusted_document(session)
    chunk = _chunks(session, document.id)[0]
    with Session(session.get_bind()) as writer:
        current_record = writer.get(Document, document.id) if location == "document" else writer.get(DocumentChunk, chunk.id)
        assert current_record is not None
        current_record.trust_level = "quarantined"
        writer.add(current_record)
        writer.commit()

    assert document.trust_level == "trusted"
    assert chunk.trust_level == "trusted"
    result = ingest_document(session, **_payload(content="Replacement GPU ownership procedure."))
    assert result["updated"] is True
    assert result["skipped"] is False
    assert document.trust_level == "quarantined"
    assert {item.trust_level for item in _chunks(session, document.id)} == {"quarantined"}
    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=True) == []


def test_same_content_trust_and_metadata_demotion_updates_existing_chunks(session: Session) -> None:
    document = _trusted_document(session)
    original_ids = [chunk.id for chunk in _chunks(session, document.id)]

    result = ingest_document(session, **_payload(metadata={"tags": ["review-pending"]}))

    session.refresh(document)
    chunks = _chunks(session, document.id)
    assert result["updated"] is True
    assert result["skipped"] is False
    assert document.trust_level == "untrusted"
    assert [chunk.id for chunk in chunks] == original_ids
    assert {chunk.trust_level for chunk in chunks} == {"untrusted"}
    assert all(chunk.chunk_metadata["trust_level"] == "untrusted" for chunk in chunks)
    assert all(chunk.chunk_metadata["document_metadata"] == {"tags": ["review-pending"]} for chunk in chunks)
    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=False) == []


def test_metadata_only_demotion_is_not_skipped(session: Session) -> None:
    document = _trusted_document(session)
    original_ids = [chunk.id for chunk in _chunks(session, document.id)]
    result = ingest_document(
        session,
        **_payload(trust_level="trusted", metadata={"trust_level": "untrusted"}),
        allow_trusted=True,
    )
    assert result["updated"] is True
    assert result["skipped"] is False
    assert [chunk.id for chunk in _chunks(session, document.id)] == original_ids
    assert retrieve_chunks(session, query="GPU ownership")[0].trust_level == TrustLevel.UNTRUSTED


@pytest.mark.parametrize("location", ["document", "chunk", "metadata", "document_metadata"])
def test_quarantine_at_any_trust_boundary_excludes_content(session: Session, location: str) -> None:
    document = _trusted_document(session)
    chunk = _chunks(session, document.id)[0]
    if location == "document":
        document.trust_level = "quarantined"
        session.add(document)
    elif location == "chunk":
        chunk.trust_level = "quarantined"
    elif location == "metadata":
        chunk.chunk_metadata = {**chunk.chunk_metadata, "trust_level": "quarantined"}
    else:
        chunk.chunk_metadata = {**chunk.chunk_metadata, "document_metadata": {"trust_level": "quarantined"}}
    session.add(chunk)
    session.commit()

    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=True) == []
    assert retrieve_chunks(session, query="GPU ownership", trust_filter="quarantined") == []
    expected_document_label = TrustLevel.QUARANTINED if location == "document" else TrustLevel.TRUSTED
    assert list_documents(session)[0].trust_level == expected_document_label


@pytest.mark.parametrize("trust_level", ["verified", "Trusted", "", None, 123])
def test_public_invalid_trust_values_are_rejected(session: Session, trust_level: object) -> None:
    response = TestClient(app).post("/api/v1/documents/ingest", json=_payload(trust_level=trust_level))
    assert response.status_code == 422
    assert session.exec(select(Document)).all() == []


@pytest.mark.parametrize("changes", [
    {"trust_level": "trusted"},
    {"metadata": {"trust_level": "trusted"}},
    {"metadata": {"document_metadata": {"trust_level": "trusted"}}},
    {"metadata": {"trust_level": "verified"}},
])
def test_public_ingestion_cannot_grant_authority_via_any_trust_declaration(session: Session, changes: dict) -> None:
    response = TestClient(app).post("/api/v1/documents/ingest", json=_payload(**changes))
    assert response.status_code == 422
    assert session.exec(select(Document)).all() == []


def test_public_internal_opt_in_field_cannot_grant_authority(session: Session) -> None:
    response = TestClient(app).post(
        "/api/v1/documents/ingest", json=_payload(trust_level="trusted", allow_trusted=True)
    )
    assert response.status_code == 422
    assert session.exec(select(Document)).all() == []


def test_internal_ingestion_requires_explicit_trusted_opt_in(session: Session) -> None:
    with pytest.raises(ValueError, match="cannot assign trusted"):
        ingest_document(session, **_payload(trust_level="trusted"))
    assert session.exec(select(Document)).all() == []
    assert _trusted_document(session).trust_level == "trusted"


def test_clean_external_content_defaults_to_untrusted(session: Session) -> None:
    payload = _payload()
    payload.pop("trust_level")
    response = TestClient(app).post("/api/v1/documents/ingest", json=payload)
    assert response.status_code == 200
    document = session.get(Document, UUID(response.json()["document_id"]))
    assert document is not None
    assert document.injection_scan_result == "clean"
    assert document.trust_level == "untrusted"
    assert retrieve_chunks(session, query="GPU ownership", include_untrusted=False) == []


def test_external_replacement_cannot_unquarantine_existing_source(session: Session) -> None:
    result = ingest_document(session, **_payload(trust_level="quarantined"))
    response = TestClient(app).post(
        "/api/v1/documents/ingest", json=_payload(content="New GPU ownership procedure.")
    )
    assert response.status_code == 200
    assert response.json()["updated"] is True
    session.expire_all()
    assert session.get(Document, result["document_id"]).trust_level == "quarantined"
    assert {chunk.trust_level for chunk in _chunks(session, result["document_id"])} == {"quarantined"}
    assert retrieve_chunks(session, query="GPU ownership") == []


def test_legacy_malformed_trust_fails_closed(session: Session) -> None:
    document = _trusted_document(session)
    session.execute(text("UPDATE documents SET trust_level = 'verified'"))
    session.commit()
    session.expire_all()
    assert session.get(Document, document.id).trust_level == "verified"
    assert retrieve_chunks(session, query="GPU ownership") == []
    assert list_documents(session)[0].trust_level == TrustLevel.QUARANTINED


def test_models_reject_invalid_trust_assignment(session: Session) -> None:
    document = _trusted_document(session)
    with pytest.raises(ValueError):
        document.trust_level = "verified"
    with pytest.raises(ValueError):
        _chunks(session, document.id)[0].trust_level = "verified"


def test_retrieval_filters_use_exact_effective_trust(session: Session) -> None:
    document = _trusted_document(session)
    chunk = _chunks(session, document.id)[0]
    chunk.chunk_metadata = {**chunk.chunk_metadata, "trust_level": "untrusted"}
    session.add(chunk)
    session.commit()
    assert retrieve_chunks(session, query="GPU ownership", trust_filter="trusted") == []
    results = retrieve_chunks(session, query="GPU ownership", trust_filter="untrusted")
    assert len(results) == 1
    assert results[0].trust_level == TrustLevel.UNTRUSTED
    with pytest.raises(ValueError):
        retrieve_chunks(session, query="GPU ownership", trust_filter="verified")
    response = TestClient(app).post("/api/v1/rag/retrieve", json={"query": "GPU", "trust_filter": "verified"})
    assert response.status_code == 422


def test_sample_upsert_does_not_restore_demoted_trust(session: Session) -> None:
    seed_demo_data()
    document = session.get(Document, demo_uuid("document:gpu_runbook"))
    assert document is not None
    document.trust_level = "untrusted"
    session.add(document)
    session.commit()
    seed_demo_data()
    session.expire_all()
    assert document.trust_level == "untrusted"
    assert {chunk.trust_level for chunk in _chunks(session, document.id)} == {"untrusted"}


def test_sample_upsert_does_not_promote_recreated_chunks(session: Session) -> None:
    seed_demo_data()
    document = session.get(Document, demo_uuid("document:gpu_runbook"))
    assert document is not None
    document.trust_level = "quarantined"
    for chunk in _chunks(session, document.id):
        session.delete(chunk)
    session.add(document)
    session.commit()
    seed_demo_data()
    session.expire_all()
    assert {chunk.trust_level for chunk in _chunks(session, document.id)} == {"quarantined"}
    assert retrieve_chunks(session, query="GPU ownership", trust_filter="trusted") == []


def test_restrictive_resolution_never_promotes_conflicting_metadata() -> None:
    assert resolve_effective_trust("trusted", "untrusted") == TrustLevel.UNTRUSTED
    assert resolve_effective_trust("trusted", "quarantined") == TrustLevel.QUARANTINED
    assert resolve_effective_trust("trusted", None) == TrustLevel.QUARANTINED
    assert effective_chunk_trust("untrusted", "trusted", {"trust_level": "trusted"}) == TrustLevel.UNTRUSTED
    assert effective_chunk_trust("trusted", "trusted", {"trust_level": "verified"}) == TrustLevel.QUARANTINED
