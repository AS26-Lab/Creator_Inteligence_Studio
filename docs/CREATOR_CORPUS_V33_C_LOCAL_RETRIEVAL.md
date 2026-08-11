# Creator Corpus v33-C Local Retrieval

## Purpose

v33-C adds the first canonical retrieval boundary for the local Creator Corpus.
The goal is deterministic, creator-scoped, auditable retrieval without embeddings, vector databases, or AI-generated ranking.

## Retrieval Choice

Selected retrieval mechanism:

- local SQLite-backed retrieval index derived from canonical corpus tables
- deterministic normalized-text filtering
- explainable match reasons
- bounded pagination
- current-version-first behavior by default

The repository also provisions an FTS5-derived index table for health and rebuild purposes, but the canonical query contract does not depend on semantic similarity or LLM calls.

## Canonical Rules

- every query requires `creator_id`
- default results exclude archived content and non-eligible versions
- current versions are returned by default
- historical versions require explicit opt-in
- retrieval eligibility is separate from voice-learning eligibility
- creator isolation is enforced in direct lookup and filtered search

## Result Shape

Retrieval results return:

- document identity
- version identity
- optional segment identity
- document type
- authorship class
- language
- provenance summary
- eligibility flags
- timestamps
- bounded snippet text
- explainable relevance reason

## Lifecycle

- retrieval rows are derived data
- the index is refreshed when documents, versions, segments, or archive state changes
- the index can be rebuilt from canonical corpus tables
- diagnostics can report index health without dumping corpus text

## Explicit Non-Goals

- embeddings
- vector databases
- semantic retrieval
- reranking
- LLM context assembly
- feedback learning
- voice modeling

## Status

Implemented on the current branch as a local-only deterministic retrieval layer.
