"""Servicio de recuperacion determinista para Creator Corpus."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from creator_intelligence_studio.domain.creator_corpus.entities import CorpusDocument, CorpusDocumentVersion
from creator_intelligence_studio.domain.creator_corpus.repositories import CreatorCorpusRepository
from creator_intelligence_studio.domain.creator_corpus.retrieval import (
    CorpusRetrievalIndexHealth,
    CorpusRetrievalQuery,
    CorpusRetrievalResult,
    CorpusRetrievalResultItem,
    CorpusRetrievalSort,
)
from creator_intelligence_studio.domain.creator_corpus.value_objects import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
)
from creator_intelligence_studio.domain.errors import ValidationError
from creator_intelligence_studio.shared.dates import from_iso_z


def _normalize_query_text(value: str | None) -> str:
    return " ".join((value or "").split())


def _tokenize_query(value: str | None) -> tuple[str, ...]:
    normalized = _normalize_query_text(value).lower()
    return tuple(token for token in re.findall(r"(?u)[\w]+", normalized) if token)


def _build_snippet(text: str, query_text: str | None, limit: int = 180) -> str:
    clean = " ".join((text or "").split())
    if not clean:
        return ""
    normalized_query = _normalize_query_text(query_text).lower()
    lowered = clean.lower()
    start = 0
    end = min(len(clean), limit)
    if normalized_query:
        index = lowered.find(normalized_query)
        if index < 0:
            for token in _tokenize_query(query_text):
                index = lowered.find(token)
                if index >= 0:
                    normalized_query = token
                    break
        if index >= 0:
            start = max(0, index - 60)
            end = min(len(clean), index + len(normalized_query) + 120)
    snippet = clean[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(clean):
        snippet = snippet + "…"
    return snippet


def _enum_values(values):
    return tuple(item.value if hasattr(item, "value") else str(item) for item in values)


@dataclass(frozen=True, slots=True)
class CreatorCorpusRetrievalService:
    repository: CreatorCorpusRepository
    logger: logging.Logger | None = None

    def search(self, query: CorpusRetrievalQuery | dict[str, object]) -> CorpusRetrievalResult:
        normalized_query = self._normalize_query(query)
        rows, total = self.repository.search_retrieval_rows(normalized_query)
        matches = tuple(self._row_to_result_item(row, normalized_query) for row in rows)
        index_health = self.repository.get_retrieval_index_health(normalized_query.creator_id)
        return CorpusRetrievalResult(
            query=normalized_query,
            total_count=total,
            returned_count=len(matches),
            results=matches,
            index_health=index_health,
        )

    def rebuild_index(self, creator_id: str | None = None) -> CorpusRetrievalIndexHealth:
        if creator_id is not None and not creator_id.strip():
            raise ValidationError("El creator_id no puede estar vacio.")
        self.repository.rebuild_retrieval_index(creator_id)
        return self.repository.get_retrieval_index_health(creator_id)

    def index_status(self, creator_id: str | None = None) -> CorpusRetrievalIndexHealth:
        if creator_id is not None and not creator_id.strip():
            raise ValidationError("El creator_id no puede estar vacio.")
        return self.repository.get_retrieval_index_health(creator_id)

    def _normalize_query(self, query: CorpusRetrievalQuery | dict[str, object]) -> CorpusRetrievalQuery:
        if isinstance(query, CorpusRetrievalQuery):
            normalized = query
        else:
            normalized = CorpusRetrievalQuery(**query)
        if not normalized.creator_id or not normalized.creator_id.strip():
            raise ValidationError("El creator_id es obligatorio para recuperar el corpus.")
        limit = max(1, min(int(normalized.limit), 100))
        offset = max(0, int(normalized.offset))
        query_text = _normalize_query_text(normalized.query_text) or None
        return CorpusRetrievalQuery(
            creator_id=normalized.creator_id,
            query_text=query_text,
            project_id=normalized.project_id,
            document_types=tuple(normalized.document_types),
            authorship_classes=tuple(normalized.authorship_classes),
            languages=tuple(normalized.languages),
            statuses=tuple(normalized.statuses),
            retrieval_eligible_only=normalized.retrieval_eligible_only,
            current_versions_only=normalized.current_versions_only,
            date_from=normalized.date_from,
            date_to=normalized.date_to,
            source_asset_id=normalized.source_asset_id,
            document_id=normalized.document_id,
            segment_id=normalized.segment_id,
            limit=limit,
            offset=offset,
            sort=normalized.sort if isinstance(normalized.sort, CorpusRetrievalSort) else CorpusRetrievalSort(str(normalized.sort)),
        )

    def _row_to_result_item(self, row: dict[str, object], query: CorpusRetrievalQuery) -> CorpusRetrievalResultItem:
        content_text = str(row.get("content_text", ""))
        title = str(row.get("title", ""))
        query_text = query.query_text
        snippet_source = content_text or str(row.get("search_text", ""))
        snippet = _build_snippet(snippet_source, query_text)
        lower_title = title.lower()
        lower_content = content_text.lower()
        lower_search = str(row.get("search_text", "")).lower()
        normalized_query = _normalize_query_text(query_text).lower()
        token_matches = [token for token in _tokenize_query(query_text) if token in lower_search]
        match_reasons: list[str] = []
        if query.project_id and str(row.get("project_id") or "") == query.project_id:
            match_reasons.append("Filtrado por proyecto")
        if query.document_id and str(row.get("document_id") or "") == query.document_id:
            match_reasons.append("Filtrado por documento")
        if query.segment_id and str(row.get("segment_id") or "") == query.segment_id:
            match_reasons.append("Filtrado por segmento")
        if normalized_query and normalized_query in lower_title:
            match_reasons.append("Coincidencia en título")
        if normalized_query and normalized_query in lower_content:
            match_reasons.append("Coincidencia exacta de frase")
        elif token_matches:
            match_reasons.append("Coincidencia textual")
        if str(row.get("row_kind")) == "segment":
            match_reasons.append("Coincidencia en segmento")
        provenance_summary = str(row.get("provenance_summary") or "")
        relevance_reason = "; ".join(dict.fromkeys(match_reasons)) if match_reasons else "Filtrado estructurado"
        version_created_at = from_iso_z(str(row.get("version_created_at"))) or from_iso_z(str(row.get("created_at")))
        created_at = from_iso_z(str(row.get("created_at")))
        updated_at = from_iso_z(str(row.get("updated_at")))
        return CorpusRetrievalResultItem(
            creator_id=str(row.get("creator_id")),
            project_id=row.get("project_id") if row.get("project_id") is not None else None,
            document_id=str(row.get("document_id")),
            version_id=str(row.get("version_id")),
            segment_id=row.get("segment_id") if row.get("segment_id") is not None else None,
            row_kind=str(row.get("row_kind")),
            document_type=CorpusDocumentType(str(row.get("document_type"))),
            title=title,
            language=row.get("language") if row.get("language") is not None else None,
            authorship_class=CorpusAuthorshipClass(str(row.get("authorship_class"))),
            source_kind=str(row.get("source_kind")),
            source_asset_id=row.get("source_asset_id") if row.get("source_asset_id") is not None else None,
            status=CorpusDocumentStatus(str(row.get("status"))),
            text=content_text,
            snippet=snippet,
            provenance_summary=provenance_summary,
            retrieval_eligible=bool(row.get("retrieval_eligible")),
            voice_learning_eligible=bool(row.get("voice_learning_eligible")),
            is_current_version=bool(row.get("is_current_version")),
            version_number=int(row.get("version_number") or 0),
            segment_start_seconds=row.get("segment_start_seconds"),
            segment_end_seconds=row.get("segment_end_seconds"),
            segment_confidence=row.get("segment_confidence"),
            segment_review_state=row.get("segment_review_state") if row.get("segment_review_state") is not None else None,
            quality_flags=tuple(json.loads(str(row.get("quality_flags_json") or "{}")).get("quality_flags", ())),
            relevance_score=float(row.get("relevance_score") or 0.0),
            relevance_reason=relevance_reason,
            match_reasons=tuple(dict.fromkeys(match_reasons)),
            created_at=created_at or version_created_at or from_iso_z(str(row.get("document_updated_at"))) or from_iso_z("1970-01-01T00:00:00Z"),
            updated_at=updated_at or created_at or version_created_at or from_iso_z("1970-01-01T00:00:00Z"),
            version_created_at=version_created_at or created_at or from_iso_z("1970-01-01T00:00:00Z"),
        )
