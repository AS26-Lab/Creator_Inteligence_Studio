"""Indice semantico local y creator-scoped para Creator Corpus."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import numpy as np

from creator_intelligence_studio.application.services.creator_corpus_embedding_service import CreatorCorpusEmbeddingService
from creator_intelligence_studio.domain.creator_corpus import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusRetrievalQuery,
    CorpusRetrievalResultItem,
    CorpusRetrievalSort,
)
from creator_intelligence_studio.domain.creator_corpus.repositories import CreatorCorpusRepository
from creator_intelligence_studio.domain.semantic_embedding import (
    SEMANTIC_MODEL_CHUNKING_VERSION,
    SemanticEmbeddingModelHealth,
    build_default_semantic_embedding_model_manifest,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _vector_blob(vector: np.ndarray) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def _vector_from_blob(blob: bytes, dimension: int) -> np.ndarray:
    vector = np.frombuffer(blob, dtype=np.float32)
    if vector.size != dimension:
        raise ValueError("Dimension vectorial invalida.")
    return vector.reshape(1, dimension)


@dataclass(frozen=True, slots=True)
class SemanticIndexChunk:
    chunk_id: str
    creator_id: str
    document_id: str
    version_id: str
    segment_id: str | None
    chunking_version: str
    content_hash: str
    text: str
    embedding_model_id: str
    embedding_model_revision: str
    vector: np.ndarray
    document_type: str
    authorship_class: str
    status: str
    project_id: str | None
    is_current_version: bool
    retrieval_eligible: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SemanticIndexHealth:
    creator_id: str | None
    status: str
    generation_id: str | None
    indexed_chunk_count: int
    expected_chunk_count: int
    stale_chunk_count: int
    orphan_chunk_count: int
    model_revision: str | None
    model_dimension: int | None
    chunking_version: str | None
    last_build_started_at: str | None
    last_build_completed_at: str | None
    last_build_duration_ms: float | None
    embedding_health: SemanticEmbeddingModelHealth | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "status": self.status,
            "generation_id": self.generation_id,
            "indexed_chunk_count": self.indexed_chunk_count,
            "expected_chunk_count": self.expected_chunk_count,
            "stale_chunk_count": self.stale_chunk_count,
            "orphan_chunk_count": self.orphan_chunk_count,
            "model_revision": self.model_revision,
            "model_dimension": self.model_dimension,
            "chunking_version": self.chunking_version,
            "last_build_started_at": self.last_build_started_at,
            "last_build_completed_at": self.last_build_completed_at,
            "last_build_duration_ms": self.last_build_duration_ms,
            "embedding_health": self.embedding_health.to_dict() if self.embedding_health else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class SemanticIndexSearchResult:
    creator_id: str
    query_text: str
    used_mode: str
    generation_id: str | None
    results: tuple[CorpusRetrievalResultItem, ...]
    scores: tuple[float, ...]
    health: SemanticIndexHealth

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "query_text": self.query_text,
            "used_mode": self.used_mode,
            "generation_id": self.generation_id,
            "results": [item.to_dict() for item in self.results],
            "scores": list(self.scores),
            "health": self.health.to_dict(),
        }


class CreatorCorpusSemanticIndexService:
    """Boundary derived local para embeddings y busqueda semantica."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        corpus_repository: CreatorCorpusRepository,
        embedding_service: CreatorCorpusEmbeddingService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.corpus_repository = corpus_repository
        self.embedding_service = embedding_service or CreatorCorpusEmbeddingService(paths=paths)
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_corpus.semantic_index")
        self.manifest = build_default_semantic_embedding_model_manifest()
        self.database_path = self.paths.data_directory / "semantic_index.sqlite"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_index_generations (
                    generation_id TEXT PRIMARY KEY,
                    creator_id TEXT NOT NULL,
                    embedding_model_id TEXT NOT NULL,
                    embedding_model_revision TEXT NOT NULL,
                    chunking_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model_dimension INTEGER NOT NULL,
                    total_chunks INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    build_started_at TEXT,
                    build_completed_at TEXT,
                    build_duration_ms REAL,
                    notes TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_index_chunks (
                    generation_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    creator_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    segment_id TEXT,
                    chunking_version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding_model_id TEXT NOT NULL,
                    embedding_model_revision TEXT NOT NULL,
                    vector_blob BLOB NOT NULL,
                    document_type TEXT NOT NULL,
                    authorship_class TEXT NOT NULL,
                    status TEXT NOT NULL,
                    project_id TEXT,
                    is_current_version INTEGER NOT NULL,
                    retrieval_eligible INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (generation_id, chunk_id),
                    FOREIGN KEY (generation_id) REFERENCES semantic_index_generations(generation_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_index_active_generations (
                    creator_id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (generation_id) REFERENCES semantic_index_generations(generation_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_semantic_index_chunks_creator ON semantic_index_chunks(creator_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_semantic_index_chunks_document ON semantic_index_chunks(document_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_semantic_index_generations_creator ON semantic_index_generations(creator_id, status)")

    def _active_generation_id(self, creator_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT generation_id FROM semantic_index_active_generations WHERE creator_id = ?",
                (creator_id,),
            ).fetchone()
        return str(row["generation_id"]) if row else None

    def _eligible_documents(self, creator_id: str) -> list[tuple[object, object]]:
        documents = []
        for document in self.corpus_repository.list_documents(creator_id):
            if document.status != CorpusDocumentStatus.ACTIVE:
                continue
            for version in self.corpus_repository.list_document_versions(document.id):
                if not version.retrieval_eligible:
                    continue
                if document.current_version_id != version.id and version.created_at and not version.retrieval_eligible:
                    continue
                documents.append((document, version))
        return documents

    def _chunks_for_version(self, document, version) -> list[SemanticIndexChunk]:
        created_at = version.created_at
        base_text = version.normalized_content or version.content or ""
        chunks: list[SemanticIndexChunk] = []
        if document.document_type == CorpusDocumentType.TRANSCRIPT:
            segments = self.corpus_repository.list_segments(version.id)
            grouped: list[list[object]] = []
            current: list[object] = []
            last_end: float | None = None
            for segment in sorted(segments, key=lambda item: (float(item.start_seconds or 0.0), item.sequence)):
                start = float(segment.start_seconds or 0.0)
                end = float(segment.end_seconds or start)
                if current and last_end is not None and start - last_end > 2.0:
                    grouped.append(current)
                    current = []
                current.append(segment)
                last_end = end
            if current:
                grouped.append(current)
            for sequence, group in enumerate(grouped, start=1):
                chunk_text = "\n".join(segment.text for segment in group if getattr(segment, "text", ""))
                if not chunk_text.strip():
                    continue
                chunk_id = f"{version.id}:segment-group:{sequence}"
                content_hash = _sha256_text(chunk_text)
                chunks.append(
                    SemanticIndexChunk(
                        chunk_id=chunk_id,
                        creator_id=document.creator_id,
                        document_id=document.id,
                        version_id=version.id,
                        segment_id=getattr(group[0], "id", None),
                        chunking_version=SEMANTIC_MODEL_CHUNKING_VERSION,
                        content_hash=content_hash,
                        text=chunk_text,
                        embedding_model_id=self.manifest.component_id,
                        embedding_model_revision=self.manifest.revision,
                        vector=np.zeros((1, self.manifest.embedding_dimension), dtype=np.float32),
                        document_type=document.document_type.value,
                        authorship_class=version.authorship_class.value,
                        status=document.status.value,
                        project_id=document.project_id,
                        is_current_version=document.current_version_id == version.id,
                        retrieval_eligible=version.retrieval_eligible,
                        created_at=created_at,
                    )
                )
            return chunks
        normalized = " ".join((base_text or "").split())
        if not normalized.strip():
            return chunks
        max_chunk_chars = 900
        step = 700
        start = 0
        sequence = 1
        while start < len(normalized):
            end = min(len(normalized), start + max_chunk_chars)
            chunk_text = normalized[start:end].strip()
            if chunk_text:
                chunk_id = f"{version.id}:chunk:{sequence}"
                chunks.append(
                    SemanticIndexChunk(
                        chunk_id=chunk_id,
                        creator_id=document.creator_id,
                        document_id=document.id,
                        version_id=version.id,
                        segment_id=None,
                        chunking_version=SEMANTIC_MODEL_CHUNKING_VERSION,
                        content_hash=_sha256_text(chunk_text),
                        text=chunk_text,
                        embedding_model_id=self.manifest.component_id,
                        embedding_model_revision=self.manifest.revision,
                        vector=np.zeros((1, self.manifest.embedding_dimension), dtype=np.float32),
                        document_type=document.document_type.value,
                        authorship_class=version.authorship_class.value,
                        status=document.status.value,
                        project_id=document.project_id,
                        is_current_version=document.current_version_id == version.id,
                        retrieval_eligible=version.retrieval_eligible,
                        created_at=created_at,
                    )
                )
            sequence += 1
            if end >= len(normalized):
                break
            start += step
        return chunks

    def _load_chunks_for_generation(self, generation_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM semantic_index_chunks WHERE generation_id = ? ORDER BY created_at ASC, chunk_id ASC",
                (generation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _expected_chunks_for_creator(self, creator_id: str, *, cancellation_token=None) -> list[SemanticIndexChunk]:
        expected: list[SemanticIndexChunk] = []
        for document, version in self._eligible_documents(creator_id):
            if cancellation_token is not None and getattr(cancellation_token, "cancelled", lambda: False)():
                break
            expected.extend(self._chunks_for_version(document, version))
        return expected

    def build_index(self, creator_id: str, *, cancellation_token=None) -> dict[str, object]:
        creator_id = creator_id.strip()
        if not creator_id:
            raise ValueError("El creator_id es obligatorio.")
        build_started = _now()
        generation_id = uuid4().hex
        generation_rows = self._expected_chunks_for_creator(creator_id, cancellation_token=cancellation_token)
        health = self.embedding_service.health()
        if health.status != "ready":
            return {
                "creator_id": creator_id,
                "generation_id": generation_id,
                "status": "failed",
                "reason": "embedding_unavailable",
                "health": health.to_dict(),
            }
        if cancellation_token is not None and getattr(cancellation_token, "cancelled", lambda: False)():
            with self._connect() as connection:
                connection.execute(
                    "INSERT OR REPLACE INTO semantic_index_generations (generation_id, creator_id, embedding_model_id, embedding_model_revision, chunking_version, status, model_dimension, total_chunks, created_at, build_started_at, build_completed_at, build_duration_ms, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        generation_id,
                        creator_id,
                        self.manifest.component_id,
                        self.manifest.revision,
                        SEMANTIC_MODEL_CHUNKING_VERSION,
                        "interrupted",
                        self.manifest.embedding_dimension,
                        len(generation_rows),
                        build_started.isoformat(),
                        None,
                        None,
                        None,
                        "cancelled",
                    ),
                )
            return {
                "creator_id": creator_id,
                "generation_id": generation_id,
                "status": "interrupted",
                "health": health.to_dict(),
                "chunk_count": len(generation_rows),
            }
        vectors = self.embedding_service.embed([row.text for row in generation_rows], query_mode=False) if generation_rows else np.zeros((0, self.manifest.embedding_dimension), dtype=np.float32)
        build_completed = _now()
        duration_ms = (build_completed - build_started).total_seconds() * 1000.0
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO semantic_index_generations (generation_id, creator_id, embedding_model_id, embedding_model_revision, chunking_version, status, model_dimension, total_chunks, created_at, build_started_at, build_completed_at, build_duration_ms, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    generation_id,
                    creator_id,
                    self.manifest.component_id,
                    self.manifest.revision,
                    SEMANTIC_MODEL_CHUNKING_VERSION,
                    "staging",
                    self.manifest.embedding_dimension,
                    len(generation_rows),
                    build_started.isoformat(),
                    build_started.isoformat(),
                    build_completed.isoformat(),
                    duration_ms,
                    None,
                ),
            )
            for index, row in enumerate(generation_rows):
                vector = vectors[index:index + 1] if len(vectors) else np.zeros((1, self.manifest.embedding_dimension), dtype=np.float32)
                connection.execute(
                    """
                    INSERT INTO semantic_index_chunks (
                        generation_id, chunk_id, creator_id, document_id, version_id, segment_id,
                        chunking_version, content_hash, text, embedding_model_id, embedding_model_revision,
                        vector_blob, document_type, authorship_class, status, project_id,
                        is_current_version, retrieval_eligible, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        generation_id,
                        row.chunk_id,
                        row.creator_id,
                        row.document_id,
                        row.version_id,
                        row.segment_id,
                        row.chunking_version,
                        row.content_hash,
                        row.text,
                        row.embedding_model_id,
                        row.embedding_model_revision,
                        _vector_blob(vector),
                        row.document_type,
                        row.authorship_class,
                        row.status,
                        row.project_id,
                        1 if row.is_current_version else 0,
                        1 if row.retrieval_eligible else 0,
                        row.created_at.isoformat(),
                    ),
                )
            connection.execute(
                "INSERT OR REPLACE INTO semantic_index_active_generations (creator_id, generation_id, updated_at) VALUES (?, ?, ?)",
                (creator_id, generation_id, build_completed.isoformat()),
            )
            connection.execute(
                "UPDATE semantic_index_generations SET status = 'active' WHERE generation_id = ?",
                (generation_id,),
            )
        return {
            "creator_id": creator_id,
            "generation_id": generation_id,
            "status": "ready",
            "chunk_count": len(generation_rows),
            "duration_ms": duration_ms,
            "health": health.to_dict(),
        }

    def _chunks_to_items(self, rows: list[dict[str, object]], *, limit: int) -> tuple[CorpusRetrievalResultItem, ...]:
        items: list[CorpusRetrievalResultItem] = []
        for row in rows[:limit]:
            items.append(
                CorpusRetrievalResultItem(
                    creator_id=str(row["creator_id"]),
                    project_id=row["project_id"] if row["project_id"] is not None else None,
                    document_id=str(row["document_id"]),
                    version_id=str(row["version_id"]),
                    segment_id=row["segment_id"] if row["segment_id"] is not None else None,
                    row_kind="segment" if row["segment_id"] is not None else "document",
                    document_type=CorpusDocumentType(str(row["document_type"])),
                    title=str(row.get("title") or ""),
                    language=str(row.get("language") or "") or None,
                    authorship_class=CorpusAuthorshipClass(str(row["authorship_class"])),
                    source_kind="semantic_index",
                    source_asset_id=None,
                    status=CorpusDocumentStatus(str(row["status"])),
                    text=str(row["text"]),
                    snippet=str(row["text"])[:180],
                    provenance_summary="semantic_index",
                    retrieval_eligible=bool(row["retrieval_eligible"]),
                    voice_learning_eligible=False,
                    is_current_version=bool(row["is_current_version"]),
                    version_number=0,
                    segment_start_seconds=None,
                    segment_end_seconds=None,
                    segment_confidence=None,
                    segment_review_state=None,
                    quality_flags=(),
                    relevance_score=float(row["score"]),
                    relevance_reason="Semantic score",
                    match_reasons=("semantic",),
                    created_at=_now(),
                    updated_at=_now(),
                    version_created_at=_now(),
                    source_segment_ids=(str(row["segment_id"]),) if row["segment_id"] is not None else (),
                )
            )
        return tuple(items)

    def search(self, query: CorpusRetrievalQuery, *, limit: int | None = None) -> SemanticIndexSearchResult:
        generation_id = self._active_generation_id(query.creator_id)
        health = self.health(query.creator_id)
        if generation_id is None or health.status not in {"ready", "active"}:
            return SemanticIndexSearchResult(
                creator_id=query.creator_id,
                query_text=query.query_text or "",
                used_mode="lexical_fallback",
                generation_id=generation_id,
                results=(),
                scores=(),
                health=health,
            )
        query_text = (query.query_text or "").strip()
        if not query_text:
            return SemanticIndexSearchResult(
                creator_id=query.creator_id,
                query_text="",
                used_mode="semantic_unavailable",
                generation_id=generation_id,
                results=(),
                scores=(),
                health=health,
            )
        query_vector = self.embedding_service.embed([query_text], query_mode=True)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT idx.* FROM semantic_index_chunks AS idx WHERE idx.generation_id = ? AND idx.creator_id = ? AND idx.retrieval_eligible = 1 ORDER BY idx.created_at ASC",
                (generation_id, query.creator_id),
            ).fetchall()
        candidates = []
        corrupted = False
        for row in rows:
            try:
                vector = np.frombuffer(row["vector_blob"], dtype=np.float32).reshape(1, self.manifest.embedding_dimension)
            except Exception:
                corrupted = True
                break
            score = float(np.dot(query_vector[0], vector[0]))
            candidate = dict(row)
            candidate["score"] = score
            candidates.append(candidate)
        if corrupted:
            return SemanticIndexSearchResult(
                creator_id=query.creator_id,
                query_text=query_text,
                used_mode="lexical_fallback",
                generation_id=generation_id,
                results=(),
                scores=(),
                health=health,
            )
        if query.project_id is not None:
            candidates = [row for row in candidates if str(row.get("project_id") or "") == query.project_id]
        if query.document_id is not None:
            candidates = [row for row in candidates if str(row.get("document_id") or "") == query.document_id]
        if query.segment_id is not None:
            candidates = [row for row in candidates if str(row.get("segment_id") or "") == query.segment_id]
        if query.current_versions_only:
            candidates = [row for row in candidates if bool(row.get("is_current_version"))]
        if query.document_types:
            allowed_document_types = {item.value if hasattr(item, "value") else str(item) for item in query.document_types}
            candidates = [row for row in candidates if str(row.get("document_type") or "") in allowed_document_types]
        if query.authorship_classes:
            allowed_authorship = {item.value if hasattr(item, "value") else str(item) for item in query.authorship_classes}
            candidates = [row for row in candidates if str(row.get("authorship_class") or "") in allowed_authorship]
        if query.statuses:
            allowed_statuses = {item.value if hasattr(item, "value") else str(item) for item in query.statuses}
            candidates = [row for row in candidates if str(row.get("status") or "") in allowed_statuses]
        candidates.sort(key=lambda item: (-float(item["score"]), str(item["document_id"]), str(item["chunk_id"])))
        if limit is not None:
            candidates = candidates[:limit]
        items = self._chunks_to_items(candidates, limit=limit or len(candidates))
        scores = tuple(float(item.relevance_score) for item in items)
        return SemanticIndexSearchResult(
            creator_id=query.creator_id,
            query_text=query_text,
            used_mode="semantic",
            generation_id=generation_id,
            results=items,
            scores=scores,
            health=health,
        )

    def health(self, creator_id: str | None = None) -> SemanticIndexHealth:
        embedding_health = self.embedding_service.health()
        with self._connect() as connection:
            if creator_id is None:
                generation_row = connection.execute(
                    "SELECT * FROM semantic_index_generations WHERE status = 'active' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                active_rows = connection.execute("SELECT * FROM semantic_index_active_generations ORDER BY creator_id ASC").fetchall()
            else:
                generation_row = connection.execute(
                    "SELECT * FROM semantic_index_generations WHERE creator_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
                    (creator_id,),
                ).fetchone()
                active_rows = connection.execute(
                    "SELECT * FROM semantic_index_active_generations WHERE creator_id = ?",
                    (creator_id,),
                ).fetchall()
        if generation_row is None:
            return SemanticIndexHealth(
                creator_id=creator_id,
                status="missing",
                generation_id=None,
                indexed_chunk_count=0,
                expected_chunk_count=0,
                stale_chunk_count=0,
                orphan_chunk_count=0,
                model_revision=self.manifest.revision,
                model_dimension=self.manifest.embedding_dimension,
                chunking_version=SEMANTIC_MODEL_CHUNKING_VERSION,
                last_build_started_at=None,
                last_build_completed_at=None,
                last_build_duration_ms=None,
                embedding_health=embedding_health,
                warnings=(),
                errors=("No existe un indice semantico activo.",),
            )
        expected_chunks = self._expected_chunks_for_creator(str(generation_row["creator_id"]))
        stored_rows = self._load_chunks_for_generation(str(generation_row["generation_id"]))
        indexed_count = len(stored_rows)
        expected_count = len(expected_chunks)
        expected_by_id = {chunk.chunk_id: chunk for chunk in expected_chunks}
        stale = 0
        orphan = 0
        corrupted = 0
        status = "active"
        if embedding_health.status != "ready":
            status = "repair_required"
        if (
            int(generation_row["model_dimension"]) != self.manifest.embedding_dimension
            or str(generation_row["embedding_model_revision"]) != self.manifest.revision
            or str(generation_row["chunking_version"]) != SEMANTIC_MODEL_CHUNKING_VERSION
        ):
            status = "stale"
        for row in stored_rows:
            chunk_id = str(row["chunk_id"])
            expected = expected_by_id.get(chunk_id)
            vector_blob = row["vector_blob"]
            if not isinstance(vector_blob, (bytes, bytearray, memoryview)):
                corrupted += 1
                continue
            try:
                vector = np.frombuffer(bytes(vector_blob), dtype=np.float32)
            except ValueError:
                corrupted += 1
                continue
            if vector.size != self.manifest.embedding_dimension or not np.isfinite(vector).all():
                corrupted += 1
                continue
            if expected is None:
                orphan += 1
                continue
            if str(row["content_hash"]) != expected.content_hash or str(row["embedding_model_revision"]) != self.manifest.revision or str(row["chunking_version"]) != SEMANTIC_MODEL_CHUNKING_VERSION:
                stale += 1
        missing = max(0, expected_count - indexed_count)
        if corrupted > 0:
            status = "repair_required"
        elif stale > 0 or missing > 0 or orphan > 0:
            status = "stale"
        return SemanticIndexHealth(
            creator_id=creator_id,
            status=status,
            generation_id=str(generation_row["generation_id"]),
            indexed_chunk_count=indexed_count,
            expected_chunk_count=expected_count,
            stale_chunk_count=stale + missing,
            orphan_chunk_count=orphan,
            model_revision=str(generation_row["embedding_model_revision"]),
            model_dimension=int(generation_row["model_dimension"]),
            chunking_version=str(generation_row["chunking_version"]),
            last_build_started_at=generation_row["build_started_at"],
            last_build_completed_at=generation_row["build_completed_at"],
            last_build_duration_ms=float(generation_row["build_duration_ms"]) if generation_row["build_duration_ms"] is not None else None,
            embedding_health=embedding_health,
            warnings=(
                "El modelo semantico no esta listo.",
            ) if embedding_health.status != "ready" else (),
            errors=(
                "Hay vectores corruptos en el indice semantico.",
            ) if corrupted > 0 else (),
        )
