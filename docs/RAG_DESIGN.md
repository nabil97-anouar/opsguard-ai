# Retrieval and Evidence

OpsGuard retrieves document excerpts from SQL storage using deterministic lexical ranking. The agent combines these excerpts with alert data and local tool results in its investigation trace.

## Ingestion

[ingest_document](../backend/app/rag/ingestion.py) accepts a title, source label, document type, trust label, content, and optional metadata. Public ingestion defaults to `untrusted` and accepts only `untrusted` or `quarantined`; declaring `trusted`, including in trust metadata, is rejected. The source is stored as a label; ingestion does not fetch URLs or read an arbitrary source path.

1. Strip surrounding whitespace and require nonempty title, source, type, and content.
2. Find an existing document by title and source. Combine requested trust with existing document, chunk, and trust-metadata restrictions, then compare its SHA-256 content hash and metadata.
3. Split content into sections with Markdown heading recognition and limited YAML heading labeling.
4. Chunk each section using a target of 1,200 characters and 150 characters of overlap.
5. Scan each chunk for known injection markers.
6. Store the document and chunks, including hashes, section metadata, trust labels, and scan results.

[chunk_text](../backend/app/rag/chunking.py) uses paragraphs and character boundaries, not a semantic or token-based splitter. Overlap can increase the final chunk length beyond the target. Token counts are approximate. Chunk IDs derive from the document ID, chunk index, and content hash. Content changes replace the document's previous chunks.

Metadata-only changes update every existing chunk in the same transaction while retaining its ID and content. Trust restrictions survive content replacement. Ingestion has no promotion or quarantine-release operation; the internal `allow_trusted=True` option permits trusted declarations for repository-controlled input, but does not remove existing source restrictions.

Ingestion refreshes document/chunk labels already cached in the caller's database session. On PostgreSQL, it locks existing document and chunk rows until commit to serialize their updates; SQLite does not provide these row locks. This does not add title/source uniqueness or serialize creation of a previously absent source.

## Retrieval

[retrieve_chunks](../backend/app/rag/retrieval.py) loads joined document/chunk rows and ranks them in Python. Tokenization lowercases ASCII letters/numbers and removes an explicit set of English function words. A query must share at least one remaining token with chunk content or document metadata. Empty, punctuation-only, stopword-only, and unrelated queries return no results.

The score combines bounded content term-frequency overlap, metadata overlap, distinct matching terms, token-boundary phrase matches, and a length penalty. Trust contributes no score and cannot create relevance. Equal scores sort by trusted status, title, chunk index, document ID, and chunk ID, giving deterministic ordering even across otherwise identical sources.

The retrieval request supports:

| Field | Behavior |
| --- | --- |
| `query` | Required string, up to 500 characters through the API; empty text returns no evidence |
| `limit` | Default 5; API range 1–20 |
| `trust_filter` | Optional exact `trusted`, `untrusted`, or `quarantined` filter; quarantine is always excluded |
| `include_untrusted` | Defaults to `true` in the retrieval API |

Quarantined documents or effective chunk labels are excluded from every retrieval path, including the agent and `retrieve_runbook`. Setting `include_untrusted=false` requires effective trust to be `trusted`. Flagged content is returned with its scan metadata if it otherwise passes the filters; scanning does not automatically quarantine or promote a document.

Each result includes `document_id`, `chunk_id`, title, source, chunk index, document type, trust level, score, excerpt, citation text, and injection indicators. Excerpts target 280 characters.

The agent builds its query from the classification hint plus the alert title, description, and source. It requests five results and includes untrusted documents for the prompt-injection incident category. The `retrieve_runbook` tool calls the same retrieval service and filters candidates to runbooks.

## Trust and screening

[detect_prompt_injection](../backend/app/rag/injection.py) recognizes a fixed set of phrases, including instruction overrides, secret disclosure, safety disabling, and shell-command markers. Ingestion stores the scan result. Retrieval uses stored scan metadata when present and scans chunk content when it is absent.

[TrustLevel and effective_chunk_trust](../backend/app/rag/trust.py) define three labels: `trusted`, `untrusted`, and `quarantined`. Effective chunk trust is the most restrictive of the document field, chunk field, chunk metadata label, and nested `document_metadata` labels. A document demotion therefore takes effect immediately even if old chunks still contain trusted labels. Malformed persisted labels fail closed to quarantine; API input and ORM document/chunk trust assignments reject invalid values.

The document-list API reports the normalized document-level label. Retrieval results report effective per-chunk trust, which can be more restrictive than the document label. A chunk-only quarantine excludes that chunk; a document quarantine excludes all of its chunks.

Public input cannot create trusted authority, and no scan outcome can grant it. Fixed sample documents are assigned trust explicitly by repository-owned seeding code; ordinary seed upserts preserve existing demotions. Explicit fixture reset deletes and recreates the fixed baseline, including its trust labels.

Trust labels remain local policy assertions, not authenticated source attestations. A clean scan means only that no configured pattern matched. The pipeline has no scheduled rescanning, document-age policy, trust-review workflow, or hash verification during retrieval.

## Evidence in the agent

[RetrievedContextItem and EvidenceItem](../backend/app/agent/state.py) preserve run-scoped evidence IDs, source type and label, document/chunk or tool-call identity, retrieval score where applicable, trust, content/excerpt snapshots, and timezone-aware observation timestamps. Hypotheses reference evidence IDs. Recommendations retain the run's evidence snapshots; tool citations include the unique persisted call ID. Failed or blocked attempts remain audit/trace records and cannot become supporting observations.

Historical views use these stored snapshots and do not perform fresh retrieval. Document edits or demotions change future retrieval, while a past run keeps the excerpt and trust label it actually observed. Legacy runs without stored evidence remain explicitly empty; missing provenance is not reconstructed from current documents.

Current grounding has practical limits:

- Lexical overlap can match incidental words; it is not semantic relevance or a guarantee that an excerpt supports a claim.
- Excerpts are snapshots, not complete copies of a source document. Old chunk IDs may no longer resolve after re-ingestion; the stored snapshot is the historical record.
- Deterministic hypotheses are selected by incident category. Evidence-reference validation establishes identity, not claim entailment or correctness.
- Trust labels and evidence snapshots are ordinary mutable SQL data, not cryptographically authenticated or tamper-evident records.

The runtime `evidence_grounding_score` is the fraction of evidence items labeled trusted. It is a diagnostic heuristic, not retrieval precision or claim-level evidence coverage.

## Storage and scope

[Document and DocumentChunk](../backend/app/models/document.py) are SQL tables. Retrieval does not use embeddings, Qdrant, BM25, reciprocal-rank fusion, or a reranker. Compose does not start Qdrant because this pipeline does not use it.

See [Agent Workflow](AGENT_GRAPH.md), [Tool Registry](TOOL_REGISTRY.md), and [API Reference](API_SPEC.md).
