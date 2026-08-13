"""Persistence contracts for creator feedback."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import CreatorFeedbackEvent, CreatorLearningSignal, CreatorLearningSignalEvidence


class CreatorFeedbackRepository(ABC):
    @abstractmethod
    def upsert_feedback_event(self, event: CreatorFeedbackEvent) -> CreatorFeedbackEvent:
        raise NotImplementedError

    @abstractmethod
    def get_feedback_event_by_id(self, event_id: str) -> CreatorFeedbackEvent | None:
        raise NotImplementedError

    @abstractmethod
    def get_feedback_event_by_dedupe_key(self, dedupe_key: str) -> CreatorFeedbackEvent | None:
        raise NotImplementedError

    @abstractmethod
    def list_feedback_events(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorFeedbackEvent]:
        raise NotImplementedError

    @abstractmethod
    def upsert_learning_signal(self, signal: CreatorLearningSignal) -> CreatorLearningSignal:
        raise NotImplementedError

    @abstractmethod
    def get_learning_signal_by_id(self, signal_id: str) -> CreatorLearningSignal | None:
        raise NotImplementedError

    @abstractmethod
    def get_learning_signal_by_key(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        workflow_type: str | None,
        scope: str,
        signal_type: str,
        signal_value: str,
        polarity: str,
    ) -> CreatorLearningSignal | None:
        raise NotImplementedError

    @abstractmethod
    def list_learning_signals(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
        signal_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorLearningSignal]:
        raise NotImplementedError

    @abstractmethod
    def upsert_learning_signal_evidence(self, evidence: CreatorLearningSignalEvidence) -> CreatorLearningSignalEvidence:
        raise NotImplementedError

    @abstractmethod
    def list_learning_signal_evidence(self, signal_id: str) -> list[CreatorLearningSignalEvidence]:
        raise NotImplementedError

    @abstractmethod
    def delete_learning_signals_for_creator(self, creator_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_learning_signal_evidence_for_creator(self, creator_id: str) -> None:
        raise NotImplementedError

