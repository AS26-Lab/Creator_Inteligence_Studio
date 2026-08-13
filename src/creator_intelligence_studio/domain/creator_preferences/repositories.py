"""Persistence contracts for creator preferences."""

from __future__ import annotations

from typing import Protocol

from .entities import (
    CreatorConfirmedPreference,
    CreatorPreferenceCandidate,
    CreatorPreferenceCandidateEvidence,
)


class CreatorPreferenceRepository(Protocol):
    def upsert_candidate(self, candidate: CreatorPreferenceCandidate) -> CreatorPreferenceCandidate: ...

    def get_candidate_by_id(self, candidate_id: str) -> CreatorPreferenceCandidate | None: ...

    def get_candidate_by_key(self, candidate_key: str) -> CreatorPreferenceCandidate | None: ...

    def list_candidates(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
        preference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorPreferenceCandidate]: ...

    def upsert_candidate_evidence(self, evidence: CreatorPreferenceCandidateEvidence) -> CreatorPreferenceCandidateEvidence: ...

    def list_candidate_evidence(self, candidate_id: str) -> list[CreatorPreferenceCandidateEvidence]: ...

    def upsert_confirmed_preference(self, preference: CreatorConfirmedPreference) -> CreatorConfirmedPreference: ...

    def get_confirmed_preference_by_id(self, preference_id: str) -> CreatorConfirmedPreference | None: ...

    def get_confirmed_preference_by_key(self, preference_key: str) -> CreatorConfirmedPreference | None: ...

    def list_confirmed_preferences(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        active: bool | None = None,
        preference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorConfirmedPreference]: ...

    def deactivate_confirmed_preference(self, preference_id: str) -> CreatorConfirmedPreference | None: ...

    def reactivate_confirmed_preference(self, preference_id: str) -> CreatorConfirmedPreference | None: ...
