"""Repositorio SQLite para Creator Corpus."""

from __future__ import annotations

import json
import sqlite3
import re
from functools import lru_cache
from uuid import uuid4

from creator_intelligence_studio.domain.creator_corpus.entities import (
    CorpusDocument,
    CorpusDocumentVersion,
    CorpusProvenanceEdge,
    CorpusSegment,
    CorpusSourceAsset,
)
from creator_intelligence_studio.domain.creator_corpus.ingestion import CorpusEligibility
from creator_intelligence_studio.domain.creator_corpus.normalization import normalize_corpus_text
from creator_intelligence_studio.domain.creator_corpus.retrieval import (
    CorpusRetrievalIndexHealth,
    CorpusRetrievalQuery,
    CorpusRetrievalSort,
)
from creator_intelligence_studio.domain.creator_corpus.repositories import CreatorCorpusRepository
from creator_intelligence_studio.domain.creator_corpus.value_objects import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusVersionSourceKind,
    TEXT_NORMALIZATION_VERSION,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _metadata_dict(value: str | None) -> dict[str, object]:
    loaded = _json_loads(value, {})
    return loaded if isinstance(loaded, dict) else {}


@lru_cache(maxsize=1)
def _supports_fts5() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE temp.creator_corpus_fts5_probe USING fts5(search_text)")
        return True
    except sqlite3.Error:
        return False
    finally:
        connection.close()


def _normalize_like_text(value: str | None) -> str:
    return normalize_corpus_text(value).lower()


def _build_search_tokens(query_text: str | None) -> tuple[str, ...]:
    normalized = normalize_corpus_text(query_text).lower()
    tokens = tuple(token for token in re.findall(r"(?u)[\w]+", normalized) if token)
    return tokens


def _build_fts_query(query_text: str | None) -> str | None:
    tokens = _build_search_tokens(query_text)
    if not tokens:
        normalized = normalize_corpus_text(query_text).strip()
        return normalized or None
    return " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def _search_text(*parts: str | None) -> str:
    values = [normalize_corpus_text(part) for part in parts if part]
    return "\n".join(part for part in values if part).strip()


