"""Comandos de alto nivel para Strategic Planning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatePlanningContextCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateStrategicPlanCommand:
    creator_id: str
    name: str
    horizon: str
    context_snapshot_id: str


@dataclass(frozen=True, slots=True)
class ReviewStrategicPlanCommand:
    plan_id: str
    decision: str
    reason: str


@dataclass(frozen=True, slots=True)
class CreateStrategicObjectiveCommand:
    plan_id: str
    objective_type: str
    title: str


@dataclass(frozen=True, slots=True)
class IntakeRecommendationCommand:
    plan_id: str
    recommendation_id: str
    intake_status: str = "approved"


@dataclass(frozen=True, slots=True)
class CreateRoadmapItemCommand:
    plan_id: str
    title: str
    item_type: str
