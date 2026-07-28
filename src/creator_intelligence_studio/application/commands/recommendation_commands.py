"""Comandos de aplicacion para Opportunity and Recommendation Engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListRecommendationRequestsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateRecommendationRequestCommand:
    creator_id: str
    request_type: str
    objective_type: str | None
    platform_scope_json: str
    content_type_scope_json: str
    market_id: str | None
    topic_id: str | None
    time_horizon: str | None
    constraints_json: str
    preferences_json: str


@dataclass(frozen=True, slots=True)
class ShowRecommendationRequestCommand:
    request_id: str


@dataclass(frozen=True, slots=True)
class GenerateRecommendationsCommand:
    request_id: str | None = None
    creator_id: str | None = None
    request_type: str | None = None
    objective_type: str | None = None


@dataclass(frozen=True, slots=True)
class ShowRecommendationRunCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListRecommendationsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowRecommendationCommand:
    recommendation_id: str


@dataclass(frozen=True, slots=True)
class ReviewRecommendationCommand:
    recommendation_id: str
    decision: str
    reason: str
    reviewer: str | None = None


@dataclass(frozen=True, slots=True)
class RecordRecommendationFeedbackCommand:
    recommendation_id: str
    feedback_type: str
    rating: int | None = None
    feedback_text: str | None = None
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class ConvertRecommendationToExperimentCommand:
    recommendation_id: str


@dataclass(frozen=True, slots=True)
class MarkRecommendationExecutedCommand:
    recommendation_id: str
    content_id: str


@dataclass(frozen=True, slots=True)
class AddRecommendationOutcomeCommand:
    recommendation_id: str
    file_path: str

