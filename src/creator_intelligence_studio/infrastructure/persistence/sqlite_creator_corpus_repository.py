"""Repositorio SQLite para Creator Corpus."""

from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from creator_intelligence_studio.domain.creator_corpus.entities import (
    CorpusDocument,
    CorpusDocumentVersion,
    CorpusProvenanceEdge,
    CorpusSegment,
    CorpusSourceAsset,
)
from creator_intelligence_studio.domain.creator_corpus.repositories import CreatorCorpusRepository
from creator_intelligence_studio.domain.creator_corpus.value_objects import (
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusVersionSourceKind,
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
    return CorpusDocumentVersion(
        id=row["id"],
        document_id=row["document_id"],
        creator_id=row["creator_id"],
        version_number=int(row["version_number"]),
        content=row["content"],
        content_hash=row["content_hash"],
        source_kind=CorpusVersionSourceKind(row["source_kind"]),
        source_asset_id=row["source_asset_id"],
        parent_version_id=row["parent_version_id"],
        language=row["language"],
        created_by=row["created_by"],
        metadata_json=row["metadata_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_segment(row: sqlite3.Row) -> CorpusSegment:
    return CorpusSegment(
        id=row["id"],
        document_version_id=row["document_version_id"],
        creator_id=row["creator_id"],
        sequence=int(row["sequence"]),
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        text=row["text"],
        confidence=row["confidence"],
        review_state=row["review_state"],
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
        return self.upsert_document(updated)

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
