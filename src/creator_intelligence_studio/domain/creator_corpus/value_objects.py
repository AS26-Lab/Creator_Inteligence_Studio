"""Valores cerrados para Creator Corpus."""

from __future__ import annotations

from enum import Enum


class CorpusSourceType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    SCRIPT = "script"
    CAPTION = "caption"
    NOTE = "note"
    IMPORTED_TEXT = "imported_text"
    MANUAL_TEXT = "manual_text"
    FUTURE_DOCUMENT = "future_document"


class CorpusSourceAssetStatus(str, Enum):
    ACTIVE = "active"
    MISSING = "missing"
    ARCHIVED = "archived"


class CorpusDocumentType(str, Enum):
    TRANSCRIPT = "transcript"
    SCRIPT = "script"
    CAPTION = "caption"
    NOTE = "note"
    IMPORTED_TEXT = "imported_text"


class CorpusDocumentStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class CorpusVersionSourceKind(str, Enum):
    ORIGINAL = "original"
    TRANSCRIPTION = "transcription"
    USER_EDIT = "user_edit"
    AI_GENERATED = "ai_generated"
    AI_REWRITE = "ai_rewrite"
    IMPORT = "import"


class CorpusProvenanceRelationType(str, Enum):
    DERIVED_FROM = "derived_from"
    TRANSCRIBED_FROM = "transcribed_from"
    EDITED_FROM = "edited_from"
    GENERATED_FROM = "generated_from"
    IMPORTED_FROM = "imported_from"


class CorpusAuthorshipClass(str, Enum):
    CREATOR_ORIGINAL = "creator_original"
    CREATOR_EDITED = "creator_edited"
    TRANSCRIBED_CREATOR_SPEECH = "transcribed_creator_speech"
    AI_GENERATED = "ai_generated"
    AI_REWRITTEN = "ai_rewritten"
    IMPORTED_UNKNOWN = "imported_unknown"


class CorpusIngestionPolicy(str, Enum):
    INGEST_AS_NEW_DOCUMENT = "ingest_as_new_document"
    UPDATE_EXISTING_DOCUMENT = "update_existing_document"
    INGEST_IF_CHANGED = "ingest_if_changed"
    SKIP_IF_DUPLICATE = "skip_if_duplicate"


TEXT_NORMALIZATION_VERSION = "text-normalizer-v1"
