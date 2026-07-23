"""Servicio de aplicacion para datasets de personalizacion por creador."""

from __future__ import annotations

import csv
import io
import json
import logging
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.clip_ranking_service import ClipRankingReport, ClipRankingService
from creator_intelligence_studio.domain.clip_ranking.entities import ClipCollectionItem, ClipRankingRun, ClipReviewEvent, RankedClipCandidate
from creator_intelligence_studio.domain.errors import NotFoundError
from creator_intelligence_studio.domain.personalization_data.entities import (
    CreatorDatasetConflict,
    CreatorDatasetExample,
    CreatorDatasetQualityReport,
    CreatorDatasetSnapshot,
    CreatorFeatureSchema,
)
from creator_intelligence_studio.domain.personalization_data.errors import PersonalizationDataStateError, PersonalizationDataValidationError
from creator_intelligence_studio.domain.personalization_data.repositories import PersonalizationDataRepository
from creator_intelligence_studio.domain.personalization_data.services import (
    build_personalization_configuration_fingerprint,
    build_personalization_source_fingerprint,
    is_personalization_dataset_stale,
)
from creator_intelligence_studio.domain.personalization_data.value_objects import (
    PersonalizationDatasetOptions,
    PersonalizationDatasetStatus,
    PersonalizationLabel,
    PersonalizationReadinessStatus,
    PersonalizationSplitName,
)
from creator_intelligence_studio.domain.projects.entities import Project
from creator_intelligence_studio.domain.creators.entities import Creator
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.personalization_data.dataset_snapshot_builder import (
    build_snapshot_group_key,
    build_snapshot_name,
    build_snapshot_version,
)
from creator_intelligence_studio.infrastructure.personalization_data.exporter import (
    export_dataset_csv,
    export_dataset_json,
    export_dataset_jsonl,
    write_export,
)
from creator_intelligence_studio.infrastructure.personalization_data.feature_extractor import (
    CREATOR_FEATURE_SCHEMA_VERSION,
    build_feature_schema_entity,
    extract_dataset_features,
)
from creator_intelligence_studio.infrastructure.personalization_data.label_builder import build_dataset_label
from creator_intelligence_studio.infrastructure.personalization_data.quality_analyzer import analyze_dataset_quality
from creator_intelligence_studio.infrastructure.personalization_data.readiness_evaluator import evaluate_dataset_readiness
from creator_intelligence_studio.infrastructure.personalization_data.split_strategy import assign_dataset_splits
from creator_intelligence_studio.shared.dates import to_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_default(value):
    if isinstance(value, (datetime,)):
        return to_iso_z(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


def _overlap_ratio(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    overlap_start = max(left_start, right_start)
    overlap_end = min(left_end, right_end)
    if overlap_end <= overlap_start:
        return 0.0
    left_span = max(left_end - left_start, 1e-9)
    right_span = max(right_end - right_start, 1e-9)
    return (overlap_end - overlap_start) / max(left_span, right_span)


def _build_source_payload(
    *,
    creator: Creator,
    project: Project | None,
    options: PersonalizationDatasetOptions,
    assembled: _AssembledDataset,
) -> dict[str, object]:
    return {
        "creator_id": creator.id,
        "project_id": project.id if project else None,
        "options": options.to_dict(),
        "videos": sorted(assembled.source_video_ids),
        "examples": [
            {
                "video_asset_id": example.video_asset_id,
                "ranking_run_id": example.ranking_run_id,
                "ranked_clip_candidate_id": example.ranked_clip_candidate_id,
                "multimodal_candidate_id": example.multimodal_candidate_id,
                "group_key": example.group_key,
                "label": example.label.value,
                "split": example.split_name.value,
                "feature_hash": json.dumps(example.feature_vector, sort_keys=True, ensure_ascii=False, default=str),
                "quality_flags": example.quality_flags,
            }
            for example in sorted(
                assembled.examples,
                key=lambda item: (
                    item.video_asset_id,
                    item.start_seconds,
                    item.end_seconds,
                    item.ranked_clip_candidate_id or "",
                    item.multimodal_candidate_id or "",
                    item.label.value,
                    item.split_name.value,
                ),
            )
        ],
        "conflicts": [
            {
                "type": conflict.conflict_type,
                "candidate_a_id": conflict.candidate_a_id,
                "candidate_b_id": conflict.candidate_b_id,
                "description": conflict.description,
                "evidence": conflict.evidence_json,
            }
            for conflict in sorted(assembled.conflicts, key=lambda item: (item.created_at, item.id))
        ],
    }


@dataclass(frozen=True, slots=True)
class PersonalizationDatasetReport:
    creator: Creator
    project: Project | None
    snapshot: CreatorDatasetSnapshot | None
    feature_schema: CreatorFeatureSchema
    examples: tuple[CreatorDatasetExample, ...]
    conflicts: tuple[CreatorDatasetConflict, ...]
    quality_report: CreatorDatasetQualityReport | None
    status: PersonalizationDatasetStatus
    is_stale: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "creator": self.creator.to_dict(),
            "project": self.project.to_dict() if self.project else None,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "feature_schema": self.feature_schema.to_dict(),
            "examples": [example.to_dict() for example in self.examples],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
            "quality_report": self.quality_report.to_dict() if self.quality_report else None,
            "status": self.status.value,
            "is_stale": self.is_stale,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class CreatorReadinessReport:
    creator: Creator
    latest_snapshot: CreatorDatasetSnapshot | None
    readiness_status: PersonalizationReadinessStatus
    readiness_score: float
    recommendations: tuple[str, ...]
    snapshot_count: int
    is_stale: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "creator": self.creator.to_dict(),
            "latest_snapshot": self.latest_snapshot.to_dict() if self.latest_snapshot else None,
            "readiness_status": self.readiness_status.value,
            "readiness_score": self.readiness_score,
            "recommendations": list(self.recommendations),
            "snapshot_count": self.snapshot_count,
            "is_stale": self.is_stale,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class DatasetSnapshotComparison:
    snapshot_a: CreatorDatasetSnapshot
    snapshot_b: CreatorDatasetSnapshot
    example_count_delta: int
    positive_count_delta: int
    negative_count_delta: int
    neutral_count_delta: int
    excluded_count_delta: int
    conflict_count_delta: int
    readiness_score_delta: float
    source_fingerprint_changed: bool
    configuration_fingerprint_changed: bool
    status_changed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot_a": self.snapshot_a.to_dict(),
            "snapshot_b": self.snapshot_b.to_dict(),
            "example_count_delta": self.example_count_delta,
            "positive_count_delta": self.positive_count_delta,
            "negative_count_delta": self.negative_count_delta,
            "neutral_count_delta": self.neutral_count_delta,
            "excluded_count_delta": self.excluded_count_delta,
            "conflict_count_delta": self.conflict_count_delta,
            "readiness_score_delta": self.readiness_score_delta,
            "source_fingerprint_changed": self.source_fingerprint_changed,
            "configuration_fingerprint_changed": self.configuration_fingerprint_changed,
            "status_changed": self.status_changed,
        }


@dataclass(frozen=True, slots=True)
class PersonalizationDatasetExportResult:
    snapshot: CreatorDatasetSnapshot
    format: str
    content: str
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "format": self.format,
            "content": self.content,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class _AssembledDataset:
    creator: Creator
    project: Project | None
    videos: tuple
    ranking_reports: tuple[ClipRankingReport, ...]
    examples: list[CreatorDatasetExample]
    conflicts: list[CreatorDatasetConflict]
    warnings: list[str]
    errors: list[str]
    total_duration_seconds: float
    source_video_ids: list[str]


class PersonalizationDatasetService:
    """Orquesta la preparacion de datasets de personalizacion."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        clip_service: ClipRankingService,
        personalization_repository: PersonalizationDataRepository,
        logger: logging.Logger | None = None,
        options: PersonalizationDatasetOptions | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.clip_service = clip_service
        self.personalization_repository = personalization_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.personalization")
        self.options = options or PersonalizationDatasetOptions()

    def _clip_repository(self):
        repository = getattr(self.clip_service, "clip_repository", None)
        if repository is None:
            raise PersonalizationDataStateError("El repositorio de clips no esta disponible.")
        return repository

    def _progress(self, progress_callback, phase: str, ratio: float) -> None:
        if progress_callback is not None:
            progress_callback(phase, max(0.0, min(1.0, ratio)))

    def _require_creator(self, creator_id: str) -> Creator:
        creator = self.catalog_service.get_creator(creator_id)
        if creator is None:
            raise NotFoundError("El creador solicitado no existe.")
        return creator

    def _require_project(self, project_id: str) -> Project:
        project = self.catalog_service.get_project(project_id)
        if project is None:
            raise NotFoundError("El proyecto solicitado no existe.")
        return project

    def _videos_for_scope(self, creator_id: str, project_id: str | None) -> tuple[Project | None, list]:
        if project_id is not None:
            project = self._require_project(project_id)
            if project.creator_id != creator_id:
                raise PersonalizationDataValidationError("El proyecto no pertenece al creador solicitado.")
            return project, list(self.catalog_service.list_videos(project.id))
        projects = self.catalog_service.list_projects(creator_id)
        videos = []
        for project in projects:
            videos.extend(self.catalog_service.list_videos(project.id))
        return None, videos

    def _collect_feedback_objects(self, video_id: str):
        clip_repository = self._clip_repository()
        ranking_report = self.clip_service.get_ranking_run(video_id)
        if ranking_report.run is None:
            return ranking_report, [], []
        collection_items: list[ClipCollectionItem] = []
        collections = clip_repository.list_collections(video_id)
        for collection in collections:
            collection_items.extend(clip_repository.list_collection_items(collection.id))
        return ranking_report, collections, collection_items

    def _build_assembled_dataset(
        self,
        creator: Creator,
        project: Project | None,
        videos: list,
        *,
        progress_callback=None,
    ) -> _AssembledDataset:
        self._progress(progress_callback, "Cargando feedback", 0.05)
        examples: list[CreatorDatasetExample] = []
        conflicts: list[CreatorDatasetConflict] = []
        warnings: list[str] = []
        errors: list[str] = []
        ranking_reports: list[ClipRankingReport] = []
        source_video_ids: list[str] = []
        total_duration_seconds = 0.0
        clip_repository = self._clip_repository()

        for index, video in enumerate(videos):
            ranking_report = self.clip_service.get_ranking_run(video.id)
            ranking_reports.append(ranking_report)
            source_video_ids.append(video.id)
            if ranking_report.run is None or ranking_report.multimodal_report is None or ranking_report.multimodal_report.analysis is None:
                warnings.append(f"Video {video.id} sin ranking multimodal utilizable.")
                continue
            multimodal_report = ranking_report.multimodal_report
            analysis = multimodal_report.analysis
            total_duration_seconds += float(analysis.duration_seconds)
            collections = clip_repository.list_collections(video.id)
            collection_items: list[ClipCollectionItem] = []
            for collection in collections:
                collection_items.extend(clip_repository.list_collection_items(collection.id))
            transcription = multimodal_report.transcription
            if transcription is not None:
                transcription = self.clip_service.transcription_repository.get_by_id(transcription.id) or transcription
                transcription_segments = self.clip_service.transcription_repository.list_segments(transcription.id)
            else:
                transcription_segments = []
            candidate_map = {candidate.id: candidate for candidate in multimodal_report.candidates}
            ranked_candidates = list(ranking_report.candidates)
            for candidate in ranked_candidates:
                multimodal_candidate = candidate_map.get(candidate.multimodal_candidate_id)
                review_events = clip_repository.list_review_events(candidate.id)
                candidate_collection_items = [item for item in collection_items if item.ranked_clip_candidate_id == candidate.id]
                nearby_candidate_count = sum(
                    1
                    for other in ranked_candidates
                    if other.id != candidate.id and _overlap_ratio(candidate.adjusted_start_seconds, candidate.adjusted_end_seconds, other.adjusted_start_seconds, other.adjusted_end_seconds) > 0.0
                )
                decision = build_dataset_label(
                    ranked_candidate=candidate,
                    review_events=review_events,
                    collection_items=candidate_collection_items,
                    options=self.options,
                )
                feature_bundle = extract_dataset_features(
                    video_duration_seconds=float(analysis.duration_seconds),
                    profile=ranking_report.run.ranker_version if ranking_report.run else self.options.dataset_version_prefix,
                    multimodal_analysis=analysis,
                    multimodal_windows=list(multimodal_report.windows),
                    multimodal_candidate=multimodal_candidate,
                    ranking_run=ranking_report.run,
                    ranked_candidate=candidate,
                    transcription=transcription,
                    transcription_segments=transcription_segments,
                    acoustic_analysis=multimodal_report.acoustic_analysis,
                    visual_analysis=multimodal_report.visual_analysis,
                    nearby_candidate_count=nearby_candidate_count,
                    collections_count=len(collections),
                    review_event_count=len(review_events),
                    conflict_count=len(decision.conflict_entries),
                )
                quality_flags = dict(feature_bundle.quality_flags)
                quality_flags.update(decision.quality_flags)
                if ranking_report.is_stale:
                    quality_flags["stale_source"] = True
                if ranking_report.missing_sources:
                    quality_flags["missing_sources"] = list(ranking_report.missing_sources)
                if review_events:
                    quality_flags["review_history_present"] = True
                if multimodal_report.missing_sources:
                    quality_flags["multimodal_missing_sources"] = list(multimodal_report.missing_sources)
                example = CreatorDatasetExample(
                    id=str(uuid4()),
                    snapshot_id="",
                    creator_id=creator.id,
                    video_asset_id=video.id,
                    ranking_run_id=ranking_report.run.id if ranking_report.run else None,
                    ranked_clip_candidate_id=candidate.id,
                    multimodal_candidate_id=candidate.multimodal_candidate_id,
                    group_key=build_snapshot_group_key(video.id, ranking_report.run.id if ranking_report.run else None),
                    start_seconds=candidate.adjusted_start_seconds,
                    end_seconds=candidate.adjusted_end_seconds,
                    duration_seconds=candidate.duration_seconds,
                    label=decision.label,
                    label_source=decision.label_source,
                    label_confidence=decision.confidence,
                    human_review_status=candidate.review_status.value,
                    human_rating=candidate.user_rating,
                    human_tags=candidate.tags,
                    feature_vector=feature_bundle.feature_vector,
                    feature_schema_version=CREATOR_FEATURE_SCHEMA_VERSION,
                    quality_flags=quality_flags,
                    exclusion_reason=str(quality_flags.get("review_status")) if decision.label == PersonalizationLabel.EXCLUDED else None,
                    split_name=PersonalizationSplitName.EXCLUDED if decision.label == PersonalizationLabel.EXCLUDED else PersonalizationSplitName.TRAIN,
                    sample_weight=self._sample_weight(decision.label, decision.confidence, quality_flags),
                    created_at=utc_now(),
                )
                examples.append(example)
                for entry_index, entry in enumerate(decision.conflict_entries):
                    conflicts.append(
                        CreatorDatasetConflict(
                            id=str(uuid4()),
                            snapshot_id="",
                            creator_id=creator.id,
                            conflict_type=entry["type"],
                            candidate_a_id=candidate.id,
                            candidate_b_id=None,
                            description=entry["description"],
                            evidence_json=entry["evidence"],
                            resolution_status="open",
                            created_at=utc_now(),
                            resolved_at=None,
                        )
                    )
            self._progress(progress_callback, "Extrayendo features", 0.2 + (0.3 * (index + 1) / max(1, len(videos))))
        self._progress(progress_callback, "Detectando conflictos", 0.55)
        self._add_pairwise_conflicts(examples, conflicts)
        self._progress(progress_callback, "Agrupando ejemplos", 0.65)
        split_assignments = assign_dataset_splits([example for example in examples if example.label != PersonalizationLabel.EXCLUDED], options=self.options)
        examples = [replace(example, split_name=split_assignments.get(example.id, example.split_name)) for example in examples]
        self._progress(progress_callback, "Generando splits", 0.72)
        return _AssembledDataset(
            creator=creator,
            project=project,
            videos=tuple(videos),
            ranking_reports=tuple(ranking_reports),
            examples=examples,
            conflicts=conflicts,
            warnings=warnings,
            errors=errors,
            total_duration_seconds=total_duration_seconds,
            source_video_ids=source_video_ids,
        )

    def _add_pairwise_conflicts(self, examples: list[CreatorDatasetExample], conflicts: list[CreatorDatasetConflict]) -> None:
        seen_pairs: set[tuple[str, str]] = set()
        for index, left in enumerate(examples):
            if left.label == PersonalizationLabel.EXCLUDED:
                continue
            for right in examples[index + 1 :]:
                if left.video_asset_id != right.video_asset_id:
                    continue
                if {left.label, right.label} != {PersonalizationLabel.POSITIVE, PersonalizationLabel.NEGATIVE}:
                    continue
                iou = _overlap_ratio(left.start_seconds, left.end_seconds, right.start_seconds, right.end_seconds)
                if iou < self.options.max_overlap_ratio:
                    continue
                pair = tuple(sorted((left.id, right.id)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                conflicts.append(
                    CreatorDatasetConflict(
                        id=str(uuid4()),
                        snapshot_id="",
                        creator_id=left.creator_id,
                        conflict_type="duplicate_label_conflict",
                        candidate_a_id=left.ranked_clip_candidate_id,
                        candidate_b_id=right.ranked_clip_candidate_id,
                        description="Candidatos casi identicos con labels opuestas.",
                        evidence_json={
                            "iou": iou,
                            "left_label": left.label.value,
                            "right_label": right.label.value,
                            "left_bounds": [left.start_seconds, left.end_seconds],
                            "right_bounds": [right.start_seconds, right.end_seconds],
                        },
                        resolution_status="open",
                        created_at=utc_now(),
                        resolved_at=None,
                    )
                )
                for example_id in (left.id, right.id):
                    for position, example in enumerate(examples):
                        if example.id == example_id:
                            quality_flags = dict(example.quality_flags)
                            quality_flags["pairwise_conflict"] = True
                            examples[position] = replace(example, quality_flags=quality_flags)

    def _sample_weight(self, label: PersonalizationLabel, confidence: float, quality_flags: dict[str, object]) -> float:
        weight = 1.0
        if label == PersonalizationLabel.EXCLUDED:
            weight = 0.0
        elif label == PersonalizationLabel.NEUTRAL_OR_UNCERTAIN:
            weight = 0.5
        else:
            weight = 0.9 + (confidence * 0.3)
        if quality_flags.get("is_conflicted"):
            weight *= 0.5
        if quality_flags.get("stale_source"):
            weight *= 0.7
        missing_feature_count = int(quality_flags.get("missing_feature_count", 0))
        feature_count = int(quality_flags.get("feature_count", max(missing_feature_count, 1)))
        missing_ratio = missing_feature_count / max(1, feature_count)
        weight *= max(0.25, 1.0 - missing_ratio)
        return round(max(0.05, min(2.0, weight)), 4)

    def _snapshot_from_assembly(
        self,
        *,
        snapshot_id: str,
        creator: Creator,
        project: Project | None,
        assembled: _AssembledDataset,
        source_fingerprint: str,
        configuration_fingerprint: str,
        snapshot_version: str,
        quality_report: CreatorDatasetQualityReport,
        readiness_status: PersonalizationReadinessStatus,
        warnings: list[str],
        errors: list[str],
        status: PersonalizationDatasetStatus,
    ) -> CreatorDatasetSnapshot:
        example_count = len(assembled.examples)
        counts = Counter(example.label.value for example in assembled.examples)
        split_counts = Counter(example.split_name.value for example in assembled.examples)
        now = utc_now()
        return CreatorDatasetSnapshot(
            id=snapshot_id,
            creator_id=creator.id,
            project_id=project.id if project else None,
            name=build_snapshot_name(creator.id, project.id if project else None),
            status=status,
            dataset_version=snapshot_version,
            feature_schema_version=self.options.feature_schema_version,
            label_schema_version=self.options.label_schema_version,
            source_fingerprint=source_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            example_count=example_count,
            positive_count=counts.get(PersonalizationLabel.POSITIVE.value, 0),
            negative_count=counts.get(PersonalizationLabel.NEGATIVE.value, 0),
            neutral_count=counts.get(PersonalizationLabel.NEUTRAL_OR_UNCERTAIN.value, 0),
            excluded_count=counts.get(PersonalizationLabel.EXCLUDED.value, 0),
            conflict_count=len(assembled.conflicts),
            train_count=split_counts.get(PersonalizationSplitName.TRAIN.value, 0),
            validation_count=split_counts.get(PersonalizationSplitName.VALIDATION.value, 0),
            test_count=split_counts.get(PersonalizationSplitName.TEST.value, 0),
            readiness_status=readiness_status,
            readiness_score=quality_report.readiness_score,
            started_at=now,
            completed_at=now,
            warning_code="dataset_warnings" if warnings else None,
            warning_message="; ".join(warnings) if warnings else None,
            error_code="dataset_errors" if errors else None,
            error_message="; ".join(errors) if errors else None,
            created_at=now,
            updated_at=now,
        )

    def _report_from_snapshot(self, snapshot_id: str) -> PersonalizationDatasetReport:
        snapshot = self.personalization_repository.get_snapshot_by_id(snapshot_id)
        if snapshot is None:
            raise NotFoundError("El snapshot solicitado no existe.")
        creator = self._require_creator(snapshot.creator_id)
        project = self._require_project(snapshot.project_id) if snapshot.project_id else None
        feature_schema = self.personalization_repository.get_feature_schema(snapshot.feature_schema_version) or build_feature_schema_entity()
        examples = tuple(self.personalization_repository.list_examples_by_snapshot_id(snapshot.id))
        conflicts = tuple(self.personalization_repository.list_conflicts_by_snapshot_id(snapshot.id))
        quality_report = self.personalization_repository.get_quality_report_by_snapshot_id(snapshot.id)
        return PersonalizationDatasetReport(
            creator=creator,
            project=project,
            snapshot=snapshot,
            feature_schema=feature_schema,
            examples=examples,
            conflicts=conflicts,
            quality_report=quality_report,
            status=snapshot.status,
            is_stale=self.is_dataset_stale(snapshot.id),
            warnings=(snapshot.warning_message,) if snapshot.warning_message else (),
            errors=(snapshot.error_message,) if snapshot.error_message else (),
        )

    def build_creator_dataset(self, creator_id: str, project_id: str | None = None, force: bool = False, *, progress_callback=None) -> PersonalizationDatasetReport:
        creator = self._require_creator(creator_id)
        project, videos = self._videos_for_scope(creator.id, project_id)
        assembled = self._build_assembled_dataset(creator, project, videos, progress_callback=progress_callback)
        feature_schema = self.personalization_repository.get_feature_schema(self.options.feature_schema_version) or build_feature_schema_entity()
        configuration_fingerprint = build_personalization_configuration_fingerprint(self.options)
        source_fingerprint = build_personalization_source_fingerprint(
            _build_source_payload(creator=creator, project=project, options=self.options, assembled=assembled)
        )
        latest = self.personalization_repository.get_latest_snapshot_by_creator_id(creator.id)
        if latest is not None and not force and not is_personalization_dataset_stale(
            latest,
            source_fingerprint=source_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
        ):
            return self._report_from_snapshot(latest.id)
        split_counts = Counter(example.split_name.value for example in assembled.examples)
        quality_stats = analyze_dataset_quality(
            snapshot=CreatorDatasetSnapshot(
                id=str(uuid4()),
                creator_id=creator.id,
                project_id=project.id if project else None,
                name=build_snapshot_name(creator.id, project.id if project else None),
                status=PersonalizationDatasetStatus.BUILDING,
                dataset_version=build_snapshot_version(latest.dataset_version if latest else None, self.options),
                feature_schema_version=self.options.feature_schema_version,
                label_schema_version=self.options.label_schema_version,
                source_fingerprint=source_fingerprint,
                configuration_fingerprint=configuration_fingerprint,
                example_count=len(assembled.examples),
                positive_count=sum(1 for example in assembled.examples if example.label == PersonalizationLabel.POSITIVE),
                negative_count=sum(1 for example in assembled.examples if example.label == PersonalizationLabel.NEGATIVE),
                neutral_count=sum(1 for example in assembled.examples if example.label == PersonalizationLabel.NEUTRAL_OR_UNCERTAIN),
                excluded_count=sum(1 for example in assembled.examples if example.label == PersonalizationLabel.EXCLUDED),
                conflict_count=len(assembled.conflicts),
                train_count=split_counts.get(PersonalizationSplitName.TRAIN.value, 0),
                validation_count=split_counts.get(PersonalizationSplitName.VALIDATION.value, 0),
                test_count=split_counts.get(PersonalizationSplitName.TEST.value, 0),
                readiness_status=PersonalizationReadinessStatus.NOT_READY,
                readiness_score=0.0,
                started_at=utc_now(),
                completed_at=utc_now(),
                warning_code=None,
                warning_message=None,
                error_code=None,
                error_message=None,
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            examples=assembled.examples,
            conflicts=assembled.conflicts,
            total_videos=len(videos),
            total_duration_seconds=assembled.total_duration_seconds,
        )
        readiness = evaluate_dataset_readiness(quality_stats)
        snapshot_status = (
            PersonalizationDatasetStatus.COMPLETED_WITH_WARNINGS
            if assembled.warnings or assembled.errors or readiness.readiness_status in {PersonalizationReadinessStatus.BLOCKED_BY_CONFLICTS, PersonalizationReadinessStatus.BLOCKED_BY_QUALITY}
            else PersonalizationDatasetStatus.COMPLETED
        )
        snapshot = self._snapshot_from_assembly(
            snapshot_id=str(uuid4()),
            creator=creator,
            project=project,
            assembled=assembled,
            source_fingerprint=source_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            snapshot_version=build_snapshot_version(latest.dataset_version if latest else None, self.options),
            quality_report=CreatorDatasetQualityReport(
                id=str(uuid4()),
                snapshot_id="",
                report_version=self.options.dataset_version_prefix,
                duplicate_ratio=quality_stats.duplicate_ratio,
                overlap_ratio=quality_stats.overlap_ratio,
                missing_feature_ratio=quality_stats.missing_feature_ratio,
                class_balance_score=quality_stats.class_balance_score,
                creator_coverage_score=quality_stats.creator_coverage_score,
                temporal_coverage_score=quality_stats.temporal_coverage_score,
                source_diversity_score=quality_stats.source_diversity_score,
                label_consistency_score=quality_stats.label_consistency_score,
                leakage_risk_score=quality_stats.leakage_risk_score,
                readiness_score=quality_stats.readiness_score,
                readiness_status=quality_stats.readiness_status,
                recommendations=quality_stats.recommendations,
                created_at=utc_now(),
            ),
            readiness_status=readiness.readiness_status,
            warnings=assembled.warnings + list(readiness.recommendations),
            errors=assembled.errors,
            status=snapshot_status,
        )
        quality_report = CreatorDatasetQualityReport(
            id=str(uuid4()),
            snapshot_id=snapshot.id,
            report_version=self.options.dataset_version_prefix,
            duplicate_ratio=quality_stats.duplicate_ratio,
            overlap_ratio=quality_stats.overlap_ratio,
            missing_feature_ratio=quality_stats.missing_feature_ratio,
            class_balance_score=quality_stats.class_balance_score,
            creator_coverage_score=quality_stats.creator_coverage_score,
            temporal_coverage_score=quality_stats.temporal_coverage_score,
            source_diversity_score=quality_stats.source_diversity_score,
            label_consistency_score=quality_stats.label_consistency_score,
            leakage_risk_score=quality_stats.leakage_risk_score,
            readiness_score=quality_stats.readiness_score,
            readiness_status=quality_stats.readiness_status,
            recommendations=quality_stats.recommendations,
            created_at=utc_now(),
        )
        snapshot = replace(snapshot, id=snapshot.id, completed_at=utc_now(), updated_at=utc_now())
        persisted = self.personalization_repository.save_snapshot_bundle(
            snapshot,
            [replace(example, snapshot_id=snapshot.id) for example in assembled.examples],
            [replace(conflict, snapshot_id=snapshot.id) for conflict in assembled.conflicts],
            quality_report,
            feature_schema,
        )
        progress_message = "Completado"
        self._progress(progress_callback, progress_message, 1.0)
        return PersonalizationDatasetReport(
            creator=creator,
            project=project,
            snapshot=persisted,
            feature_schema=feature_schema,
            examples=tuple(self.personalization_repository.list_examples_by_snapshot_id(persisted.id)),
            conflicts=tuple(self.personalization_repository.list_conflicts_by_snapshot_id(persisted.id)),
            quality_report=self.personalization_repository.get_quality_report_by_snapshot_id(persisted.id),
            status=persisted.status,
            is_stale=False,
            warnings=tuple(assembled.warnings + list(readiness.recommendations)),
            errors=tuple(assembled.errors),
            progress_message=progress_message,
        )

    def get_dataset_snapshot(self, snapshot_id: str) -> PersonalizationDatasetReport:
        return self._report_from_snapshot(snapshot_id)

    def get_latest_creator_dataset(self, creator_id: str) -> PersonalizationDatasetReport:
        latest = self.personalization_repository.get_latest_snapshot_by_creator_id(creator_id)
        if latest is None:
            creator = self._require_creator(creator_id)
            schema = self.personalization_repository.get_feature_schema(self.options.feature_schema_version) or build_feature_schema_entity()
            return PersonalizationDatasetReport(
                creator=creator,
                project=None,
                snapshot=None,
                feature_schema=schema,
                examples=(),
                conflicts=(),
                quality_report=None,
                status=PersonalizationDatasetStatus.FAILED,
                is_stale=True,
                warnings=("No existe un snapshot de personalizacion para este creador.",),
            )
        return self._report_from_snapshot(latest.id)

    def list_creator_datasets(self, creator_id: str) -> list[CreatorDatasetSnapshot]:
        return self.personalization_repository.list_snapshots_by_creator_id(creator_id)

    def list_dataset_examples(self, snapshot_id: str, filters: dict[str, object] | None = None) -> list[CreatorDatasetExample]:
        examples = list(self.personalization_repository.list_examples_by_snapshot_id(snapshot_id))
        if not filters:
            return examples
        label = filters.get("label")
        split_name = filters.get("split_name")
        excluded = filters.get("excluded")
        conflict_only = filters.get("conflict_only")
        if label is not None:
            examples = [example for example in examples if example.label.value == str(label)]
        if split_name is not None:
            examples = [example for example in examples if example.split_name.value == str(split_name)]
        if excluded:
            examples = [example for example in examples if example.label == PersonalizationLabel.EXCLUDED]
        if conflict_only:
            examples = [example for example in examples if example.quality_flags.get("is_conflicted")]
        return examples

    def get_dataset_example(self, example_id: str) -> CreatorDatasetExample:
        example = self.personalization_repository.get_example_by_id(example_id)
        if example is None:
            raise NotFoundError("El ejemplo de dataset solicitado no existe.")
        return example

    def get_dataset_quality_report(self, snapshot_id: str) -> CreatorDatasetQualityReport:
        report = self.personalization_repository.get_quality_report_by_snapshot_id(snapshot_id)
        if report is None:
            raise NotFoundError("El quality report solicitado no existe.")
        return report

    def get_creator_readiness(self, creator_id: str) -> CreatorReadinessReport:
        latest = self.personalization_repository.get_latest_snapshot_by_creator_id(creator_id)
        creator = self._require_creator(creator_id)
        if latest is None:
            return CreatorReadinessReport(
                creator=creator,
                latest_snapshot=None,
                readiness_status=PersonalizationReadinessStatus.NOT_READY,
                readiness_score=0.0,
                recommendations=("No hay snapshots construidos.",),
                snapshot_count=0,
                is_stale=True,
            )
        quality_report = self.personalization_repository.get_quality_report_by_snapshot_id(latest.id)
        readiness = quality_report.readiness_status if quality_report else latest.readiness_status
        score = quality_report.readiness_score if quality_report else latest.readiness_score
        recommendations = quality_report.recommendations if quality_report else ()
        return CreatorReadinessReport(
            creator=creator,
            latest_snapshot=latest,
            readiness_status=readiness,
            readiness_score=score,
            recommendations=recommendations,
            snapshot_count=len(self.personalization_repository.list_snapshots_by_creator_id(creator_id)),
            is_stale=self.is_dataset_stale(latest.id),
        )

    def compare_dataset_snapshots(self, snapshot_a_id: str, snapshot_b_id: str) -> DatasetSnapshotComparison:
        snapshot_a = self.personalization_repository.get_snapshot_by_id(snapshot_a_id)
        snapshot_b = self.personalization_repository.get_snapshot_by_id(snapshot_b_id)
        if snapshot_a is None or snapshot_b is None:
            raise NotFoundError("No se pudieron encontrar ambos snapshots para comparar.")
        return DatasetSnapshotComparison(
            snapshot_a=snapshot_a,
            snapshot_b=snapshot_b,
            example_count_delta=snapshot_b.example_count - snapshot_a.example_count,
            positive_count_delta=snapshot_b.positive_count - snapshot_a.positive_count,
            negative_count_delta=snapshot_b.negative_count - snapshot_a.negative_count,
            neutral_count_delta=snapshot_b.neutral_count - snapshot_a.neutral_count,
            excluded_count_delta=snapshot_b.excluded_count - snapshot_a.excluded_count,
            conflict_count_delta=snapshot_b.conflict_count - snapshot_a.conflict_count,
            readiness_score_delta=snapshot_b.readiness_score - snapshot_a.readiness_score,
            source_fingerprint_changed=snapshot_a.source_fingerprint != snapshot_b.source_fingerprint,
            configuration_fingerprint_changed=snapshot_a.configuration_fingerprint != snapshot_b.configuration_fingerprint,
            status_changed=snapshot_a.status != snapshot_b.status,
        )

    def archive_dataset_snapshot(self, snapshot_id: str) -> CreatorDatasetSnapshot:
        snapshot = self.personalization_repository.archive_snapshot(snapshot_id)
        if snapshot is None:
            raise NotFoundError("El snapshot solicitado no existe.")
        return snapshot

    def export_dataset(self, snapshot_id: str, format: str, *, include_sensitive: bool = False, destination: Path | None = None) -> PersonalizationDatasetExportResult:
        report = self.get_dataset_snapshot(snapshot_id)
        if report.snapshot is None:
            raise PersonalizationDataStateError("No existe snapshot para exportar.")
        format_name = format.strip().lower()
        if format_name not in {"json", "csv", "jsonl"}:
            raise PersonalizationDataValidationError("Formato de exportacion no reconocido.")
        feature_schema = report.feature_schema
        if format_name == "json":
            content = export_dataset_json(
                snapshot=report.snapshot,
                feature_schema=feature_schema,
                examples=list(report.examples),
                conflicts=list(report.conflicts),
                quality_report=report.quality_report or self.get_dataset_quality_report(snapshot_id),
                options=self.options,
                include_sensitive=include_sensitive,
            )
            suffix = "json"
        elif format_name == "csv":
            content = export_dataset_csv(
                snapshot=report.snapshot,
                feature_schema=feature_schema,
                examples=list(report.examples),
                include_sensitive=include_sensitive,
            )
            suffix = "csv"
        else:
            content = export_dataset_jsonl(
                snapshot=report.snapshot,
                feature_schema=feature_schema,
                examples=list(report.examples),
                include_sensitive=include_sensitive,
            )
            suffix = "jsonl"
        export_root = self.paths.project_root / "cache" / "personalization" / report.snapshot.creator_id / report.snapshot.id / "exports"
        export_root.mkdir(parents=True, exist_ok=True)
        destination = destination or export_root / f"creator_dataset.{suffix}"
        write_export(destination, content)
        return PersonalizationDatasetExportResult(
            snapshot=report.snapshot,
            format=suffix,
            content=content,
            path=str(destination),
        )

    def is_dataset_stale(self, snapshot_id: str) -> bool:
        snapshot = self.personalization_repository.get_snapshot_by_id(snapshot_id)
        if snapshot is None:
            return True
        creator = self._require_creator(snapshot.creator_id)
        project = self._require_project(snapshot.project_id) if snapshot.project_id else None
        _, videos = self._videos_for_scope(creator.id, project.id if project else None)
        assembled = self._build_assembled_dataset(creator, project, videos)
        return is_personalization_dataset_stale(
            snapshot,
            source_fingerprint=build_personalization_source_fingerprint(
                _build_source_payload(creator=creator, project=project, options=self.options, assembled=assembled)
            ),
            configuration_fingerprint=build_personalization_configuration_fingerprint(self.options),
        )


def build_personalization_dataset_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    clip_service: ClipRankingService,
    personalization_repository: PersonalizationDataRepository,
    logger: logging.Logger | None = None,
) -> PersonalizationDatasetService:
    return PersonalizationDatasetService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        clip_service=clip_service,
        personalization_repository=personalization_repository,
        logger=logger,
    )
