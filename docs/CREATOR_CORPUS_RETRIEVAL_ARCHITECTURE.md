# Creator Corpus Retrieval Architecture

## Boundary

All corpus retrieval must flow through one canonical service:

- `CreatorCorpusRetrievalService`

Inputs:

- `CorpusRetrievalQuery`

Outputs:

- `CorpusRetrievalResult`

## Query Contract

Queries are creator-scoped and may optionally filter by:

- project
- document type
- authorship class
- language
- status
- source asset
- document
- segment
- date range
- current version
- retrieval eligibility

The query contract supports both:

- structured browse
- local text search

## Search Technology

The implemented search path is deterministic and local:

- normalized text is indexed into a derived retrieval table
- the query layer filters and ranks using local text matching
- the result set is explainable and bounded

SQLite FTS5 is provisioned as derived infrastructure, but v33-C does not require semantic text search, embeddings, or a model-backed retriever.

v33-F adds an evaluation-only local semantic foundation for later comparison. It does not replace lexical retrieval or become the default product path.

v33-G adds an optional hybrid path when the local semantic capability is healthy.

Product retrieval modes now conceptually include:

- `lexical`
- `hybrid_if_available`

The semantic path must never be used as a hidden prefilter before creator scoping. Creator filters remain mandatory before any semantic result is exposed.

## Ranking

Ranking is intentionally simple and explainable:

- title match
- phrase/content match
- provenance match
- current-version preference
- project preference
- updated/created ordering when no query text is provided

## Health And Repair

The retrieval index exposes health metrics:

- indexed row counts
- expected row counts
- missing rows
- stale rows

The semantic index exposes a separate derived-health boundary for:

- model revision
- chunking version
- vector integrity
- creator-scoped activation
- fallback readiness

## Context Assembly

Retrieval results feed the separate Creator Context Assembly layer.

That layer is responsible for:

- deterministic item deduplication
- segment grouping
- budget enforcement
- authorship/category labeling
- prompt grounding with corpus text treated as data

Retrieval itself stays local, deterministic, and creator-scoped. Context assembly does not add embeddings or semantic search.

The index can be rebuilt deterministically from canonical corpus tables.

Semantic retrieval is only used when the local embedding component and the derived semantic index are ready. Otherwise retrieval remains lexical and reports lexical fallback.

## Security

- creator isolation is enforced before result emission
- direct lookup respects creator ownership
- no raw SQL interpolation from user input
- no network calls
- no LLM calls
