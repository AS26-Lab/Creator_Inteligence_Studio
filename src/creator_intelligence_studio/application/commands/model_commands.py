"""Comandos de aplicacion para modelos personalizados."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidatePersonalizationSnapshotCommand:
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class TrainPersonalizationModelCommand:
    snapshot_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowPersonalizationModelRunCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListPersonalizationModelRunsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class PersonalizationModelMetricsCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class PersonalizationModelPredictionsCommand:
    run_id: str
    split: str | None = None


@dataclass(frozen=True, slots=True)
class ComparePersonalizationModelRunsCommand:
    baseline_run_id: str
    candidate_run_id: str


@dataclass(frozen=True, slots=True)
class ActivatePersonalizationModelCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class DeactivatePersonalizationModelCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class RetirePersonalizationModelCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ActivePersonalizationModelCommand:
    creator_id: str
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyPersonalizationModelCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class DeletePersonalizationModelArtifactCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ScoreCandidateForCreatorCommand:
    creator_id: str
    candidate_id: str


@dataclass(frozen=True, slots=True)
class ScoreVideoForCreatorCommand:
    creator_id: str
    video_id: str


@dataclass(frozen=True, slots=True)
class ExplainPersonalizedScoreCommand:
    creator_id: str
    candidate_id: str