def _row_to_source_asset(row: sqlite3.Row) -> CorpusSourceAsset:
    return CorpusSourceAsset(
        id=row["id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        source_type=CorpusSourceType(row["source_type"]),
        original_name=row["original_name"],
        local_path=row["local_path"],
        content_hash=row["content_hash"],
        size_bytes=int(row["size_bytes"]),
        mime_type=row["mime_type"],
        status=CorpusSourceAssetStatus(row["status"]),
        source_metadata_json=row["source_metadata_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        imported_at=from_iso_z(row["imported_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_document(row: sqlite3.Row) -> CorpusDocument:
    return CorpusDocument(
        id=row["id"],
        creator_id=row["creator_id"],
        source_asset_id=row["source_asset_id"],
        project_id=row["project_id"],
        document_type=CorpusDocumentType(row["document_type"]),
        title=row["title"],
        language=row["language"],
        current_version_id=row["current_version_id"],
        status=CorpusDocumentStatus(row["status"]),
        document_identity_hash=row["document_identity_hash"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_version(row: sqlite3.Row) -> CorpusDocumentVersion:
    metadata = _metadata_dict(row["metadata_json"])
    return CorpusDocumentVersion(
        id=row["id"],
        document_id=row["document_id"],
        creator_id=row["creator_id"],
        version_number=int(row["version_number"]),
        content=row["content"],
        content_hash=row["content_hash"],
        raw_content=str(metadata.get("raw_content", row["content"] or "")),
        normalized_content=str(metadata.get("normalized_content", row["content"] or "")),
        raw_content_hash=str(metadata.get("raw_content_hash", "")),
        normalization_version=str(metadata.get("normalization_version", TEXT_NORMALIZATION_VERSION)),
        authorship_class=CorpusAuthorshipClass(str(metadata.get("authorship_class", CorpusAuthorshipClass.IMPORTED_UNKNOWN.value))),
        retrieval_eligible=bool(metadata.get("retrieval_eligible", True)),
        voice_learning_eligible=bool(metadata.get("voice_learning_eligible", False)),
        quality_flags=tuple(metadata.get("quality_flags", ())),
        source_kind=CorpusVersionSourceKind(row["source_kind"]),
        source_asset_id=row["source_asset_id"],
        parent_version_id=row["parent_version_id"],
        language=row["language"],
        created_by=row["created_by"],
        metadata_json=row["metadata_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_segment(row: sqlite3.Row) -> CorpusSegment:
    metadata = _metadata_dict(row["metadata_json"])
    return CorpusSegment(
        id=row["id"],
        document_version_id=row["document_version_id"],
        creator_id=row["creator_id"],
        sequence=int(row["sequence"]),
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        text=row["text"],
        raw_text=str(metadata.get("raw_text", row["text"] or "")),
        confidence=row["confidence"],
        review_state=row["review_state"],
        normalization_version=str(metadata.get("normalization_version", TEXT_NORMALIZATION_VERSION)),
        retrieval_eligible=bool(metadata.get("retrieval_eligible", True)),
        voice_learning_eligible=bool(metadata.get("voice_learning_eligible", True)),
        quality_flags=tuple(metadata.get("quality_flags", ())),
        source_reference_type=row["source_reference_type"],
        source_reference_id=row["source_reference_id"],
        metadata_json=row["metadata_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_edge(row: sqlite3.Row) -> CorpusProvenanceEdge:
    return CorpusProvenanceEdge(
        id=row["id"],
        creator_id=row["creator_id"],
        parent_type=row["parent_type"],
        parent_id=row["parent_id"],
        child_version_id=row["child_version_id"],
        relation_type=CorpusProvenanceRelationType(row["relation_type"]),
        metadata_json=row["metadata_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteCreatorCorpusRepository(CreatorCorpusRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_source_asset(self, asset: CorpusSourceAsset) -> CorpusSourceAsset:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_corpus_source_assets (
                    id, creator_id, project_id, source_type, original_name, local_path,
                    content_hash, size_bytes, mime_type, status, source_metadata_json,
                    created_at, imported_at, updated_at
                ) VALUES (
                    :id, :creator_id, :project_id, :source_type, :original_name, :local_path,
                    :content_hash, :size_bytes, :mime_type, :status, :source_metadata_json,
                    :created_at, :imported_at, :updated_at
                )
                ON CONFLICT(creator_id, content_hash) DO UPDATE SET
                    project_id = excluded.project_id,
                    source_type = excluded.source_type,
                    original_name = excluded.original_name,
                    local_path = excluded.local_path,
                    size_bytes = excluded.size_bytes,
                    mime_type = excluded.mime_type,
                    status = excluded.status,
                    source_metadata_json = excluded.source_metadata_json,
                    updated_at = excluded.updated_at
                """,
                {
                    **asset.to_dict(),
                    "source_type": asset.source_type.value,
                    "status": asset.status.value,
                    "created_at": asset.created_at.isoformat(),
                    "imported_at": asset.imported_at.isoformat(),
                    "updated_at": asset.updated_at.isoformat(),
                },
            )
            row = connection.execute(
                "SELECT * FROM creator_corpus_source_assets WHERE creator_id = ? AND content_hash = ?",
                (asset.creator_id, asset.content_hash),
            ).fetchone()
        return _row_to_source_asset(row)

    def get_source_asset(self, source_asset_id: str) -> CorpusSourceAsset | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_corpus_source_assets WHERE id = ?", (source_asset_id,)).fetchone()
        return _row_to_source_asset(row) if row else None

    def get_source_asset_by_hash(self, creator_id: str, content_hash: str) -> CorpusSourceAsset | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_corpus_source_assets WHERE creator_id = ? AND content_hash = ?",
                (creator_id, content_hash),
            ).fetchone()
        return _row_to_source_asset(row) if row else None

    def list_source_assets(self, creator_id: str, project_id: str | None = None) -> list[CorpusSourceAsset]:
        query = "SELECT * FROM creator_corpus_source_assets WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if project_id is not None:
            query += " AND IFNULL(project_id, '') = IFNULL(?, '')"
            params.append(project_id)
        query += " ORDER BY created_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_source_asset(row) for row in rows]

    def upsert_document(self, document: CorpusDocument) -> CorpusDocument:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_corpus_documents (
                    id, creator_id, source_asset_id, project_id, document_type, title,
                    language, current_version_id, status, document_identity_hash,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :source_asset_id, :project_id, :document_type, :title,
                    :language, :current_version_id, :status, :document_identity_hash,
                    :created_at, :updated_at
                )
                ON CONFLICT(creator_id, document_identity_hash) DO UPDATE SET
                    source_asset_id = excluded.source_asset_id,
                    project_id = excluded.project_id,
                    document_type = excluded.document_type,
                    title = excluded.title,
                    language = excluded.language,
                    current_version_id = excluded.current_version_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                {
                    **document.to_dict(),
                    "document_type": document.document_type.value,
                    "status": document.status.value,
                    "created_at": document.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat(),
                },
            )
            row = connection.execute(
                "SELECT * FROM creator_corpus_documents WHERE creator_id = ? AND document_identity_hash = ?",
                (document.creator_id, document.document_identity_hash),
            ).fetchone()
        return _row_to_document(row)

    def get_document(self, document_id: str) -> CorpusDocument | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_corpus_documents WHERE id = ?", (document_id,)).fetchone()
        return _row_to_document(row) if row else None

    def list_documents(self, creator_id: str, project_id: str | None = None) -> list[CorpusDocument]:
        query = "SELECT * FROM creator_corpus_documents WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if project_id is not None:
            query += " AND IFNULL(project_id, '') = IFNULL(?, '')"
            params.append(project_id)
        query += " ORDER BY created_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_document(row) for row in rows]

    def get_document_by_identity_hash(self, creator_id: str, document_identity_hash: str) -> CorpusDocument | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_corpus_documents WHERE creator_id = ? AND document_identity_hash = ?",
                (creator_id, document_identity_hash),
            ).fetchone()
        return _row_to_document(row) if row else None

    def upsert_document_version(self, version: CorpusDocumentVersion) -> CorpusDocumentVersion:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_corpus_document_versions (
                    id, document_id, creator_id, version_number, content, content_hash,
                    source_kind, source_asset_id, parent_version_id, language,
                    created_by, metadata_json, created_at
                ) VALUES (
                    :id, :document_id, :creator_id, :version_number, :content, :content_hash,
                    :source_kind, :source_asset_id, :parent_version_id, :language,
                    :created_by, :metadata_json, :created_at
                )
                ON CONFLICT(document_id, content_hash) DO NOTHING
                """,
                {
                    **version.to_dict(),
                    "source_kind": version.source_kind.value,
                    "created_at": version.created_at.isoformat(),
                },
            )
            row = connection.execute(
                "SELECT * FROM creator_corpus_document_versions WHERE document_id = ? AND content_hash = ?",
                (version.document_id, version.content_hash),
            ).fetchone()
        return _row_to_version(row)

    def get_document_version(self, version_id: str) -> CorpusDocumentVersion | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_corpus_document_versions WHERE id = ?", (version_id,)).fetchone()
        return _row_to_version(row) if row else None

    def list_document_versions(self, document_id: str) -> list[CorpusDocumentVersion]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_corpus_document_versions WHERE document_id = ? ORDER BY version_number ASC",
                (document_id,),
            ).fetchall()
        return [_row_to_version(row) for row in rows]

    def get_document_version_by_hash(self, document_id: str, content_hash: str) -> CorpusDocumentVersion | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_corpus_document_versions WHERE document_id = ? AND content_hash = ?",
                (document_id, content_hash),
            ).fetchone()
        return _row_to_version(row) if row else None

    def upsert_segment(self, segment: CorpusSegment) -> CorpusSegment:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_corpus_segments (
                    id, document_version_id, creator_id, sequence, start_seconds, end_seconds,
                    text, confidence, review_state, source_reference_type, source_reference_id,
                    metadata_json, created_at
                ) VALUES (
                    :id, :document_version_id, :creator_id, :sequence, :start_seconds, :end_seconds,
                    :text, :confidence, :review_state, :source_reference_type, :source_reference_id,
                    :metadata_json, :created_at
                )
                ON CONFLICT(document_version_id, sequence) DO UPDATE SET
                    start_seconds = excluded.start_seconds,
                    end_seconds = excluded.end_seconds,
                    text = excluded.text,
                    confidence = excluded.confidence,
                    review_state = excluded.review_state,
                    source_reference_type = excluded.source_reference_type,
                    source_reference_id = excluded.source_reference_id,
                    metadata_json = excluded.metadata_json
                """,
                {
                    **segment.to_dict(),
                    "created_at": segment.created_at.isoformat(),
                },
            )
            row = connection.execute(
                "SELECT * FROM creator_corpus_segments WHERE document_version_id = ? AND sequence = ?",
                (segment.document_version_id, segment.sequence),
            ).fetchone()
        return _row_to_segment(row)

    def list_segments(self, document_version_id: str) -> list[CorpusSegment]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_corpus_segments WHERE document_version_id = ? ORDER BY sequence ASC",
                (document_version_id,),
            ).fetchall()
        return [_row_to_segment(row) for row in rows]

    def upsert_provenance_edge(self, edge: CorpusProvenanceEdge) -> CorpusProvenanceEdge:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_corpus_provenance_edges (
                    id, creator_id, parent_type, parent_id, child_version_id,
                    relation_type, metadata_json, created_at
                ) VALUES (
                    :id, :creator_id, :parent_type, :parent_id, :child_version_id,
                    :relation_type, :metadata_json, :created_at
                )
                ON CONFLICT(child_version_id, parent_type, parent_id, relation_type) DO NOTHING
                """,
                {
                    **edge.to_dict(),
                    "relation_type": edge.relation_type.value,
                    "created_at": edge.created_at.isoformat(),
                },
            )
            row = connection.execute(
                """
                SELECT * FROM creator_corpus_provenance_edges
                WHERE child_version_id = ? AND parent_type = ? AND parent_id = ? AND relation_type = ?
                """,
                (edge.child_version_id, edge.parent_type, edge.parent_id, edge.relation_type.value),
            ).fetchone()
        return _row_to_edge(row)

    def list_provenance_edges(self, document_version_id: str) -> list[CorpusProvenanceEdge]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_corpus_provenance_edges WHERE child_version_id = ? ORDER BY created_at ASC",
                (document_version_id,),
            ).fetchall()
        return [_row_to_edge(row) for row in rows]

    def archive_document(self, document_id: str) -> CorpusDocument | None:
        current = self.get_document(document_id)
        if current is None:
            return None
        updated = CorpusDocument(
            id=current.id,
            creator_id=current.creator_id,
            source_asset_id=current.source_asset_id,
            project_id=current.project_id,
            document_type=current.document_type,
            title=current.title,
            language=current.language,
            current_version_id=current.current_version_id,
            status=CorpusDocumentStatus.ARCHIVED,
            document_identity_hash=current.document_identity_hash,
            created_at=current.created_at,
            updated_at=utc_now(),
        )
        stored = self.upsert_document(updated)
        self.refresh_retrieval_index_for_document(document_id)
        return stored

    def mark_source_asset_missing(self, source_asset_id: str) -> CorpusSourceAsset | None:
        current = self.get_source_asset(source_asset_id)
        if current is None:
            return None
        updated = CorpusSourceAsset(
            id=current.id,
            creator_id=current.creator_id,
            project_id=current.project_id,
            source_type=current.source_type,
            original_name=current.original_name,
            local_path=current.local_path,
            content_hash=current.content_hash,
            size_bytes=current.size_bytes,
            mime_type=current.mime_type,
            status=CorpusSourceAssetStatus.MISSING,
            source_metadata_json=current.source_metadata_json,
            created_at=current.created_at,
            imported_at=current.imported_at,
            updated_at=utc_now(),
        )
        return self.upsert_source_asset(updated)

    def supports_fts5(self) -> bool:
        return _supports_fts5()

    def _delete_retrieval_rows_for_document(self, connection: sqlite3.Connection, document_id: str) -> None:
        connection.execute(
            "DELETE FROM creator_corpus_retrieval_index WHERE document_id = ?",
            (document_id,),
        )

    def _upsert_retrieval_row(self, connection: sqlite3.Connection, payload: dict[str, object]) -> None:
        connection.execute(
            """
            INSERT INTO creator_corpus_retrieval_index (
                retrieval_key, creator_id, project_id, document_id, version_id, segment_id,
                row_kind, document_type, title, language, authorship_class, source_kind,
                source_asset_id, status, retrieval_eligible, voice_learning_eligible,
                is_current_version, version_number, content_text, search_text,
                provenance_summary, segment_start_seconds, segment_end_seconds,
                segment_confidence, segment_review_state, quality_flags_json,
                created_at, updated_at, version_created_at, document_updated_at
            ) VALUES (
                :retrieval_key, :creator_id, :project_id, :document_id, :version_id, :segment_id,
                :row_kind, :document_type, :title, :language, :authorship_class, :source_kind,
                :source_asset_id, :status, :retrieval_eligible, :voice_learning_eligible,
                :is_current_version, :version_number, :content_text, :search_text,
                :provenance_summary, :segment_start_seconds, :segment_end_seconds,
                :segment_confidence, :segment_review_state, :quality_flags_json,
                :created_at, :updated_at, :version_created_at, :document_updated_at
            )
            ON CONFLICT(retrieval_key) DO UPDATE SET
                project_id = excluded.project_id,
                document_id = excluded.document_id,
                version_id = excluded.version_id,
                segment_id = excluded.segment_id,
                row_kind = excluded.row_kind,
                document_type = excluded.document_type,
                title = excluded.title,
                language = excluded.language,
                authorship_class = excluded.authorship_class,
                source_kind = excluded.source_kind,
                source_asset_id = excluded.source_asset_id,
                status = excluded.status,
                retrieval_eligible = excluded.retrieval_eligible,
                voice_learning_eligible = excluded.voice_learning_eligible,
                is_current_version = excluded.is_current_version,
                version_number = excluded.version_number,
                content_text = excluded.content_text,
                search_text = excluded.search_text,
                provenance_summary = excluded.provenance_summary,
                segment_start_seconds = excluded.segment_start_seconds,
                segment_end_seconds = excluded.segment_end_seconds,
                segment_confidence = excluded.segment_confidence,
                segment_review_state = excluded.segment_review_state,
                quality_flags_json = excluded.quality_flags_json,
                updated_at = excluded.updated_at,
                version_created_at = excluded.version_created_at,
                document_updated_at = excluded.document_updated_at
            """,
            payload,
        )

    def refresh_retrieval_index_for_document(self, document_id: str) -> int:
        document = self.get_document(document_id)
        if document is None:
            return 0
        versions = self.list_document_versions(document_id)
        if not versions:
            with self._database.connect() as connection:
                self._delete_retrieval_rows_for_document(connection, document_id)
            return 0
        provenance_by_version = {version.id: self.list_provenance_edges(version.id) for version in versions}
        segments_by_version = {version.id: self.list_segments(version.id) for version in versions}
        document_updated_at = document.updated_at.isoformat()
        indexed_rows = 0
        with self._database.connect() as connection:
            self._delete_retrieval_rows_for_document(connection, document_id)
            for version in versions:
                metadata = _metadata_dict(version.metadata_json)
                provenance_summary = "; ".join(
                    f"{edge.relation_type.value}:{edge.parent_type}:{edge.parent_id[:12]}"
                    for edge in provenance_by_version.get(version.id, ())
                )
                content_text = str(metadata.get("normalized_content", version.normalized_content or version.content or ""))
                search_text = _search_text(document.title, content_text, provenance_summary)
                payload = {
                    "retrieval_key": f"{document.id}:document:{version.id}",
                    "creator_id": document.creator_id,
                    "project_id": document.project_id,
                    "document_id": document.id,
                    "version_id": version.id,
                    "segment_id": None,
                    "row_kind": "document",
                    "document_type": document.document_type.value,
                    "title": document.title,
                    "language": version.language or document.language,
                    "authorship_class": version.authorship_class.value,
                    "source_kind": version.source_kind.value,
                    "source_asset_id": version.source_asset_id,
                    "status": document.status.value,
                    "retrieval_eligible": 1 if version.retrieval_eligible else 0,
                    "voice_learning_eligible": 1 if version.voice_learning_eligible else 0,
                    "is_current_version": 1 if document.current_version_id == version.id else 0,
                    "version_number": version.version_number,
                    "content_text": content_text,
                    "search_text": search_text,
                    "provenance_summary": provenance_summary,
                    "segment_start_seconds": None,
                    "segment_end_seconds": None,
                    "segment_confidence": None,
                    "segment_review_state": None,
                    "quality_flags_json": version.metadata_json,
                    "created_at": version.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat(),
                    "version_created_at": version.created_at.isoformat(),
                    "document_updated_at": document_updated_at,
                }
                self._upsert_retrieval_row(connection, payload)
                indexed_rows += 1
                for segment in segments_by_version.get(version.id, ()):
                    segment_metadata = _metadata_dict(segment.metadata_json)
                    segment_search_text = _search_text(document.title, segment.text, provenance_summary)
                    segment_payload = {
                        "retrieval_key": f"{document.id}:segment:{segment.id}",
                        "creator_id": document.creator_id,
                        "project_id": document.project_id,
                        "document_id": document.id,
                        "version_id": version.id,
                        "segment_id": segment.id,
                        "row_kind": "segment",
                        "document_type": document.document_type.value,
                        "title": document.title,
                        "language": version.language or document.language,
                        "authorship_class": version.authorship_class.value,
                        "source_kind": version.source_kind.value,
                        "source_asset_id": version.source_asset_id,
                        "status": document.status.value,
                        "retrieval_eligible": 1 if segment.retrieval_eligible and version.retrieval_eligible else 0,
                        "voice_learning_eligible": 1 if segment.voice_learning_eligible and version.voice_learning_eligible else 0,
                        "is_current_version": 1 if document.current_version_id == version.id else 0,
                        "version_number": version.version_number,
                        "content_text": segment.text,
                        "search_text": segment_search_text,
                        "provenance_summary": provenance_summary,
                        "segment_start_seconds": segment.start_seconds,
                        "segment_end_seconds": segment.end_seconds,
                        "segment_confidence": segment.confidence,
                        "segment_review_state": segment.review_state,
                        "quality_flags_json": _json_dumps(
                            {
                                **segment_metadata,
                                "raw_text": segment.raw_text,
                                "normalization_version": segment.normalization_version,
                                "quality_flags": list(segment.quality_flags),
                            }
                        ),
                        "created_at": segment.created_at.isoformat(),
                        "updated_at": document.updated_at.isoformat(),
                        "version_created_at": version.created_at.isoformat(),
                        "document_updated_at": document_updated_at,
                    }
                    self._upsert_retrieval_row(connection, segment_payload)
                    indexed_rows += 1
        return indexed_rows

    def rebuild_retrieval_index(self, creator_id: str | None = None) -> int:
        if creator_id is not None:
            documents = self.list_documents(creator_id)
        else:
            with self._database.connect() as connection:
                rows = connection.execute("SELECT * FROM creator_corpus_documents ORDER BY created_at ASC").fetchall()
            documents = [_row_to_document(row) for row in rows]
        total = 0
        for document in documents:
            total += self.refresh_retrieval_index_for_document(document.id)
        return total

    def search_retrieval_rows(self, query: CorpusRetrievalQuery) -> tuple[list[dict[str, object]], int]:
        if query.limit <= 0:
            return [], 0
        normalized_query = _normalize_like_text(query.query_text) if query.query_text else ""
        search_tokens = _build_search_tokens(query.query_text) if query.query_text else ()
        where_clauses = ["idx.creator_id = ?"]
        params: list[object] = [query.creator_id]
        if query.project_id is not None:
            where_clauses.append("IFNULL(idx.project_id, '') = IFNULL(?, '')")
            params.append(query.project_id)
        if query.document_id is not None:
            where_clauses.append("idx.document_id = ?")
            params.append(query.document_id)
        if query.segment_id is not None:
            where_clauses.append("idx.segment_id = ?")
            params.append(query.segment_id)
        if query.source_asset_id is not None:
            where_clauses.append("idx.source_asset_id = ?")
            params.append(query.source_asset_id)
        if query.retrieval_eligible_only:
            where_clauses.append("idx.retrieval_eligible = 1")
        if query.current_versions_only:
            where_clauses.append("idx.is_current_version = 1")
        if query.document_types:
            where_clauses.append(f"idx.document_type IN ({', '.join('?' for _ in query.document_types)})")
            params.extend(item.value if hasattr(item, "value") else str(item) for item in query.document_types)
        if query.authorship_classes:
            where_clauses.append(f"idx.authorship_class IN ({', '.join('?' for _ in query.authorship_classes)})")
            params.extend(item.value if hasattr(item, "value") else str(item) for item in query.authorship_classes)
        if query.languages:
            where_clauses.append(f"idx.language IN ({', '.join('?' for _ in query.languages)})")
            params.extend(query.languages)
        if query.statuses:
            where_clauses.append(f"idx.status IN ({', '.join('?' for _ in query.statuses)})")
            params.extend(item.value if hasattr(item, "value") else str(item) for item in query.statuses)
        else:
            where_clauses.append("idx.status = 'active'")
        if query.date_from is not None:
            where_clauses.append("idx.version_created_at >= ?")
            params.append(query.date_from.isoformat())
        if query.date_to is not None:
            where_clauses.append("idx.version_created_at <= ?")
            params.append(query.date_to.isoformat())
        select_score = "0.0 AS relevance_score"
        order_clause = "idx.updated_at DESC, idx.title ASC, idx.version_number DESC"
        score_params: list[object] = []
        if query.query_text and normalized_query:
            if search_tokens:
                where_clauses.append(
                    "(" + " AND ".join("instr(lower(idx.search_text), lower(?)) > 0" for _ in search_tokens) + ")"
                )
                params.extend(search_tokens)
            else:
                where_clauses.append("instr(lower(idx.search_text), lower(?)) > 0")
                params.append(normalized_query)
            select_score = (
                "("
                "CASE WHEN lower(idx.title) = lower(?) THEN 250.0 ELSE 0.0 END + "
                "CASE WHEN instr(lower(idx.title), lower(?)) > 0 THEN 120.0 ELSE 0.0 END + "
                "CASE WHEN instr(lower(idx.content_text), lower(?)) > 0 THEN 80.0 ELSE 0.0 END + "
                "CASE WHEN instr(lower(idx.provenance_summary), lower(?)) > 0 THEN 10.0 ELSE 0.0 END + "
                "CASE WHEN idx.is_current_version = 1 THEN 15.0 ELSE 0.0 END + "
                "CASE WHEN IFNULL(idx.project_id, '') = IFNULL(?, '') THEN 5.0 ELSE 0.0 END"
                ") AS relevance_score"
            )
            score_params = [normalized_query, normalized_query, normalized_query, normalized_query, query.project_id or ""]
            order_clause = "relevance_score DESC, idx.updated_at DESC, idx.title ASC"
        elif query.sort == CorpusRetrievalSort.UPDATED_DESC:
            order_clause = "idx.updated_at DESC, idx.title ASC"
        elif query.sort == CorpusRetrievalSort.CREATED_DESC:
            order_clause = "idx.created_at DESC, idx.title ASC"
        elif query.sort == CorpusRetrievalSort.TITLE:
            order_clause = "idx.title ASC, idx.updated_at DESC"
        query_sql = f"""
            SELECT idx.*, {select_score}
            FROM creator_corpus_retrieval_index AS idx
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """
        count_sql = f"""
            SELECT COUNT(*)
            FROM creator_corpus_retrieval_index AS idx
            WHERE {' AND '.join(where_clauses)}
        """
        count_params = list(params)
        query_params = score_params + list(params) + [int(query.limit), int(query.offset)]
        with self._database.connect() as connection:
            total = int(connection.execute(count_sql, count_params).fetchone()[0])
            rows = connection.execute(query_sql, query_params).fetchall()
        return [dict(row) for row in rows], total

    def get_retrieval_index_health(self, creator_id: str | None = None) -> CorpusRetrievalIndexHealth:
        if creator_id is None:
            creator_filter = ""
            params: list[object] = []
        else:
            creator_filter = "WHERE creator_id = ?"
            params = [creator_id]
        with self._database.connect() as connection:
            document_count = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM creator_corpus_documents {creator_filter}",
                    params,
                ).fetchone()[0]
            )
            version_count = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM creator_corpus_document_versions WHERE document_id IN (SELECT id FROM creator_corpus_documents {creator_filter})",
                    params,
                ).fetchone()[0]
            )
            segment_count = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM creator_corpus_segments WHERE document_version_id IN (SELECT id FROM creator_corpus_document_versions WHERE document_id IN (SELECT id FROM creator_corpus_documents {creator_filter}))",
                    params,
                ).fetchone()[0]
            )
            indexed_rows = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM creator_corpus_retrieval_index {creator_filter}",
                    params,
                ).fetchone()[0]
            )
            indexed_document_rows = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM creator_corpus_retrieval_index WHERE row_kind = 'document' {'AND creator_id = ?' if creator_id is not None else ''}",
                    params,
                ).fetchone()[0]
            )
            indexed_segment_rows = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM creator_corpus_retrieval_index WHERE row_kind = 'segment' {'AND creator_id = ?' if creator_id is not None else ''}",
                    params,
                ).fetchone()[0]
            )
        expected_rows = version_count + segment_count
        missing_rows = max(0, expected_rows - indexed_rows)
        stale_rows = max(0, indexed_rows - expected_rows)
        return CorpusRetrievalIndexHealth(
            creator_id=creator_id,
            supports_fts5=self.supports_fts5(),
            document_count=document_count,
            version_count=version_count,
            segment_count=segment_count,
            indexed_row_count=indexed_rows,
            indexed_document_row_count=indexed_document_rows,
            indexed_segment_row_count=indexed_segment_rows,
            expected_row_count=expected_rows,
            missing_row_count=missing_rows,
            stale_row_count=stale_rows,
        )
