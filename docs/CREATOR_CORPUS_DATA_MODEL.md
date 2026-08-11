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
- `content`
- `content_hash`
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
- `text`
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

## Integrity Rules

- source asset dedupe is creator-scoped;
- document identity is creator-scoped;
- version history is immutable;
- provenance edges are additive;
- segments belong to one version only;
- archive and missing-state changes do not cascade-delete derived text.

## Provenance Relation Types

Current controlled relation types:

- `derived_from`
- `transcribed_from`
- `edited_from`
- `generated_from`
- `imported_from`

## Current Status

This model is implemented as a local SQLite-backed foundation for v33-A.
It is not a retrieval model and it is not a learning model.
