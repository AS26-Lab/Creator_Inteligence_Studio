"""Contratos de persistencia para Creator Language Analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .analysis_types import CreatorLanguageProfileComparison, CreatorLanguageQueryFilters, CreatorLanguageRetrievalResult
from .entities import (
    CreatorLanguageAnalysisRun,
    CreatorLanguageCandidate,
    CreatorLanguageCorpus,
    CreatorLanguageCorpusSource,
    CreatorLanguageMetric,
    CreatorLanguagePattern,
    CreatorLanguagePatternEvidence,
    CreatorLanguageProfileSnapshot,
    CreatorNarrativeProfile,
)


class CreatorLanguageRepository(ABC):
    @abstractmethod
    def upsert_corpus(self, corpus: CreatorLanguageCorpus) -> CreatorLanguageCorpus:
        raise NotImplementedError

    @abstractmethod
    def get_corpus(self, corpus_id: str) -> CreatorLanguageCorpus | None:
        raise NotImplementedError

    @abstractmethod
    def list_corpora(self, creator_id: str) -> list[CreatorLanguageCorpus]:
        raise NotImplementedError

    @abstractmethod
    def get_corpus_by_fingerprint(self, creator_id: str, source_fingerprint: str) -> CreatorLanguageCorpus | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_corpus_source(self, source: CreatorLanguageCorpusSource) -> CreatorLanguageCorpusSource:
        raise NotImplementedError

    @abstractmethod
    def list_corpus_sources(self, corpus_id: str) -> list[CreatorLanguageCorpusSource]:
        raise NotImplementedError

    @abstractmethod
    def get_corpus_source(self, source_id: str) -> CreatorLanguageCorpusSource | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_analysis_run(self, run: CreatorLanguageAnalysisRun) -> CreatorLanguageAnalysisRun:
        raise NotImplementedError

    @abstractmethod
    def get_analysis_run(self, run_id: str) -> CreatorLanguageAnalysisRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_analysis_run_by_fingerprint(self, creator_id: str, source_fingerprint: str, analysis_version: str) -> CreatorLanguageAnalysisRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_analysis_runs(self, creator_id: str, corpus_id: str | None = None) -> list[CreatorLanguageAnalysisRun]:
        raise NotImplementedError

    @abstractmethod
    def upsert_metric(self, metric: CreatorLanguageMetric) -> CreatorLanguageMetric:
        raise NotImplementedError

    @abstractmethod
    def list_metrics(self, run_id: str) -> list[CreatorLanguageMetric]:
        raise NotImplementedError

    @abstractmethod
    def upsert_pattern(self, pattern: CreatorLanguagePattern) -> CreatorLanguagePattern:
        raise NotImplementedError

    @abstractmethod
    def list_patterns(self, creator_id: str, run_id: str | None = None) -> list[CreatorLanguagePattern]:
        raise NotImplementedError

    @abstractmethod
    def get_pattern(self, pattern_id: str) -> CreatorLanguagePattern | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_pattern_evidence(self, evidence: CreatorLanguagePatternEvidence) -> CreatorLanguagePatternEvidence:
        raise NotImplementedError

    @abstractmethod
    def list_pattern_evidence(self, pattern_id: str) -> list[CreatorLanguagePatternEvidence]:
        raise NotImplementedError

    @abstractmethod
    def upsert_narrative_profile(self, profile: CreatorNarrativeProfile) -> CreatorNarrativeProfile:
        raise NotImplementedError

    @abstractmethod
    def get_narrative_profile(self, creator_id: str) -> CreatorNarrativeProfile | None:
        raise NotImplementedError

    @abstractmethod
    def list_narrative_profiles(self, creator_id: str) -> list[CreatorNarrativeProfile]:
        raise NotImplementedError

    @abstractmethod
    def upsert_candidate(self, candidate: CreatorLanguageCandidate) -> CreatorLanguageCandidate:
        raise NotImplementedError

    @abstractmethod
    def list_candidates(self, creator_id: str) -> list[CreatorLanguageCandidate]:
        raise NotImplementedError

    @abstractmethod
    def get_candidate(self, candidate_id: str) -> CreatorLanguageCandidate | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_profile_snapshot(self, snapshot: CreatorLanguageProfileSnapshot) -> CreatorLanguageProfileSnapshot:
        raise NotImplementedError

    @abstractmethod
    def list_profile_snapshots(self, creator_id: str) -> list[CreatorLanguageProfileSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def get_profile_snapshot(self, snapshot_id: str) -> CreatorLanguageProfileSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def compare_profile_snapshots(self, creator_id: str, base_snapshot_id: str, compare_snapshot_id: str) -> CreatorLanguageProfileComparison:
        raise NotImplementedError

    @abstractmethod
    def retrieve_context(self, creator_id: str, filters: CreatorLanguageQueryFilters) -> list[CreatorLanguageRetrievalResult]:
        raise NotImplementedError

