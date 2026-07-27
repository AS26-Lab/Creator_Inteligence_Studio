"""Contratos de persistencia del modelo de audiencia."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    AudienceAffinity,
    AudienceJourney,
    AudienceJourneyStep,
    AudienceModelRun,
    AudienceProfile,
    AudienceProfileSnapshot,
    AudienceReview,
    AudienceSegment,
    AudienceSegmentDefinition,
    AudienceSegmentEvidence,
    AudienceSignal,
)


class AudienceRepository(ABC):
    @abstractmethod
    def upsert_profile(self, profile: AudienceProfile) -> AudienceProfile:
        raise NotImplementedError

    @abstractmethod
    def get_profile(self, creator_id: str, profile_version: int | None = None) -> AudienceProfile | None:
        raise NotImplementedError

    @abstractmethod
    def list_profiles(self, creator_id: str) -> list[AudienceProfile]:
        raise NotImplementedError

    @abstractmethod
    def upsert_signal(self, signal: AudienceSignal) -> AudienceSignal:
        raise NotImplementedError

    @abstractmethod
    def list_signals(self, creator_id: str, *, platform: str | None = None) -> list[AudienceSignal]:
        raise NotImplementedError

    @abstractmethod
    def get_signal(self, signal_id: str) -> AudienceSignal | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_segment(self, segment: AudienceSegment) -> AudienceSegment:
        raise NotImplementedError

    @abstractmethod
    def list_segments(self, creator_id: str) -> list[AudienceSegment]:
        raise NotImplementedError

    @abstractmethod
    def get_segment(self, segment_id: str) -> AudienceSegment | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_segment_definition(self, definition: AudienceSegmentDefinition) -> AudienceSegmentDefinition:
        raise NotImplementedError

    @abstractmethod
    def list_segment_definitions(self, segment_id: str) -> list[AudienceSegmentDefinition]:
        raise NotImplementedError

    @abstractmethod
    def upsert_segment_evidence(self, evidence: AudienceSegmentEvidence) -> AudienceSegmentEvidence:
        raise NotImplementedError

    @abstractmethod
    def list_segment_evidence(self, segment_id: str) -> list[AudienceSegmentEvidence]:
        raise NotImplementedError

    @abstractmethod
    def upsert_affinity(self, affinity: AudienceAffinity) -> AudienceAffinity:
        raise NotImplementedError

    @abstractmethod
    def list_affinities(self, creator_id: str) -> list[AudienceAffinity]:
        raise NotImplementedError

    @abstractmethod
    def get_affinity(self, affinity_id: str) -> AudienceAffinity | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_journey(self, journey: AudienceJourney) -> AudienceJourney:
        raise NotImplementedError

    @abstractmethod
    def list_journeys(self, creator_id: str) -> list[AudienceJourney]:
        raise NotImplementedError

    @abstractmethod
    def get_journey(self, journey_id: str) -> AudienceJourney | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_journey_step(self, step: AudienceJourneyStep) -> AudienceJourneyStep:
        raise NotImplementedError

    @abstractmethod
    def list_journey_steps(self, journey_id: str) -> list[AudienceJourneyStep]:
        raise NotImplementedError

    @abstractmethod
    def upsert_profile_snapshot(self, snapshot: AudienceProfileSnapshot) -> AudienceProfileSnapshot:
        raise NotImplementedError

    @abstractmethod
    def list_profile_snapshots(self, creator_id: str) -> list[AudienceProfileSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def upsert_review(self, review: AudienceReview) -> AudienceReview:
        raise NotImplementedError

    @abstractmethod
    def list_reviews(self, creator_id: str, *, target_type: str | None = None) -> list[AudienceReview]:
        raise NotImplementedError

    @abstractmethod
    def upsert_run(self, run: AudienceModelRun) -> AudienceModelRun:
        raise NotImplementedError

    @abstractmethod
    def get_run_by_fingerprint(self, creator_id: str, source_fingerprint: str, configuration_json: str) -> AudienceModelRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_run(self, run_id: str) -> AudienceModelRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_runs(self, creator_id: str) -> list[AudienceModelRun]:
        raise NotImplementedError

