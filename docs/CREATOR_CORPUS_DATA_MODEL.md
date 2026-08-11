# Creator Corpus Data Model

## Overview

The Creator Corpus is a creator-scoped local data layer that preserves textual evidence and provenance without collapsing source identity into a single global store.

## Core Entities

### Creator

Existing stable identity record reused by the corpus.

Key property:

- every corpus record resolves to exactly one `creator_id`

### Corpus Source Asset

Represents an original input such as a video, audio file, transcript source, script file, imported text, or manual text.

Important fields:

- `id`
- `creator_id`
- `project_id` optional
- `source_type`
- `original_name`
- `local_path`
- `content_hash`
- `size_bytes`
- `mime_type`
- `status`
- timestamps

### Corpus Document

Represents the textual or structured corpus object derived from a source asset or import.

Important fields:

- `id`
- `creator_id`
- `source_asset_id` optional
- `project_id` optional
- `document_type`
- `title`
- `language`
- `current_version_id`
- `status`
- `document_identity_hash`

### Corpus Document Version

Represents immutable history for a document.

Important fields:

- `id`
- `document_id`
- `creator_id`
- `version_number`
- `content` raw content
- `normalized_content`
- `content_hash` normalized hash
- `raw_content_hash`
- `normalization_version`
- `authorship_class`
- `retrieval_eligible`
- `voice_learning_eligible`
- `quality_flags`
- `source_kind`
- `source_asset_id`
- `parent_version_id`
- `language`
- `created_by`
- `metadata_json`

### Corpus Segment

Represents optional structured segment data, especially for transcripts.

Important fields:

- `id`
- `document_version_id`
- `creator_id`
- `sequence`
- `start_seconds`
- `end_seconds`
- `text` normalized segment text
- `raw_text`
- `normalization_version`
- `retrieval_eligible`
- `voice_learning_eligible`
- `quality_flags`
- `confidence`
- `review_state`
- source reference metadata

### Corpus Provenance Edge

Represents a simple relational provenance link between a parent source and a child version.

Important fields:

- `id`
- `creator_id`
- `parent_type`
- `parent_id`
- `child_version_id`
- `relation_type`
- `metadata_json`

### Corpus Retrieval Index

Represents derived retrieval data used by the local query layer.

Important fields:

- `retrieval_key`
- `creator_id`
- `project_id`
- `document_id`
- `version_id`
- `segment_id` optional
- `row_kind`
- `document_type`
- `title`
- `language`
- `authorship_class`
- `source_kind`
- `source_asset_id`
- `status`
- `retrieval_eligible`
- `voice_learning_eligible`
- `is_current_version`
- `version_number`
- `content_text`
- `search_text`
- `provenance_summary`
- `segment_start_seconds`
- `segment_end_seconds`
- `segment_confidence`
- `segment_review_state`
- `quality_flags_json`

This index is derived data. The canonical corpus tables remain the source of truth and the index can be rebuilt from them.

## Integrity Rules

- source asset dedupe is creator-scoped;
- document identity is creator-scoped;
- document identity uses the normalized content hash so repeated ingestion is idempotent;
- version history is immutable;
- provenance edges are additive;
- segments belong to one version only;
- archive and missing-state changes do not cascade-delete derived text.

## Ingestion And Normalization

The current ingestion layer keeps both the raw and normalized representations.

- raw content is preserved exactly as received;
- normalized content is derived deterministically and versioned with `text-normalizer-v1`;
- duplicate detection uses the normalized representation;
- source assets continue to use source-specific hashes for identity;
- transcript segment text is normalized independently from source audio/video metadata.

## Authorship And Eligibility

The corpus now stores explicit forward-looking metadata:

- `authorship_class`
- `retrieval_eligible`
- `voice_learning_eligible`
- `quality_flags`

These are not retrieval or learning systems. They are durable signals for future phases.

## Provenance Relation Types

Current controlled relation types:

- `derived_from`
- `transcribed_from`
- `edited_from`
- `generated_from`
- `imported_from`

## Current Status

This model is implemented as a local SQLite-backed foundation for v33-A, v33-B, and v33-C.
It is not a learning model and it is not a semantic retrieval model.
