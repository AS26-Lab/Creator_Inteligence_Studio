# Creator Corpus v33-B Ingestion And Normalization

## Purpose

v33-A established the creator-scoped local corpus foundation. v33-B turns that foundation into a deterministic ingestion pipeline with explicit normalization, provenance, deduplication, authorship classification, and minimal UX.

This phase does not add retrieval, embeddings, vector search, or learning.

## What v33-B Adds

- deterministic text normalization;
- raw and normalized text preservation;
- normalization versioning;
- canonical ingestion request/result contracts;
- explicit authorship classes;
- explicit retrieval eligibility;
- explicit voice-learning eligibility;
- content-quality flags for diagnostics;
- transcript ingestion integration;
- idempotent repeated ingestion;
- creator-isolation checks on mutation and source reuse;
- minimal user-facing confirmation that corpus ingestion occurred.

## Normalization Contract

Normalization is intentionally conservative and deterministic.

Allowed operations:

- line-ending normalization;
- Unicode normalization;
- trim accidental outer whitespace;
- collapse repeated internal spaces and tabs where safe;
- preserve paragraph boundaries;
- remove null and other non-meaningful control characters;
- normalize transcript segment text consistently.

Not allowed:

- grammar rewriting;
- punctuation invention;
- semantic rewriting;
- summarization;
- translation;
- language correction;
- AI-based rewriting.

Normalization version currently used:

- `text-normalizer-v1`

## Raw vs Normalized Content

The corpus preserves both representations:

- raw source content remains available;
- normalized content is stored separately and used for deterministic hashing and dedupe;
- the normalized representation is the one used for version identity and idempotency;
- the raw representation remains available for provenance and inspection.

## Authorship Classes

Current controlled values:

- `creator_original`
- `creator_edited`
- `transcribed_creator_speech`
- `ai_generated`
- `ai_rewritten`
- `imported_unknown`

Authorship class is explicit and must not be inferred from `document_type`.

## Eligibility Signals

The corpus persists two different forward-looking eligibility signals:

- `retrieval_eligible`
- `voice_learning_eligible`

These are not retrieval or learning systems. They are only durable metadata for future phases.

## Segment Eligibility

Transcript segments preserve:

- raw text;
- normalized text;
- review state;
- confidence;
- retrieval eligibility;
- voice-learning eligibility.

Low-confidence transcript segments default to `voice_learning_eligible = false`.

## Ingestion Outcomes

The ingestion result records:

- whether a new document was created;
- whether a new version was created;
- whether the request was deduplicated;
- which normalization version ran;
- which eligibility flags were assigned;
- whether the user received a corpus confirmation message.

## UX Boundary

The current UX is intentionally minimal.

The application only surfaces that the transcription result was saved to the corpus or already existed there.

It does not expose:

- a retrieval UI;
- embeddings UI;
- a corpus library redesign;
- AI voice-learning controls.

## Status

v33-B is implemented as a local-only ingestion and normalization layer on top of the v33-A foundation.
