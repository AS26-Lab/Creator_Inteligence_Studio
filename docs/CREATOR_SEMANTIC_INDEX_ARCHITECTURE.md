# Creator Semantic Index Architecture

## Purpose

This document defines the local semantic index boundary for Creator Corpus.

It is derived data, not the source of truth.

## Core Principles

- creator isolation is mandatory
- no external vector database
- no remote embedding API
- no hidden download
- no cross-creator nearest-neighbor search before scoping
- lexical retrieval must remain usable without semantic assets

## Logical Components

- `CreatorCorpusEmbeddingService`
- `CreatorCorpusSemanticIndexService`
- `CreatorCorpusRetrievalService`

The embedding service is responsible for model loading, tokenization, vector creation, normalization, and health.

The semantic index service is responsible for:

- chunk selection
- chunk identity
- vector persistence
- creator-scoped search
- health and stale detection
- rebuild and activation lifecycle

The canonical retrieval service is responsible for:

- lexical search
- hybrid candidate fusion
- fallback reporting

## Storage Choice

The index uses a simple local SQLite boundary with vector blobs and in-process scoring.

Why:

- simplest robust local option at current scale
- keeps creator data on disk locally
- avoids another service process
- keeps rebuild and activation lifecycle transparent

## Index Records

Each stored chunk records:

- `creator_id`
- `document_id`
- `version_id`
- `segment_id`
- `chunk_id`
- `content_hash`
- `embedding_model_id`
- `embedding_model_revision`
- `chunking_version`
- `vector_blob`
- `created_at`

## Health Model

Health reports:

- `missing`
- `ready`
- `active`
- `stale`
- `repair_required`

Health checks should validate:

- required files
- model load
- tokenizer load
- expected vector dimension
- finite vectors
- normalization
- revision match
- chunking version match
- content hash match

## Build Lifecycle

Build flow:

1. collect retrieval-eligible corpus rows for one creator
2. derive chunks deterministically
3. embed chunks locally
4. persist a staging generation
5. validate the generation
6. activate it atomically

Previous active data remains usable until replacement activation finishes.

## Search Lifecycle

Search flow:

1. resolve active generation for one creator
2. validate health
3. embed the query locally
4. score vectors in-process
5. apply creator-scoped filters
6. return ranked items

## Cancellation

If a build is cancelled, the incomplete generation must not replace the previous active one.

## Incremental Update

Incremental rebuilds should update only the affected creator data when feasible:

- new document/version -> new chunks
- archive/remove -> remove from active candidate set
- hash change -> stale chunk replacement
- eligibility change -> rebuild affected chunks

## Security

- never log vectors
- never upload vectors
- never expose global semantic neighbors before creator scoping
- never rely on remote provider memory
