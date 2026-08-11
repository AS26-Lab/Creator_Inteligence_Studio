# Creator Corpus v33-A Foundation

## Purpose

v33-A establishes the local Creator Corpus foundation for identity, provenance, ingestion, deduplication, versioning, and lifecycle management.

This phase is intentionally narrow:

- local creator-scoped storage only;
- no retrieval;
- no embeddings;
- no vector database;
- no collective sharing;
- no remote corpus upload.

## Implemented Boundary

The repository now models:

- `creator_id`
- source assets
- content documents
- document versions
- provenance edges
- transcript segments

The current implementation preserves:

- creator isolation;
- idempotent ingestion;
- source asset deduplication by creator and hash;
- version history;
- provenance relationships;
- segment metadata;
- local-only operation.

## Current Ingestion Paths

Implemented ingestion paths:

- explicit text document ingestion;
- transcription-to-corpus ingestion from the local transcription stack.

The transcription bridge preserves:

- creator ownership;
- project linkage when available;
- language;
- segments;
- provenance from the source video/transcription;
- current-version tracking.

## Lifecycle Rules

- source assets can be marked missing without deleting derived text;
- documents can be archived without deleting prior versions;
- versions are immutable history records;
- deduplication is creator-scoped;
- same content across different creators is never merged.

## What Is Not Included

This phase does not add:

- semantic retrieval;
- embeddings;
- feedback learning;
- creator voice modeling;
- vector search;
- remote sync;
- cloud corpus storage.

## Migration

- schema migration: `v33`
- forward-only from the prior v32 production schema
- additive tables and indexes only

## Notes

The corpus foundation is designed to support later retrieval and learning layers, but those layers remain paused until their own approved phase.
