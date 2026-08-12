"""Semantic and hybrid Creator Corpus evaluation utilities.

This module is intentionally local-only and evaluation-oriented. It does not
replace lexical retrieval as the product baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from typing import Protocol, Sequence

from creator_intelligence_studio.application.services.creator_corpus_retrieval_service import (
    CreatorCorpusRetrievalService,
)
from creator_intelligence_studio.domain.creator_corpus import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusRetrievalQuery,
    CorpusRetrievalResultItem,
    CorpusRetrievalSort,
)


class SemanticMatchMode(str, Enum):
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class SemanticScorer(Protocol):
    def score(self, query_text: str, candidates: Sequence[CorpusRetrievalResultItem]) -> Sequence[float]:
        """Return one score per candidate in the same order."""


@dataclass(frozen=True, slots=True)
class SemanticRetrievalCandidate:
    document_id: str
    version_id: str
    creator_id: str
    title: str
    text: str
    match_mode: SemanticMatchMode
    lexical_rank: int | None
    semantic_rank: int | None
    lexical_score: float
    semantic_score: float | None
    fused_score: float
    relevance_reason: str
    provenance_summary: str
    document_type: CorpusDocumentType
    authorship_class: CorpusAuthorshipClass
    status: CorpusDocumentStatus
    project_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "version_id": self.version_id,
            "creator_id": self.creator_id,
            "title": self.title,
            "text": self.text,
            "match_mode": self.match_mode.value,
            "lexical_rank": self.lexical_rank,
            "semantic_rank": self.semantic_rank,
            "lexical_score": self.lexical_score,
            "semantic_score": self.semantic_score,
            "fused_score": self.fused_score,
            "relevance_reason": self.relevance_reason,
            "provenance_summary": self.provenance_summary,
            "document_type": self.document_type.value,
            "authorship_class": self.authorship_class.value,
            "status": self.status.value,
            "project_id": self.project_id,
        }


@dataclass(frozen=True, slots=True)
class SemanticRetrievalCase:
    case_id: str
    creator_id: str
    query_text: str
    expected_document_ids: tuple[str, ...]
    project_id: str | None = None
    document_types: tuple[CorpusDocumentType | str, ...] = ()
    authorship_classes: tuple[CorpusAuthorshipClass | str, ...] = ()
    languages: tuple[str, ...] = ()
    statuses: tuple[CorpusDocumentStatus | str, ...] = ()
    retrieval_eligible_only: bool = True
    current_versions_only: bool = True
    limit: int = 10

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "creator_id": self.creator_id,
            "query_text": self.query_text,
            "expected_document_ids": list(self.expected_document_ids),
            "project_id": self.project_id,
            "document_types": [item.value if hasattr(item, "value") else str(item) for item in self.document_types],
            "authorship_classes": [item.value if hasattr(item, "value") else str(item) for item in self.authorship_classes],
            "languages": list(self.languages),
            "statuses": [item.value if hasattr(item, "value") else str(item) for item in self.statuses],
            "retrieval_eligible_only": self.retrieval_eligible_only,
            "current_versions_only": self.current_versions_only,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class SemanticRetrievalCaseResult:
    case: SemanticRetrievalCase
    lexical_document_ids: tuple[str, ...]
    semantic_document_ids: tuple[str, ...]
    hybrid_document_ids: tuple[str, ...]
    lexical_top1_hit: bool
    lexical_top3_recall: float
    lexical_top5_recall: float
    lexical_mrr: float
    semantic_top1_hit: bool
    semantic_top3_recall: float
    semantic_top5_recall: float
    semantic_mrr: float
    hybrid_top1_hit: bool
    hybrid_top3_recall: float
    hybrid_top5_recall: float
    hybrid_mrr: float
    lexical_latency_ms: float
    semantic_latency_ms: float | None
    hybrid_latency_ms: float | None
    semantic_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "case": self.case.to_dict(),
            "lexical_document_ids": list(self.lexical_document_ids),
            "semantic_document_ids": list(self.semantic_document_ids),
            "hybrid_document_ids": list(self.hybrid_document_ids),
            "lexical_top1_hit": self.lexical_top1_hit,
            "lexical_top3_recall": self.lexical_top3_recall,
            "lexical_top5_recall": self.lexical_top5_recall,
            "lexical_mrr": self.lexical_mrr,
            "semantic_top1_hit": self.semantic_top1_hit,
            "semantic_top3_recall": self.semantic_top3_recall,
            "semantic_top5_recall": self.semantic_top5_recall,
            "semantic_mrr": self.semantic_mrr,
            "hybrid_top1_hit": self.hybrid_top1_hit,
            "hybrid_top3_recall": self.hybrid_top3_recall,
            "hybrid_top5_recall": self.hybrid_top5_recall,
            "hybrid_mrr": self.hybrid_mrr,
            "lexical_latency_ms": self.lexical_latency_ms,
            "semantic_latency_ms": self.semantic_latency_ms,
            "hybrid_latency_ms": self.hybrid_latency_ms,
            "semantic_status": self.semantic_status,
        }


@dataclass(frozen=True, slots=True)
class SemanticRetrievalMetrics:
    case_count: int
    lexical_top1_hit_rate: float
    lexical_top3_recall: float
    lexical_top5_recall: float
    lexical_mrr: float
    semantic_top1_hit_rate: float | None
    semantic_top3_recall: float | None
    semantic_top5_recall: float | None
    semantic_mrr: float | None
    hybrid_top1_hit_rate: float | None
    hybrid_top3_recall: float | None
    hybrid_top5_recall: float | None
    hybrid_mrr: float | None
    lexical_latency_ms: float
    semantic_latency_ms: float | None
    hybrid_latency_ms: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "case_count": self.case_count,
            "lexical_top1_hit_rate": self.lexical_top1_hit_rate,
            "lexical_top3_recall": self.lexical_top3_recall,
            "lexical_top5_recall": self.lexical_top5_recall,
            "lexical_mrr": self.lexical_mrr,
            "semantic_top1_hit_rate": self.semantic_top1_hit_rate,
            "semantic_top3_recall": self.semantic_top3_recall,
            "semantic_top5_recall": self.semantic_top5_recall,
            "semantic_mrr": self.semantic_mrr,
            "hybrid_top1_hit_rate": self.hybrid_top1_hit_rate,
            "hybrid_top3_recall": self.hybrid_top3_recall,
            "hybrid_top5_recall": self.hybrid_top5_recall,
            "hybrid_mrr": self.hybrid_mrr,
            "lexical_latency_ms": self.lexical_latency_ms,
            "semantic_latency_ms": self.semantic_latency_ms,
            "hybrid_latency_ms": self.hybrid_latency_ms,
        }


@dataclass(frozen=True, slots=True)
class SemanticRetrievalEvaluationReport:
    metrics: SemanticRetrievalMetrics
    cases: tuple[SemanticRetrievalCaseResult, ...]
    semantic_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "metrics": self.metrics.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "semantic_status": self.semantic_status,
        }


def _reciprocal_rank_fusion(rankings: Sequence[Sequence[str]], *, rank_constant: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, document_id in enumerate(ranking, start=1):
            scores[document_id] = scores.get(document_id, 0.0) + 1.0 / (rank_constant + position)
    return scores


def _recall_at_k(ranked_document_ids: Sequence[str], expected_document_ids: Sequence[str], k: int) -> float:
    if not expected_document_ids:
        return 0.0
    hits = len(set(ranked_document_ids[:k]) & set(expected_document_ids))
    return hits / len(set(expected_document_ids))


def _mrr(ranked_document_ids: Sequence[str], expected_document_ids: Sequence[str]) -> float:
    expected = set(expected_document_ids)
    for index, document_id in enumerate(ranked_document_ids, start=1):
        if document_id in expected:
            return 1.0 / index
    return 0.0


class CreatorCorpusSemanticEvaluationService:
    def __init__(
        self,
        *,
        retrieval_service: CreatorCorpusRetrievalService,
        semantic_scorer: SemanticScorer | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.semantic_scorer = semantic_scorer

    def evaluate(self, cases: Sequence[SemanticRetrievalCase]) -> SemanticRetrievalEvaluationReport:
        case_results: list[SemanticRetrievalCaseResult] = []
        lexical_top1 = lexical_top3 = lexical_top5 = lexical_mrr = 0.0
        semantic_top1 = semantic_top3 = semantic_top5 = semantic_mrr = None
        hybrid_top1 = hybrid_top3 = hybrid_top5 = hybrid_mrr = None
        lexical_latency_total = semantic_latency_total = hybrid_latency_total = 0.0
        semantic_latency_count = hybrid_latency_count = 0
        semantic_status = "ready" if self.semantic_scorer is not None else "unavailable"

        for case in cases:
            lexical_result, lexical_latency = self._lexical_rank(case)
            lexical_latency_total += lexical_latency
            semantic_result: tuple[SemanticRetrievalCandidate, ...] = ()
            hybrid_result: tuple[SemanticRetrievalCandidate, ...] = lexical_result
            semantic_latency: float | None = None
            hybrid_latency: float | None = None
            if self.semantic_scorer is not None:
                semantic_result, semantic_latency = self._semantic_rank(case, lexical_result)
                hybrid_result, hybrid_latency = self._hybrid_rank(case, lexical_result, semantic_result)
                semantic_latency_total += semantic_latency
                hybrid_latency_total += hybrid_latency
                semantic_latency_count += 1
                hybrid_latency_count += 1

            lexical_ids = tuple(item.document_id for item in lexical_result)
            semantic_ids = tuple(item.document_id for item in semantic_result)
            hybrid_ids = tuple(item.document_id for item in hybrid_result)

            lexical_top1 += 1.0 if _recall_at_k(lexical_ids, case.expected_document_ids, 1) > 0 else 0.0
            lexical_top3 += _recall_at_k(lexical_ids, case.expected_document_ids, 3)
            lexical_top5 += _recall_at_k(lexical_ids, case.expected_document_ids, 5)
            lexical_mrr += _mrr(lexical_ids, case.expected_document_ids)

            semantic_top1 = (semantic_top1 or 0.0) + (1.0 if semantic_result and _recall_at_k(semantic_ids, case.expected_document_ids, 1) > 0 else 0.0) if self.semantic_scorer is not None else None
            semantic_top3 = (semantic_top3 or 0.0) + _recall_at_k(semantic_ids, case.expected_document_ids, 3) if self.semantic_scorer is not None else None
            semantic_top5 = (semantic_top5 or 0.0) + _recall_at_k(semantic_ids, case.expected_document_ids, 5) if self.semantic_scorer is not None else None
            semantic_mrr = (semantic_mrr or 0.0) + _mrr(semantic_ids, case.expected_document_ids) if self.semantic_scorer is not None else None

            hybrid_top1 = (hybrid_top1 or 0.0) + (1.0 if _recall_at_k(hybrid_ids, case.expected_document_ids, 1) > 0 else 0.0) if self.semantic_scorer is not None else None
            hybrid_top3 = (hybrid_top3 or 0.0) + _recall_at_k(hybrid_ids, case.expected_document_ids, 3) if self.semantic_scorer is not None else None
            hybrid_top5 = (hybrid_top5 or 0.0) + _recall_at_k(hybrid_ids, case.expected_document_ids, 5) if self.semantic_scorer is not None else None
            hybrid_mrr = (hybrid_mrr or 0.0) + _mrr(hybrid_ids, case.expected_document_ids) if self.semantic_scorer is not None else None

            case_results.append(
                SemanticRetrievalCaseResult(
                    case=case,
                    lexical_document_ids=lexical_ids,
                    semantic_document_ids=semantic_ids,
                    hybrid_document_ids=hybrid_ids,
                    lexical_top1_hit=_recall_at_k(lexical_ids, case.expected_document_ids, 1) > 0,
                    lexical_top3_recall=_recall_at_k(lexical_ids, case.expected_document_ids, 3),
                    lexical_top5_recall=_recall_at_k(lexical_ids, case.expected_document_ids, 5),
                    lexical_mrr=_mrr(lexical_ids, case.expected_document_ids),
                    semantic_top1_hit=(semantic_result and _recall_at_k(semantic_ids, case.expected_document_ids, 1) > 0) if self.semantic_scorer is not None else False,
                    semantic_top3_recall=_recall_at_k(semantic_ids, case.expected_document_ids, 3) if self.semantic_scorer is not None else 0.0,
                    semantic_top5_recall=_recall_at_k(semantic_ids, case.expected_document_ids, 5) if self.semantic_scorer is not None else 0.0,
                    semantic_mrr=_mrr(semantic_ids, case.expected_document_ids) if self.semantic_scorer is not None else 0.0,
                    hybrid_top1_hit=_recall_at_k(hybrid_ids, case.expected_document_ids, 1) > 0 if self.semantic_scorer is not None else False,
                    hybrid_top3_recall=_recall_at_k(hybrid_ids, case.expected_document_ids, 3) if self.semantic_scorer is not None else 0.0,
                    hybrid_top5_recall=_recall_at_k(hybrid_ids, case.expected_document_ids, 5) if self.semantic_scorer is not None else 0.0,
                    hybrid_mrr=_mrr(hybrid_ids, case.expected_document_ids) if self.semantic_scorer is not None else 0.0,
                    lexical_latency_ms=lexical_latency,
                    semantic_latency_ms=semantic_latency,
                    hybrid_latency_ms=hybrid_latency,
                    semantic_status=semantic_status,
                )
            )

        case_count = max(len(case_results), 1)
        metrics = SemanticRetrievalMetrics(
            case_count=len(case_results),
            lexical_top1_hit_rate=lexical_top1 / case_count,
            lexical_top3_recall=lexical_top3 / case_count,
            lexical_top5_recall=lexical_top5 / case_count,
            lexical_mrr=lexical_mrr / case_count,
            semantic_top1_hit_rate=(semantic_top1 / case_count) if semantic_top1 is not None else None,
            semantic_top3_recall=(semantic_top3 / case_count) if semantic_top3 is not None else None,
            semantic_top5_recall=(semantic_top5 / case_count) if semantic_top5 is not None else None,
            semantic_mrr=(semantic_mrr / case_count) if semantic_mrr is not None else None,
            hybrid_top1_hit_rate=(hybrid_top1 / case_count) if hybrid_top1 is not None else None,
            hybrid_top3_recall=(hybrid_top3 / case_count) if hybrid_top3 is not None else None,
            hybrid_top5_recall=(hybrid_top5 / case_count) if hybrid_top5 is not None else None,
            hybrid_mrr=(hybrid_mrr / case_count) if hybrid_mrr is not None else None,
            lexical_latency_ms=lexical_latency_total / case_count,
            semantic_latency_ms=(semantic_latency_total / semantic_latency_count) if semantic_latency_count else None,
            hybrid_latency_ms=(hybrid_latency_total / hybrid_latency_count) if hybrid_latency_count else None,
        )
        return SemanticRetrievalEvaluationReport(metrics=metrics, cases=tuple(case_results), semantic_status=semantic_status)

    def _lexical_rank(self, case: SemanticRetrievalCase) -> tuple[tuple[SemanticRetrievalCandidate, ...], float]:
        query = CorpusRetrievalQuery(
            creator_id=case.creator_id,
            query_text=case.query_text,
            project_id=case.project_id,
            document_types=case.document_types,
            authorship_classes=case.authorship_classes,
            languages=case.languages,
            statuses=case.statuses,
            retrieval_eligible_only=case.retrieval_eligible_only,
            current_versions_only=case.current_versions_only,
            limit=case.limit,
            sort=CorpusRetrievalSort.RELEVANCE,
        )
        started = perf_counter()
        result = self.retrieval_service.search(query)
        elapsed = (perf_counter() - started) * 1000.0
        ranked = tuple(
            SemanticRetrievalCandidate(
                document_id=item.document_id,
                version_id=item.version_id,
                creator_id=item.creator_id,
                title=item.title,
                text=item.text,
                match_mode=SemanticMatchMode.LEXICAL,
                lexical_rank=index + 1,
                semantic_rank=None,
                lexical_score=item.relevance_score,
                semantic_score=None,
                fused_score=item.relevance_score,
                relevance_reason=item.relevance_reason,
                provenance_summary=item.provenance_summary,
                document_type=item.document_type,
                authorship_class=item.authorship_class,
                status=item.status,
                project_id=item.project_id,
            )
            for index, item in enumerate(result.results)
        )
        return ranked, elapsed

    def _semantic_rank(self, case: SemanticRetrievalCase, lexical_ranked: tuple[SemanticRetrievalCandidate, ...]) -> tuple[tuple[SemanticRetrievalCandidate, ...], float]:
        pool_query = CorpusRetrievalQuery(
            creator_id=case.creator_id,
            query_text=None,
            project_id=case.project_id,
            document_types=case.document_types,
            authorship_classes=case.authorship_classes,
            languages=case.languages,
            statuses=case.statuses,
            retrieval_eligible_only=case.retrieval_eligible_only,
            current_versions_only=case.current_versions_only,
            limit=max(case.limit, 20),
            sort=CorpusRetrievalSort.UPDATED_DESC,
        )
        pool = self.retrieval_service.search(pool_query).results
        started = perf_counter()
        scores = list(self.semantic_scorer.score(case.query_text, pool))
        elapsed = (perf_counter() - started) * 1000.0
        ranked = sorted(
            zip(pool, scores, strict=False),
            key=lambda item: (
                -float(item[1]),
                0 if item[0].is_current_version else 1,
                -item[0].relevance_score,
                item[0].title.lower(),
                item[0].document_id,
            ),
        )
        return tuple(
            SemanticRetrievalCandidate(
                document_id=item.document_id,
                version_id=item.version_id,
                creator_id=item.creator_id,
                title=item.title,
                text=item.text,
                match_mode=SemanticMatchMode.SEMANTIC,
                lexical_rank=next((index + 1 for index, lexical_item in enumerate(lexical_ranked) if lexical_item.document_id == item.document_id), None),
                semantic_rank=index + 1,
                lexical_score=item.relevance_score,
                semantic_score=float(score),
                fused_score=float(score),
                relevance_reason=f"Semantic score {score:.4f}",
                provenance_summary=item.provenance_summary,
                document_type=item.document_type,
                authorship_class=item.authorship_class,
                status=item.status,
                project_id=item.project_id,
            )
            for index, (item, score) in enumerate(ranked)
        ), elapsed

    def _hybrid_rank(
        self,
        case: SemanticRetrievalCase,
        lexical_ranked: tuple[SemanticRetrievalCandidate, ...],
        semantic_ranked: tuple[SemanticRetrievalCandidate, ...],
    ) -> tuple[tuple[SemanticRetrievalCandidate, ...], float]:
        started = perf_counter()
        lexical_ids = [item.document_id for item in lexical_ranked]
        semantic_ids = [item.document_id for item in semantic_ranked]
        fused_scores = _reciprocal_rank_fusion((lexical_ids, semantic_ids))
        lookup = {item.document_id: item for item in (*lexical_ranked, *semantic_ranked)}
        ranked_ids = sorted(
            fused_scores,
            key=lambda document_id: (
                -fused_scores[document_id],
                0 if lookup[document_id].status == CorpusDocumentStatus.ACTIVE else 1,
                0 if lookup[document_id].project_id == case.project_id and case.project_id else 1,
                lookup[document_id].title.lower(),
                document_id,
            ),
        )
        elapsed = (perf_counter() - started) * 1000.0
        result: list[SemanticRetrievalCandidate] = []
        for index, document_id in enumerate(ranked_ids, start=1):
            lexical_item = next((item for item in lexical_ranked if item.document_id == document_id), None)
            semantic_item = next((item for item in semantic_ranked if item.document_id == document_id), None)
            base = lexical_item or semantic_item
            if base is None:
                continue
            result.append(
                SemanticRetrievalCandidate(
                    document_id=base.document_id,
                    version_id=base.version_id,
                    creator_id=base.creator_id,
                    title=base.title,
                    text=base.text,
                    match_mode=SemanticMatchMode.HYBRID,
                    lexical_rank=lexical_item.lexical_rank if lexical_item else None,
                    semantic_rank=semantic_item.semantic_rank if semantic_item else None,
                    lexical_score=lexical_item.lexical_score if lexical_item else 0.0,
                    semantic_score=semantic_item.semantic_score if semantic_item else None,
                    fused_score=fused_scores[document_id],
                    relevance_reason="Fusión lexical + semántica" if lexical_item and semantic_item else "Fusión híbrida",
                    provenance_summary=base.provenance_summary,
                    document_type=base.document_type,
                    authorship_class=base.authorship_class,
                    status=base.status,
                    project_id=base.project_id,
                )
            )
        return tuple(result), elapsed
