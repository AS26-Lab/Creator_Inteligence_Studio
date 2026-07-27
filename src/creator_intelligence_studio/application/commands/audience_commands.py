"""Comandos de aplicacion para Audience Model Foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuildAudienceProfileCommand:
    creator_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ListAudienceSignalsCommand:
    creator_id: str
    platform: str | None = None


@dataclass(frozen=True, slots=True)
class ShowAudienceSignalCommand:
    signal_id: str


@dataclass(frozen=True, slots=True)
class ListAudienceSegmentsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateAudienceSegmentCommand:
    creator_id: str
    name: str
    segment_type: str
    scope: str
    description: str
    platform: str | None = None
    content_type: str | None = None
    topic: str | None = None
    lifecycle_stage: str | None = None


@dataclass(frozen=True, slots=True)
class ShowAudienceSegmentCommand:
    segment_id: str


@dataclass(frozen=True, slots=True)
class ReviewAudienceSegmentCommand:
    segment_id: str
    decision: str
    reason: str
    previous_value_json: str | None = None
    new_value_json: str | None = None


@dataclass(frozen=True, slots=True)
class ArchiveAudienceSegmentCommand:
    segment_id: str


@dataclass(frozen=True, slots=True)
class ListAudienceAffinitiesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowAudienceAffinityCommand:
    affinity_id: str


@dataclass(frozen=True, slots=True)
class ListAudienceJourneysCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowAudienceJourneyCommand:
    journey_id: str


@dataclass(frozen=True, slots=True)
class ReviewAudienceJourneyCommand:
    journey_id: str
    decision: str
    reason: str
    previous_value_json: str | None = None
    new_value_json: str | None = None


@dataclass(frozen=True, slots=True)
class ListAudiencePlatformRolesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListAudienceContentRolesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListAudienceProfileHistoryCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CompareAudienceProfileCommand:
    creator_id: str
    base_version: int
    compare_version: int


@dataclass(frozen=True, slots=True)
class ExportAudienceCommand:
    creator_id: str
    format: str

