"""Reglas puras para Creator Corpus."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_corpus_identity_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def build_corpus_text_fingerprint(*, content: str, language: str | None, creator_id: str, document_type: str, source_asset_id: str | None = None, title: str | None = None, project_id: str | None = None) -> str:
    payload = {
        "content": content,
        "language": language,
        "creator_id": creator_id,
        "document_type": document_type,
        "source_asset_id": source_asset_id,
        "title": title,
        "project_id": project_id,
    }
    return build_corpus_identity_fingerprint(payload)


def build_corpus_provenance_fingerprint(payload: dict[str, object]) -> str:
    return build_corpus_identity_fingerprint(payload)
