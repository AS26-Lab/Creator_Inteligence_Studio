"""Servicio principal para Thumbnail Lab and Titles Foundation."""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsQueryService
from creator_intelligence_studio.application.services.creator_language_service import CreatorLanguageService
from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService
from creator_intelligence_studio.application.services.experiment_service import ExperimentService
from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.domain.creative_packaging.concept_types import CreativeConceptResult
from creator_intelligence_studio.domain.creative_packaging.entities import (
    CreativeConcept,
    CreativePrompt,
    CreativePromptReference,
    PackagingAsset,
    PackagingBrandProfile,
    PackagingDecision,
    PackagingExperimentLink,
    PackagingPairEvaluation,
    PackagingReferenceAsset,
    ThumbnailFrameCandidate,
    ThumbnailReview,
    ThumbnailVersion,
    TitleAnalysisMetric,
    TitleAnalysisRun,
    TitleVersion,
    ThumbnailAnalysisMetric,
    ThumbnailAnalysisRun,
)
from creator_intelligence_studio.domain.creative_packaging.evaluation_types import (
    PackagingPairEvaluationResult,
    ThumbnailReviewResult,
)
from creator_intelligence_studio.domain.creative_packaging.errors import CreativePackagingNotFoundError, CreativePackagingValidationError
from creator_intelligence_studio.domain.creative_packaging.prompt_types import CreativePromptResult
from creator_intelligence_studio.domain.creative_packaging.reference_types import ReferencePackageResult
from creator_intelligence_studio.domain.creative_packaging.repositories import CreativePackagingRepository
from creator_intelligence_studio.domain.creative_packaging.services import build_creative_packaging_fingerprint
from creator_intelligence_studio.domain.creative_packaging.thumbnail_types import ThumbnailAnalysisResult, ThumbnailReviewStatus
from creator_intelligence_studio.domain.creative_packaging.title_types import TitleAnalysisResult, TitlePatternType
from creator_intelligence_studio.domain.creative_packaging.value_objects import (
    PackagingAssetStatus,
    PackagingAssetType,
    PackagingDecisionType,
    PackagingPromptTargetTool,
    PackagingRecommendationStatus,
    PackagingReviewDecision,
    PackagingRunStatus,
)
from creator_intelligence_studio.infrastructure.analytics_lab.percentile_calculator import calculate_percentile
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.creator_language import normalize_language_text
from creator_intelligence_studio.infrastructure.creator_language.filler_word_analyzer import FILLER_WORDS
from creator_intelligence_studio.infrastructure.creative_packaging.concept_builder import build_creative_concepts
from creator_intelligence_studio.infrastructure.creative_packaging.frame_quality_analyzer import extract_frame_candidates
from creator_intelligence_studio.infrastructure.creative_packaging.pair_evaluator import evaluate_title_thumbnail_pair
from creator_intelligence_studio.infrastructure.creative_packaging.prompt_adapter import adapt_prompt_for_tool
from creator_intelligence_studio.infrastructure.creative_packaging.prompt_builder import build_creative_prompt
from creator_intelligence_studio.infrastructure.creative_packaging.reference_advisor import build_reference_package
from creator_intelligence_studio.infrastructure.creative_packaging.reference_matcher import match_reference_assets
from creator_intelligence_studio.infrastructure.creative_packaging.review_builder import build_thumbnail_review_instructions
from creator_intelligence_studio.infrastructure.creative_packaging.thumbnail_composition_analyzer import analyze_thumbnail_pixels
from creator_intelligence_studio.infrastructure.creative_packaging.thumbnail_metadata_analyzer import read_thumbnail_pixels
from creator_intelligence_studio.infrastructure.creative_packaging.title_feature_extractor import analyze_title_text
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_language_repository import SQLiteCreatorLanguageRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_memory_repository import SQLiteCreatorMemoryRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_experiment_repository import SQLiteExperimentRepository
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback):
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return value if value is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _sanitize_csv(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped and stripped[0] in "=+-@" and not (stripped[0] in "+-" and stripped[1:].replace(".", "", 1).isdigit()):
        return "'" + value
    return value


def _extract_terms(value: object) -> set[str]:
    terms: set[str] = set()
    if value is None:
        return terms
    if isinstance(value, str):
        terms.update(re.findall(r"[A-Za-zÀ-ÿ0-9_@#]+", value.casefold()))
        return terms
    if isinstance(value, dict):
        for item in value.values():
            terms.update(_extract_terms(item))
        return terms
    if isinstance(value, (list, tuple, set)):
        for item in value:
            terms.update(_extract_terms(item))
        return terms
    return terms


def _json_array(value: object) -> str:
    if isinstance(value, str):
        return value
    return _json_dumps(value if value is not None else [])


@dataclass(frozen=True, slots=True)
class CreativePackagingAnalysisDetail:
    run: TitleAnalysisRun | ThumbnailAnalysisRun
    asset: PackagingAsset
    version: TitleVersion | ThumbnailVersion
    analysis: TitleAnalysisResult | ThumbnailAnalysisResult
    metrics: tuple[TitleAnalysisMetric | ThumbnailAnalysisMetric, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "asset": self.asset.to_dict(),
            "version": self.version.to_dict(),
            "analysis": self.analysis.to_dict(),
            "metrics": [item.to_dict() for item in self.metrics],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class PackagingBrandProfileDetail:
    profile: PackagingBrandProfile | None
    references: tuple[PackagingReferenceAsset, ...]
    titles: tuple[TitleVersion, ...]
    thumbnails: tuple[ThumbnailVersion, ...]
    pair_evaluations: tuple[PackagingPairEvaluation, ...]
    decisions: tuple[PackagingDecision, ...]
    experiment_links: tuple[PackagingExperimentLink, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.to_dict() if self.profile else None,
            "references": [item.to_dict() for item in self.references],
            "titles": [item.to_dict() for item in self.titles],
            "thumbnails": [item.to_dict() for item in self.thumbnails],
            "pair_evaluations": [item.to_dict() for item in self.pair_evaluations],
            "decisions": [item.to_dict() for item in self.decisions],
            "experiment_links": [item.to_dict() for item in self.experiment_links],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CreativePackagingExportResult:
    creator_id: str
    format: str
    path: str
    rows_written: int
    created_at: str
    summary: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "format": self.format,
            "path": self.path,
            "rows_written": self.rows_written,
            "created_at": self.created_at,
            "summary": self.summary,
        }


class CreativePackagingService:
    ANALYZER_VERSION = "v1"

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: CreativePackagingRepository,
        database: SQLiteDatabase,
        catalog_service: CatalogService | None = None,
        analytics_repository: SQLiteAnalyticsRepository | None = None,
        creator_memory_service: CreatorMemoryService | None = None,
        creator_language_service: CreatorLanguageService | None = None,
        experiment_service: ExperimentService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.database = database
        self.catalog_service = catalog_service
        self.analytics_repository = analytics_repository
        self.creator_memory_service = creator_memory_service
        self.creator_language_service = creator_language_service
        self.experiment_service = experiment_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creative_packaging")
        self._exports_root = self.paths.data_directory / "packaging" / "exports"
        self._exports_root.mkdir(parents=True, exist_ok=True)

    def _creator_memory_terms(self, creator_id: str) -> set[str]:
        if self.creator_memory_service is None:
            return set()
        detail = self.creator_memory_service.get_profile_detail(creator_id)
        terms = set()
        for item in detail.vocabulary:
            terms.update(_extract_terms(item.term))
            terms.update(_extract_terms(item.meaning))
            terms.update(_extract_terms(item.usage_notes))
        for example in detail.examples:
            terms.update(_extract_terms(example.title))
            terms.update(_extract_terms(example.text_content))
        for rule in detail.rules:
            terms.update(_extract_terms(rule.statement))
        return {term for term in terms if term}

    def _creator_language_terms(self, creator_id: str) -> set[str]:
        if self.creator_language_service is None:
            return set()
        detail = self.creator_language_service.get_profile_detail(creator_id)
        terms = set()
        for pattern in detail.patterns:
            terms.update(_extract_terms(pattern.title))
            terms.update(_extract_terms(pattern.description))
        for candidate in detail.candidates:
            terms.update(_extract_terms(candidate.proposed_key))
            terms.update(_extract_terms(candidate.proposed_value_json))
        return {term for term in terms if term}

    def _current_brand_profile(self, creator_id: str) -> PackagingBrandProfile | None:
        return self.repository.get_brand_profile(creator_id)

    def _brand_reference_payload(self, creator_id: str) -> dict[str, object]:
        references = [reference.to_dict() for reference in self.repository.list_reference_assets(creator_id)]
        titles = [title.to_dict() for asset in self.repository.list_assets(creator_id) for title in self.repository.list_title_versions(asset.id)]
        thumbnails = [thumbnail.to_dict() for asset in self.repository.list_assets(creator_id) for thumbnail in self.repository.list_thumbnail_versions(asset.id)]
        pair_evaluations = [evaluation.to_dict() for evaluation in self.repository.list_pair_evaluations(creator_id)]
        decisions = [decision.to_dict() for decision in self.repository.list_decisions(creator_id)]
        links = [link.to_dict() for asset in self.repository.list_assets(creator_id) for link in self.repository.list_experiment_links(asset.id)]
        return {
            "references": references,
            "titles": titles,
            "thumbnails": thumbnails,
            "pair_evaluations": pair_evaluations,
            "decisions": decisions,
            "experiment_links": links,
        }

    def _find_asset(self, creator_id: str, asset_type: PackagingAssetType, *, publication_id: str | None = None, video_asset_id: str | None = None, platform: str | None = None, content_type: str | None = None, topic: str | None = None) -> PackagingAsset:
        assets = self.repository.list_assets(creator_id)
        for asset in assets:
            if asset.asset_type != asset_type:
                continue
            if publication_id is not None and asset.publication_id != publication_id:
                continue
            if video_asset_id is not None and asset.video_asset_id != video_asset_id:
                continue
            if platform is not None and asset.platform != platform:
                continue
            if content_type is not None and asset.content_type != content_type:
                continue
            if topic is not None and asset.topic != topic:
                continue
            return asset
        asset = PackagingAsset(
            id=str(uuid4()),
            creator_id=creator_id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            asset_type=asset_type,
            platform=platform or "manual_other",
            content_type=content_type or "other",
            topic=topic,
            status=PackagingAssetStatus.ACTIVE,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_asset(asset)

    def create_asset(self, *, creator_id: str, asset_type: str, platform: str, content_type: str, publication_id: str | None = None, video_asset_id: str | None = None, topic: str | None = None, status: str = PackagingAssetStatus.ACTIVE.value) -> PackagingAsset:
        asset = PackagingAsset(
            id=str(uuid4()),
            creator_id=creator_id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            asset_type=PackagingAssetType(asset_type),
            platform=platform,
            content_type=content_type,
            topic=topic,
            status=PackagingAssetStatus(status),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_asset(asset)

    def list_assets(self, creator_id: str) -> list[PackagingAsset]:
        return self.repository.list_assets(creator_id)

    def get_asset(self, asset_id: str) -> PackagingAsset | None:
        return self.repository.get_asset(asset_id)

    def create_title_version(
        self,
        *,
        creator_id: str,
        title_text: str,
        platform: str,
        content_type: str,
        source_type: str = "manual",
        language: str = "es",
        topic: str | None = None,
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        packaging_asset_id: str | None = None,
        is_published: bool = False,
        is_selected: bool = False,
        creator_approval_status: str = "pending",
        creator_feedback: str | None = None,
    ) -> TitleVersion:
        asset = self.repository.get_asset(packaging_asset_id) if packaging_asset_id else None
        if asset is None:
            asset = self._find_asset(
                creator_id,
                PackagingAssetType.TITLE,
                publication_id=publication_id,
                video_asset_id=video_asset_id,
                platform=platform,
                content_type=content_type,
                topic=topic,
            )
        version_number = (max((item.version_number for item in self.repository.list_title_versions(asset.id)), default=0) + 1)
        fingerprint = build_creative_packaging_fingerprint(
            {
                "asset_id": asset.id,
                "title_text": title_text.strip(),
                "source_type": source_type,
                "language": language,
                "platform": platform,
                "content_type": content_type,
                "topic": topic,
                "version_number": version_number,
                "creator_approval_status": creator_approval_status,
            }
        )
        title = TitleVersion(
            id=str(uuid4()),
            packaging_asset_id=asset.id,
            version_number=version_number,
            title_text=title_text.strip(),
            source_type=source_type,
            language=language,
            platform=platform,
            content_type=content_type,
            topic=topic,
            is_published=is_published,
            is_selected=is_selected,
            creator_approval_status=creator_approval_status,
            creator_feedback=creator_feedback,
            source_fingerprint=fingerprint,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_title_version(title)

    def list_title_versions(self, packaging_asset_id: str) -> list[TitleVersion]:
        return self.repository.list_title_versions(packaging_asset_id)

    def get_title_version(self, title_version_id: str) -> TitleVersion | None:
        return self.repository.get_title_version(title_version_id)

    def list_title_analysis_runs(self, creator_id: str) -> list[TitleAnalysisRun]:
        return self.repository.list_title_analysis_runs(creator_id)

    def list_title_analysis_metrics(self, run_id: str) -> list[TitleAnalysisMetric]:
        return self.repository.list_title_analysis_metrics(run_id)

    def _title_analysis_run(self, title_version: TitleVersion) -> TitleAnalysisRun | None:
        for run in self.repository.list_title_analysis_runs(title_version.platform and title_version.platform or title_version.packaging_asset_id):
            if run.title_version_id == title_version.id and run.analyzer_version == self.ANALYZER_VERSION:
                return run
        return None

    def analyze_title(self, title_version_id: str, *, force_recompute: bool = False) -> CreativePackagingAnalysisDetail:
        title_version = self.repository.get_title_version(title_version_id)
        if title_version is None:
            raise CreativePackagingNotFoundError("La version del titulo no existe.")
        asset = self.repository.get_asset(title_version.packaging_asset_id)
        if asset is None:
            raise CreativePackagingNotFoundError("El asset del titulo no existe.")
        existing_runs = [run for run in self.repository.list_title_analysis_runs(asset.creator_id) if run.title_version_id == title_version.id and run.analyzer_version == self.ANALYZER_VERSION]
        if existing_runs and not force_recompute and existing_runs[0].status in {PackagingRunStatus.COMPLETED, PackagingRunStatus.COMPLETED_WITH_WARNINGS}:
            run = existing_runs[0]
            metrics = tuple(self.repository.list_title_analysis_metrics(run.id))
            analysis = analyze_title_text(
                title_version.title_text,
                platform=title_version.platform,
                content_type=title_version.content_type,
                creator_vocabulary=self._creator_memory_terms(asset.creator_id),
                creator_style_terms=self._creator_language_terms(asset.creator_id),
                historical_titles=[item.title_text for item in self.repository.list_title_versions(asset.id) if item.id != title_version.id],
                rejected_titles=[item.title_text for item in self.repository.list_title_versions(asset.id) if str(item.creator_approval_status).lower() in {"rejected", "needs_more_work"}],
                prohibited_terms=list(FILLER_WORDS),
            )
            return CreativePackagingAnalysisDetail(run=run, asset=asset, version=title_version, analysis=analysis, metrics=metrics, warnings=tuple())
        memory_terms = self._creator_memory_terms(asset.creator_id)
        language_terms = self._creator_language_terms(asset.creator_id)
        historical_titles = [item.title_text for item in self.repository.list_title_versions(asset.id) if item.id != title_version.id]
        rejected_titles = [item.title_text for item in self.repository.list_title_versions(asset.id) if str(item.creator_approval_status).lower() in {"rejected", "needs_more_work"}]
        result = analyze_title_text(
            title_version.title_text,
            platform=title_version.platform,
            content_type=title_version.content_type,
            creator_vocabulary=memory_terms,
            creator_style_terms=language_terms,
            historical_titles=historical_titles,
            rejected_titles=rejected_titles,
            prohibited_terms=list(FILLER_WORDS),
        )
        run = TitleAnalysisRun(
            id=str(uuid4()),
            creator_id=asset.creator_id,
            title_version_id=title_version.id,
            analyzer_version=self.ANALYZER_VERSION,
            status=PackagingRunStatus.RUNNING,
            configuration_json=_json_dumps({"force_recompute": force_recompute}),
            creator_memory_snapshot_id=None,
            creator_language_snapshot_id=None,
            brand_profile_version=self._current_brand_profile(asset.creator_id).profile_version if self._current_brand_profile(asset.creator_id) else None,
            source_fingerprint=build_creative_packaging_fingerprint({
                "title_version": title_version.to_dict(),
                "memory_terms": sorted(memory_terms),
                "language_terms": sorted(language_terms),
            }),
            warning_count=len(result.warnings),
            created_at=utc_now(),
            completed_at=None,
        )
        persisted_run = self.repository.upsert_title_analysis_run(run)
        metrics: list[TitleAnalysisMetric] = []
        for metric in result.metrics:
            stored = TitleAnalysisMetric(
                id=str(uuid4()),
                analysis_run_id=persisted_run.id,
                metric_key=metric.metric_key,
                numeric_value=metric.numeric_value,
                text_value=metric.text_value,
                unit=metric.unit,
                confidence_level=metric.confidence_level,
                warning_codes_json=_json_dumps(list(metric.warning_codes)),
                created_at=utc_now(),
            )
            metrics.append(self.repository.upsert_title_analysis_metric(stored))
        completed = replace(
            persisted_run,
            status=PackagingRunStatus.COMPLETED_WITH_WARNINGS if result.warnings else PackagingRunStatus.COMPLETED,
            warning_count=len(result.warnings),
            completed_at=utc_now(),
        )
        completed_run = self.repository.upsert_title_analysis_run(completed)
        return CreativePackagingAnalysisDetail(run=completed_run, asset=asset, version=title_version, analysis=result, metrics=tuple(metrics), warnings=tuple(sorted(result.warnings)))

    def create_thumbnail_version(
        self,
        *,
        creator_id: str,
        image_path: str | None,
        source_type: str = "manual",
        platform: str,
        content_type: str,
        topic: str | None = None,
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        packaging_asset_id: str | None = None,
        concept_id: str | None = None,
        is_published: bool = False,
        is_selected: bool = False,
        creator_approval_status: str = "pending",
        creator_feedback: str | None = None,
    ) -> ThumbnailVersion:
        asset = self.repository.get_asset(packaging_asset_id) if packaging_asset_id else None
        if asset is None:
            asset = self._find_asset(
                creator_id,
                PackagingAssetType.THUMBNAIL,
                publication_id=publication_id,
                video_asset_id=video_asset_id,
                platform=platform,
                content_type=content_type,
                topic=topic,
            )
        version_number = (max((item.version_number for item in self.repository.list_thumbnail_versions(asset.id)), default=0) + 1)
        metadata, _ = read_thumbnail_pixels(Path(image_path), ffmpeg_path=self.settings.ffmpeg_path, ffprobe_path=self.settings.ffprobe_path) if image_path else (None, None)
        fingerprint = metadata.file_fingerprint if metadata and metadata.file_fingerprint else build_creative_packaging_fingerprint({
            "asset_id": asset.id,
            "image_path": image_path,
            "source_type": source_type,
            "platform": platform,
            "content_type": content_type,
            "topic": topic,
            "version_number": version_number,
        })
        thumbnail = ThumbnailVersion(
            id=str(uuid4()),
            packaging_asset_id=asset.id,
            version_number=version_number,
            image_path=image_path,
            source_type=source_type,
            width=metadata.width if metadata else None,
            height=metadata.height if metadata else None,
            file_fingerprint=fingerprint,
            concept_id=concept_id,
            is_published=is_published,
            is_selected=is_selected,
            creator_approval_status=creator_approval_status,
            creator_feedback=creator_feedback,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_thumbnail_version(thumbnail)

    def list_thumbnail_versions(self, packaging_asset_id: str) -> list[ThumbnailVersion]:
        return self.repository.list_thumbnail_versions(packaging_asset_id)

    def get_thumbnail_version(self, thumbnail_version_id: str) -> ThumbnailVersion | None:
        return self.repository.get_thumbnail_version(thumbnail_version_id)

    def list_thumbnail_analysis_runs(self, creator_id: str) -> list[ThumbnailAnalysisRun]:
        return self.repository.list_thumbnail_analysis_runs(creator_id)

    def list_thumbnail_analysis_metrics(self, run_id: str) -> list[ThumbnailAnalysisMetric]:
        return self.repository.list_thumbnail_analysis_metrics(run_id)

    def analyze_thumbnail(self, thumbnail_version_id: str, *, force_recompute: bool = False) -> CreativePackagingAnalysisDetail:
        thumbnail_version = self.repository.get_thumbnail_version(thumbnail_version_id)
        if thumbnail_version is None:
            raise CreativePackagingNotFoundError("La version de la miniatura no existe.")
        asset = self.repository.get_asset(thumbnail_version.packaging_asset_id)
        if asset is None:
            raise CreativePackagingNotFoundError("El asset de la miniatura no existe.")
        existing_runs = [run for run in self.repository.list_thumbnail_analysis_runs(asset.creator_id) if run.thumbnail_version_id == thumbnail_version.id and run.analyzer_version == self.ANALYZER_VERSION]
        if existing_runs and not force_recompute and existing_runs[0].status in {PackagingRunStatus.COMPLETED, PackagingRunStatus.COMPLETED_WITH_WARNINGS}:
            run = existing_runs[0]
            metrics = tuple(self.repository.list_thumbnail_analysis_metrics(run.id))
            metadata, pixels = read_thumbnail_pixels(Path(thumbnail_version.image_path), ffmpeg_path=self.settings.ffmpeg_path, ffprobe_path=self.settings.ffprobe_path) if thumbnail_version.image_path else (None, None)
            analysis = analyze_thumbnail_pixels(
                pixels,
                width=thumbnail_version.width or (metadata.width if metadata else None),
                height=thumbnail_version.height or (metadata.height if metadata else None),
                platform=asset.platform,
                brand_palette=_json_loads(self.repository.get_brand_profile(asset.creator_id).preferred_palette_json, []) if self.repository.get_brand_profile(asset.creator_id) else None,
                approved_patterns=_json_loads(self.repository.get_brand_profile(asset.creator_id).approved_patterns_json, []) if self.repository.get_brand_profile(asset.creator_id) else None,
                rejected_patterns=_json_loads(self.repository.get_brand_profile(asset.creator_id).rejected_patterns_json, []) if self.repository.get_brand_profile(asset.creator_id) else None,
            )
            return CreativePackagingAnalysisDetail(run=run, asset=asset, version=thumbnail_version, analysis=analysis, metrics=metrics, warnings=tuple())
        brand_profile = self.repository.get_brand_profile(asset.creator_id)
        pixels = None
        metadata = None
        if thumbnail_version.image_path:
            metadata, pixels = read_thumbnail_pixels(Path(thumbnail_version.image_path), ffmpeg_path=self.settings.ffmpeg_path, ffprobe_path=self.settings.ffprobe_path)
        result = analyze_thumbnail_pixels(
            pixels,
            width=thumbnail_version.width or (metadata.width if metadata else None),
            height=thumbnail_version.height or (metadata.height if metadata else None),
            platform=asset.platform,
            brand_palette=_json_loads(brand_profile.preferred_palette_json, []) if brand_profile else None,
            approved_patterns=_json_loads(brand_profile.approved_patterns_json, []) if brand_profile else None,
            rejected_patterns=_json_loads(brand_profile.rejected_patterns_json, []) if brand_profile else None,
        )
        warnings = set(result.warnings)
        if metadata:
            warnings.update(metadata.warnings)
        run = ThumbnailAnalysisRun(
            id=str(uuid4()),
            creator_id=asset.creator_id,
            thumbnail_version_id=thumbnail_version.id,
            analyzer_version=self.ANALYZER_VERSION,
            status=PackagingRunStatus.RUNNING,
            configuration_json=_json_dumps({"force_recompute": force_recompute}),
            creator_memory_snapshot_id=None,
            creator_language_snapshot_id=None,
            brand_profile_version=brand_profile.profile_version if brand_profile else None,
            source_fingerprint=build_creative_packaging_fingerprint({
                "thumbnail_version": thumbnail_version.to_dict(),
                "brand_profile_version": brand_profile.profile_version if brand_profile else None,
                "warning_codes": sorted(warnings),
            }),
            warning_count=len(warnings),
            created_at=utc_now(),
            completed_at=None,
        )
        persisted_run = self.repository.upsert_thumbnail_analysis_run(run)
        metrics: list[ThumbnailAnalysisMetric] = []
        for metric in result.metrics:
            stored = ThumbnailAnalysisMetric(
                id=str(uuid4()),
                analysis_run_id=persisted_run.id,
                metric_key=metric.metric_key,
                numeric_value=metric.numeric_value,
                text_value=metric.text_value,
                unit=metric.unit,
                confidence_level=metric.confidence_level,
                warning_codes_json=_json_dumps(list(metric.warning_codes)),
                created_at=utc_now(),
            )
            metrics.append(self.repository.upsert_thumbnail_analysis_metric(stored))
        completed = replace(
            persisted_run,
            status=PackagingRunStatus.COMPLETED_WITH_WARNINGS if warnings else PackagingRunStatus.COMPLETED,
            warning_count=len(warnings),
            completed_at=utc_now(),
        )
        completed_run = self.repository.upsert_thumbnail_analysis_run(completed)
        analysis = replace(result, warnings=tuple(sorted(warnings)))
        return CreativePackagingAnalysisDetail(run=completed_run, asset=asset, version=thumbnail_version, analysis=analysis, metrics=tuple(metrics), warnings=tuple(sorted(warnings)))

    def list_reference_assets(self, creator_id: str) -> list[PackagingReferenceAsset]:
        return self.repository.list_reference_assets(creator_id)

    def get_reference_asset(self, reference_id: str) -> PackagingReferenceAsset | None:
        return self.repository.get_reference_asset(reference_id)

    def add_reference_asset(
        self,
        *,
        creator_id: str,
        reference_type: str,
        source_type: str,
        reference_purpose: str,
        usage_permission: str,
        image_path: str | None = None,
        text_content: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        source_creator_name: str | None = None,
        source_url: str | None = None,
        represents_creator: bool = False,
        approval_status: str = "pending",
        notes: str | None = None,
    ) -> PackagingReferenceAsset:
        fingerprint = build_creative_packaging_fingerprint({
            "creator_id": creator_id,
            "reference_type": reference_type,
            "image_path": image_path,
            "text_content": text_content,
            "platform": platform,
            "content_type": content_type,
            "topic": topic,
            "source_type": source_type,
            "source_creator_name": source_creator_name,
            "source_url": source_url,
            "usage_permission": usage_permission,
            "represents_creator": represents_creator,
            "approval_status": approval_status,
            "reference_purpose": reference_purpose,
            "notes": notes,
        })
        reference = PackagingReferenceAsset(
            id=str(uuid4()),
            creator_id=creator_id,
            reference_type=reference_type,
            image_path=image_path,
            text_content=text_content,
            platform=platform,
            content_type=content_type,
            topic=topic,
            source_type=source_type,
            source_creator_name=source_creator_name,
            source_url=source_url,
            usage_permission=usage_permission,
            represents_creator=represents_creator,
            approval_status=approval_status,
            reference_purpose=reference_purpose,
            notes=notes,
            file_fingerprint=fingerprint,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_reference_asset(reference)

    def review_reference_asset(self, reference_id: str, *, approval_status: str, notes: str | None = None) -> PackagingReferenceAsset:
        reference = self.repository.get_reference_asset(reference_id)
        if reference is None:
            raise CreativePackagingNotFoundError("La referencia no existe.")
        return self.repository.upsert_reference_asset(replace(reference, approval_status=approval_status, notes=notes or reference.notes, updated_at=utc_now()))

    def build_brand_profile(self, creator_id: str) -> PackagingBrandProfile:
        existing = self.repository.get_brand_profile(creator_id)
        references = self.repository.list_reference_assets(creator_id)
        titles = [title for asset in self.repository.list_assets(creator_id) for title in self.repository.list_title_versions(asset.id)]
        thumbnails = [thumbnail for asset in self.repository.list_assets(creator_id) for thumbnail in self.repository.list_thumbnail_versions(asset.id)]
        evaluations = self.repository.list_pair_evaluations(creator_id)
        decisions = self.repository.list_decisions(creator_id)
        experiment_links = [link for asset in self.repository.list_assets(creator_id) for link in self.repository.list_experiment_links(asset.id)]
        memory_terms = self._creator_memory_terms(creator_id)
        language_terms = self._creator_language_terms(creator_id)
        source_fingerprint = build_creative_packaging_fingerprint({
            "references": [reference.to_dict() for reference in references],
            "titles": [title.to_dict() for title in titles],
            "thumbnails": [thumbnail.to_dict() for thumbnail in thumbnails],
            "evaluations": [evaluation.to_dict() for evaluation in evaluations],
            "decisions": [decision.to_dict() for decision in decisions],
            "experiment_links": [link.to_dict() for link in experiment_links],
            "memory_terms": sorted(memory_terms),
            "language_terms": sorted(language_terms),
        })
        if existing and existing.source_fingerprint == source_fingerprint:
            return existing
        palette = sorted({reference.reference_purpose for reference in references if "palette" in reference.reference_type or "color" in reference.reference_type})
        subject_guidance = " ".join(sorted({reference.reference_purpose for reference in references if reference.reference_type in {"creator_face", "product", "instrument", "object", "recurring_object"}}))
        expression_guidance = " ".join(sorted(memory_terms & language_terms)) or "Usar expresiones coherentes con la memoria local."
        completeness = sum(bool(value) for value in [references, titles, thumbnails, evaluations, decisions, experiment_links]) / 6.0
        visual_identity = {
            "completeness": round(completeness, 2),
            "notes": "Perfil derivado localmente y revisable.",
            "evidence": len(references) + len(titles) + len(thumbnails),
            "confidence": "low" if completeness < 0.5 else "medium",
        }
        composition = {
            "approved_patterns": [evaluation.recommendation_status.value for evaluation in evaluations if evaluation.recommendation_status == PackagingRecommendationStatus.APPROVED_AS_IS],
            "rejected_patterns": [evaluation.recommendation_status.value for evaluation in evaluations if evaluation.recommendation_status == PackagingRecommendationStatus.NOT_RECOMMENDED],
            "element_count_hint": len(references) + len(thumbnails),
        }
        brand_profile = PackagingBrandProfile(
            id=existing.id if existing else str(uuid4()),
            creator_id=creator_id,
            profile_version=(existing.profile_version + 1) if existing else 1,
            brand_summary=(
                f"Perfil de marca de packaging para {creator_id} con {len(references)} referencias, {len(titles)} titulos y {len(thumbnails)} miniaturas."
            ),
            visual_identity_json=_json_dumps(visual_identity),
            preferred_composition_json=_json_dumps(composition),
            preferred_palette_json=_json_dumps(palette),
            typography_guidance_json=_json_dumps({
                "title_length_hint": "corto" if any(len(title.title_text) < 40 for title in titles) else "variable",
                "text_density": "minima",
            }),
            subject_guidance_json=_json_dumps({
                "summary": subject_guidance or "Sujeto principal claro y contextual.",
                "references": [reference.id for reference in references if reference.represents_creator],
            }),
            expression_guidance_json=_json_dumps({
                "summary": expression_guidance,
                "examples": [example.title for example in (self.creator_memory_service.list_examples(creator_id) if self.creator_memory_service else [])[:5]],
            }),
            approved_patterns_json=_json_dumps([evaluation.to_dict() for evaluation in evaluations if evaluation.recommendation_status == PackagingRecommendationStatus.APPROVED_AS_IS]),
            rejected_patterns_json=_json_dumps([evaluation.to_dict() for evaluation in evaluations if evaluation.recommendation_status == PackagingRecommendationStatus.NOT_RECOMMENDED]),
            prohibited_elements_json=_json_dumps([decision.to_dict() for decision in decisions if decision.decision == PackagingDecisionType.REJECTED]),
            platform_differences_json=_json_dumps(sorted({asset.platform for asset in self.repository.list_assets(creator_id)})),
            source_fingerprint=source_fingerprint,
            created_at=existing.created_at if existing else utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_brand_profile(brand_profile)

    def list_brand_profiles(self, creator_id: str) -> list[PackagingBrandProfile]:
        return self.repository.list_brand_profiles(creator_id)

    def get_brand_profile(self, creator_id: str) -> PackagingBrandProfile | None:
        return self.repository.get_brand_profile(creator_id)

    def get_brand_profile_detail(self, creator_id: str) -> PackagingBrandProfileDetail:
        profile = self.repository.get_brand_profile(creator_id)
        return PackagingBrandProfileDetail(
            profile=profile,
            references=tuple(self.repository.list_reference_assets(creator_id)),
            titles=tuple(title for asset in self.repository.list_assets(creator_id) for title in self.repository.list_title_versions(asset.id)),
            thumbnails=tuple(thumbnail for asset in self.repository.list_assets(creator_id) for thumbnail in self.repository.list_thumbnail_versions(asset.id)),
            pair_evaluations=tuple(self.repository.list_pair_evaluations(creator_id)),
            decisions=tuple(self.repository.list_decisions(creator_id)),
            experiment_links=tuple(link for asset in self.repository.list_assets(creator_id) for link in self.repository.list_experiment_links(asset.id)),
            warnings=tuple([] if profile else ["incomplete_brand_profile"]),
        )

    def evaluate_pair(
        self,
        *,
        title_version_id: str,
        thumbnail_version_id: str,
        publication_id: str | None = None,
    ) -> PackagingPairEvaluation:
        title = self.repository.get_title_version(title_version_id)
        thumbnail = self.repository.get_thumbnail_version(thumbnail_version_id)
        if title is None or thumbnail is None:
            raise CreativePackagingNotFoundError("No se encontro el titulo o la miniatura.")
        asset = self.repository.get_asset(title.packaging_asset_id)
        if asset is None:
            raise CreativePackagingNotFoundError("El asset de packaging no existe.")
        existing = next(
            (
                item
                for item in self.repository.list_pair_evaluations(asset.creator_id)
                if item.title_version_id == title_version_id and item.thumbnail_version_id == thumbnail_version_id and item.publication_id == publication_id
            ),
            None,
        )
        if existing is not None:
            return existing
        title_analysis = self.analyze_title(title_version_id)
        thumbnail_analysis = self.analyze_thumbnail(thumbnail_version_id)
        brand_profile = self.repository.get_brand_profile(asset.creator_id)
        history_summary = {
            "fit_score": calculate_percentile(
                [evaluation.creator_brand_alignment_score or 0.0 for evaluation in self.repository.list_pair_evaluations(asset.creator_id)],
                50.0,
            ) or 0.0
        }
        publication = None
        if publication_id and self.analytics_repository is not None:
            publication = self.analytics_repository.get_publication_by_id(publication_id)
        result = evaluate_title_thumbnail_pair(
            title_analysis=title_analysis.analysis.to_dict(),
            thumbnail_analysis=thumbnail_analysis.analysis.to_dict(),
            brand_profile=brand_profile.to_dict() if brand_profile else None,
            history_summary=history_summary,
            publication=publication.to_dict() if publication else None,
            title_text=title.title_text,
            thumbnail_text=None,
        )
        evaluation = PackagingPairEvaluation(
            id=str(uuid4()),
            creator_id=asset.creator_id,
            title_version_id=title_version_id,
            thumbnail_version_id=thumbnail_version_id,
            publication_id=publication_id,
            status=PackagingRunStatus.COMPLETED,
            visual_quality_score=result.visual_quality_score,
            content_alignment_score=result.content_alignment_score,
            creator_brand_alignment_score=result.creator_brand_alignment_score,
            audience_fit_score=result.audience_fit_score,
            platform_fit_score=result.platform_fit_score,
            historical_fit_score=result.historical_fit_score,
            niche_fit_score=result.niche_fit_score,
            differentiation_score=result.differentiation_score,
            clarity_score=result.clarity_score,
            curiosity_score=result.curiosity_score,
            hierarchy_score=result.hierarchy_score,
            complement_score=result.complement_score,
            authenticity_score=result.authenticity_score,
            promise_alignment_score=result.promise_alignment_score,
            evidence_json=_json_dumps(result.evidence),
            warnings_json=_json_dumps(list(result.warnings)),
            risks_json=_json_dumps(list(result.risks)),
            limitations_json=_json_dumps(list(result.limitations)),
            recommendation_status=PackagingRecommendationStatus(result.recommendation_status),
            created_at=utc_now(),
        )
        return self.repository.upsert_pair_evaluation(evaluation)

    def list_pair_evaluations(self, creator_id: str) -> list[PackagingPairEvaluation]:
        return self.repository.list_pair_evaluations(creator_id)

    def get_pair_evaluation(self, evaluation_id: str) -> PackagingPairEvaluation | None:
        return self.repository.get_pair_evaluation(evaluation_id)

    def extract_frame_candidates(self, *, creator_id: str, video_asset_id: str, timestamps: list[float] | None = None) -> tuple[ThumbnailFrameCandidate, ...]:
        if self.catalog_service is None:
            raise CreativePackagingValidationError("El servicio de catalogo no esta disponible.")
        video = self.catalog_service.get_video(video_asset_id)
        candidates = extract_frame_candidates(
            creator_id=creator_id,
            video_asset_id=video_asset_id,
            video_path=Path(video.source_path),
            duration_seconds=video.duration_seconds,
            ffmpeg_path=self.settings.ffmpeg_path,
            ffprobe_path=self.settings.ffprobe_path,
            timestamps=timestamps,
        )
        persisted = [self.repository.upsert_frame_candidate(candidate) for candidate in candidates]
        if timestamps:
            timestamp_set = {round(timestamp, 1) for timestamp in timestamps}
            persisted = [candidate for candidate in persisted if round(candidate.timestamp_seconds, 1) in timestamp_set]
        return tuple(persisted)

    def list_frame_candidates(self, creator_id: str, video_asset_id: str | None = None) -> list[ThumbnailFrameCandidate]:
        return self.repository.list_frame_candidates(creator_id, video_asset_id=video_asset_id)

    def build_concepts(
        self,
        *,
        creator_id: str,
        platform: str,
        content_type: str,
        topic: str | None = None,
        title: str | None = None,
        objective: str | None = None,
        audience: str | None = None,
        concept_type: str = "curiosity_driven",
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        references: list[dict[str, object]] | None = None,
        constraints: list[str] | None = None,
    ) -> CreativeConcept:
        brand_profile = self.repository.get_brand_profile(creator_id)
        concept_result: CreativeConceptResult = build_creative_concepts(
            creator_id=creator_id,
            platform=platform,
            content_type=content_type,
            topic=topic,
            title=title,
            objective=objective,
            audience=audience,
            concept_type=concept_type,
            brand_profile=brand_profile.to_dict() if brand_profile else None,
            language_profile=self.creator_language_service.get_profile_detail(creator_id).to_dict() if self.creator_language_service else None,
            historical_fit={"fit_score": 0.5},
            references=references,
            constraints=constraints,
        )
        concept = CreativeConcept(
            id=str(uuid4()),
            creator_id=creator_id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            concept_type=concept_result.concept_type,
            platform=platform,
            content_type=content_type,
            topic=topic,
            title=concept_result.title,
            premise=concept_result.premise,
            subject_description=concept_result.subject_description,
            action_description=concept_result.action_description,
            composition_description=concept_result.composition_description,
            emotion_description=concept_result.emotion_description,
            background_description=concept_result.background_description,
            color_guidance=concept_result.color_guidance,
            text_guidance=concept_result.text_guidance,
            visual_hierarchy=concept_result.visual_hierarchy,
            relation_to_title=concept_result.relation_to_title,
            brand_alignment_notes=concept_result.brand_alignment_notes,
            audience_fit_notes=concept_result.audience_fit_notes,
            platform_fit_notes=concept_result.platform_fit_notes,
            differentiation_notes=concept_result.differentiation_notes,
            authenticity_notes=concept_result.authenticity_notes,
            risks_json=_json_dumps(list(concept_result.risks)),
            reference_requirements_json=_json_dumps(list(concept_result.reference_requirements)),
            status="draft",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_concept(concept)

    def list_concepts(self, creator_id: str) -> list[CreativeConcept]:
        return self.repository.list_concepts(creator_id)

    def get_concept(self, concept_id: str) -> CreativeConcept | None:
        return self.repository.get_concept(concept_id)

    def build_prompt(self, *, concept_id: str, target_tool: str, title: str | None = None) -> CreativePrompt:
        concept = self.repository.get_concept(concept_id)
        if concept is None:
            raise CreativePackagingNotFoundError("El concepto no existe.")
        references = self.repository.list_reference_assets(concept.creator_id)
        matched = match_reference_assets(
            [reference.to_dict() for reference in references],
            purpose=concept.concept_type,
            platform=concept.platform,
        )
        reference_package = build_reference_package(
            references=matched,
            concept_type=concept.concept_type,
            has_creator_face=any(reference.get("represents_creator") for reference in matched),
            has_object_focus=any(reference.get("reference_type") in {"product", "instrument", "recurring_object"} for reference in matched),
        )
        brand_profile = self.repository.get_brand_profile(concept.creator_id)
        language_profile = self.creator_language_service.get_profile_detail(concept.creator_id).to_dict() if self.creator_language_service else None
        prompt_result: CreativePromptResult = build_creative_prompt(
            concept=concept.to_dict(),
            target_tool=target_tool,
            reference_package=reference_package.to_dict(),
            title=title,
            brand_profile=brand_profile.to_dict() if brand_profile else None,
            language_profile=language_profile,
            constraints=_json_loads(concept.risks_json, []),
        )
        version_number = max((item.version_number for item in self.repository.list_prompts(concept_id)), default=0) + 1
        prompt = CreativePrompt(
            id=str(uuid4()),
            concept_id=concept_id,
            target_tool=PackagingPromptTargetTool(target_tool),
            prompt_text=prompt_result.prompt_text,
            negative_guidance=prompt_result.negative_guidance,
            reference_instructions_json=_json_dumps(prompt_result.reference_instructions),
            tool_usage_notes_json=_json_dumps(prompt_result.tool_usage_notes),
            expected_output_notes=prompt_result.expected_output_notes,
            version_number=version_number,
            creator_approval_status="pending",
            created_at=utc_now(),
        )
        stored_prompt = self.repository.upsert_prompt(prompt)
        for reference in prompt_result.reference_package.get("required", []) + prompt_result.reference_package.get("recommended", []) + prompt_result.reference_package.get("optional", []) + prompt_result.reference_package.get("not_recommended", []):
            self.repository.upsert_prompt_reference(
                CreativePromptReference(
                    id=str(uuid4()),
                    prompt_id=stored_prompt.id,
                    reference_asset_id=reference.get("id"),
                    reference_role=str(reference.get("reference_type") or reference.get("reference_purpose") or "reference"),
                    required_level=str(reference.get("required_level") or "optional"),
                    instruction=str(reference.get("instruction") or "Extraccion de principios, no copia literal."),
                    risk_notes=reference.get("risk_notes"),
                    created_at=utc_now(),
                )
            )
        return stored_prompt

    def get_prompt(self, prompt_id: str) -> CreativePrompt | None:
        return self.repository.get_prompt(prompt_id)

    def list_prompts(self, concept_id: str) -> list[CreativePrompt]:
        return self.repository.list_prompts(concept_id)

    def list_prompt_references(self, prompt_id: str) -> list[CreativePromptReference]:
        return self.repository.list_prompt_references(prompt_id)

    def review_thumbnail(self, *, thumbnail_version_id: str, title_version_id: str | None = None, publication_id: str | None = None, concept_id: str | None = None, prompt_id: str | None = None) -> ThumbnailReview:
        thumbnail = self.repository.get_thumbnail_version(thumbnail_version_id)
        if thumbnail is None:
            raise CreativePackagingNotFoundError("La miniatura no existe.")
        asset = self.repository.get_asset(thumbnail.packaging_asset_id)
        title = self.repository.get_title_version(title_version_id) if title_version_id else None
        fallback_titles = self.repository.list_title_versions(thumbnail.packaging_asset_id)
        pair_evaluation = None
        if title_version_id:
            pair_evaluation = self.evaluate_pair(title_version_id=title_version_id, thumbnail_version_id=thumbnail_version_id, publication_id=publication_id)
        elif fallback_titles:
            pair_evaluation = self.evaluate_pair(title_version_id=fallback_titles[0].id, thumbnail_version_id=thumbnail_version_id, publication_id=publication_id)
        concept = self.repository.get_concept(concept_id) if concept_id else None
        prompt = self.repository.get_prompt(prompt_id) if prompt_id else None
        brand_profile = self.repository.get_brand_profile(asset.creator_id) if asset else None
        review_result: ThumbnailReviewResult = build_thumbnail_review_instructions(
            pair_evaluation=pair_evaluation.to_dict() if pair_evaluation else {"warnings": ["missing_pair"], "risks": [], "visual_quality_score": 0, "creator_brand_alignment_score": 0, "content_alignment_score": 0, "audience_fit_score": 0, "platform_fit_score": 0, "historical_fit_score": 0, "promise_alignment_score": 0},
            concept=concept.to_dict() if concept else None,
            prompt=prompt.to_dict() if prompt else None,
            brand_profile=brand_profile.to_dict() if brand_profile else None,
            title=title.title_text if title else None,
            thumbnail=thumbnail.to_dict(),
        )
        review = ThumbnailReview(
            id=str(uuid4()),
            creator_id=asset.creator_id if asset else "",
            thumbnail_version_id=thumbnail_version_id,
            title_version_id=title_version_id,
            publication_id=publication_id,
            review_type="thumbnail_review",
            overall_status=review_result.overall_status,
            visual_quality_json=_json_dumps(review_result.keep),
            content_alignment_json=_json_dumps(review_result.change),
            brand_alignment_json=_json_dumps(review_result.brand_fit),
            audience_fit_json=_json_dumps(review_result.audience_fit),
            platform_fit_json=_json_dumps(review_result.platform_fit),
            historical_fit_json=_json_dumps(review_result.historical_fit),
            niche_fit_json=_json_dumps(review_result.differentiation),
            differentiation_json=_json_dumps(review_result.differentiation),
            strengths_json=_json_dumps(review_result.what_works),
            weaknesses_json=_json_dumps(review_result.what_does_not),
            keep_json=_json_dumps(review_result.keep),
            change_json=_json_dumps(review_result.change),
            risks_json=_json_dumps(review_result.risks),
            final_recommendation=review_result.overall_status,
            confidence_level=review_result.confidence_level,
            created_at=utc_now(),
        )
        return self.repository.upsert_thumbnail_review(review)

    def list_thumbnail_reviews(self, creator_id: str) -> list[ThumbnailReview]:
        return self.repository.list_thumbnail_reviews(creator_id)

    def get_thumbnail_review(self, review_id: str) -> ThumbnailReview | None:
        return self.repository.get_thumbnail_review(review_id)

    def record_decision(
        self,
        *,
        creator_id: str,
        target_type: str,
        target_id: str,
        decision: str,
        reason: str | None = None,
        modified_value_json: str | dict | list | None = None,
    ) -> PackagingDecision:
        record = PackagingDecision(
            id=str(uuid4()),
            creator_id=creator_id,
            target_type=target_type,
            target_id=target_id,
            decision=PackagingDecisionType(decision),
            reason=reason,
            modified_value_json=_json_dumps(modified_value_json) if modified_value_json is not None and not isinstance(modified_value_json, str) else modified_value_json,
            decided_at=utc_now(),
            created_at=utc_now(),
        )
        return self.repository.upsert_decision(record)

    def list_decisions(self, creator_id: str) -> list[PackagingDecision]:
        return self.repository.list_decisions(creator_id)

    def link_experiment(self, *, packaging_asset_id: str, experiment_id: str, assignment_id: str | None = None) -> PackagingExperimentLink:
        link = PackagingExperimentLink(
            id=str(uuid4()),
            packaging_asset_id=packaging_asset_id,
            experiment_id=experiment_id,
            assignment_id=assignment_id,
            created_at=utc_now(),
        )
        return self.repository.upsert_experiment_link(link)

    def list_experiment_links(self, packaging_asset_id: str) -> list[PackagingExperimentLink]:
        return self.repository.list_experiment_links(packaging_asset_id)

    def export(self, *, creator_id: str, format_name: str, summary: bool = False, destination: Path | None = None) -> CreativePackagingExportResult:
        payload = {
            "creator_id": creator_id,
            "assets": [item.to_dict() for item in self.repository.list_assets(creator_id)],
            "references": [item.to_dict() for item in self.repository.list_reference_assets(creator_id)],
            "brand_profiles": [item.to_dict() for item in self.repository.list_brand_profiles(creator_id)],
            "title_versions": [item.to_dict() for asset in self.repository.list_assets(creator_id) for item in self.repository.list_title_versions(asset.id)],
            "thumbnail_versions": [item.to_dict() for asset in self.repository.list_assets(creator_id) for item in self.repository.list_thumbnail_versions(asset.id)],
            "pair_evaluations": [item.to_dict() for item in self.repository.list_pair_evaluations(creator_id)],
            "frame_candidates": [item.to_dict() for item in self.repository.list_frame_candidates(creator_id)],
            "concepts": [item.to_dict() for item in self.repository.list_concepts(creator_id)],
            "prompts": [item.to_dict() for concept in self.repository.list_concepts(creator_id) for item in self.repository.list_prompts(concept.id)],
            "reviews": [item.to_dict() for item in self.repository.list_thumbnail_reviews(creator_id)],
            "decisions": [item.to_dict() for item in self.repository.list_decisions(creator_id)],
            "experiment_links": [link.to_dict() for asset in self.repository.list_assets(creator_id) for link in self.repository.list_experiment_links(asset.id)],
            "summary": summary,
        }
        export_root = destination or self._exports_root
        export_root.mkdir(parents=True, exist_ok=True)
        created_at = utc_now().isoformat()
        if format_name == "json":
            path = export_root / f"{creator_id}_packaging_{'summary' if summary else 'full'}.json"
            content = payload if not summary else {
                "creator_id": creator_id,
                "asset_count": len(payload["assets"]),
                "reference_count": len(payload["references"]),
                "brand_profile_count": len(payload["brand_profiles"]),
                "title_version_count": len(payload["title_versions"]),
                "thumbnail_version_count": len(payload["thumbnail_versions"]),
            }
            path.write_text(_json_dumps(content), encoding="utf-8")
            return CreativePackagingExportResult(creator_id, format_name, str(path), 1, created_at, summary)
        if format_name == "txt":
            path = export_root / f"{creator_id}_packaging_{'summary' if summary else 'full'}.txt"
            lines = [
                f"Creator: {creator_id}",
                f"Assets: {len(payload['assets'])}",
                f"References: {len(payload['references'])}",
                f"Brand profiles: {len(payload['brand_profiles'])}",
                f"Title versions: {len(payload['title_versions'])}",
                f"Thumbnail versions: {len(payload['thumbnail_versions'])}",
                f"Pair evaluations: {len(payload['pair_evaluations'])}",
                f"Concepts: {len(payload['concepts'])}",
                f"Prompts: {len(payload['prompts'])}",
                f"Reviews: {len(payload['reviews'])}",
            ]
            path.write_text("\n".join(lines), encoding="utf-8")
            return CreativePackagingExportResult(creator_id, format_name, str(path), len(lines), created_at, summary)
        if format_name == "csv":
            path = export_root / f"{creator_id}_packaging_{'summary' if summary else 'full'}.csv"
            rows: list[list[object]] = [["section", "item_id", "title", "summary", "platform", "content_type", "status", "notes"]]
            for asset in payload["assets"]:
                rows.append([
                    _sanitize_csv("asset"),
                    _sanitize_csv(asset["id"]),
                    _sanitize_csv(asset["asset_type"]),
                    _sanitize_csv(asset.get("topic") or ""),
                    _sanitize_csv(asset.get("platform") or ""),
                    _sanitize_csv(asset.get("content_type") or ""),
                    _sanitize_csv(asset.get("status") or ""),
                    _sanitize_csv(""),
                ])
            for title in payload["title_versions"]:
                rows.append([
                    _sanitize_csv("title"),
                    _sanitize_csv(title["id"]),
                    _sanitize_csv(title["title_text"]),
                    _sanitize_csv(title.get("creator_feedback") or ""),
                    _sanitize_csv(title.get("platform") or ""),
                    _sanitize_csv(title.get("content_type") or ""),
                    _sanitize_csv(title.get("creator_approval_status") or ""),
                    _sanitize_csv(title.get("source_fingerprint") or ""),
                ])
            for thumbnail in payload["thumbnail_versions"]:
                rows.append([
                    _sanitize_csv("thumbnail"),
                    _sanitize_csv(thumbnail["id"]),
                    _sanitize_csv(thumbnail.get("image_path") or ""),
                    _sanitize_csv(thumbnail.get("creator_feedback") or ""),
                    _sanitize_csv(""),
                    _sanitize_csv(""),
                    _sanitize_csv(thumbnail.get("creator_approval_status") or ""),
                    _sanitize_csv(thumbnail.get("file_fingerprint") or ""),
                ])
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            return CreativePackagingExportResult(creator_id, format_name, str(path), len(rows), created_at, summary)
        raise CreativePackagingValidationError("Formato de exportacion no soportado.")


def build_creative_packaging_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: CreativePackagingRepository,
    database: SQLiteDatabase,
    catalog_service: CatalogService | None = None,
    analytics_repository: SQLiteAnalyticsRepository | None = None,
    creator_memory_service: CreatorMemoryService | None = None,
    creator_language_service: CreatorLanguageService | None = None,
    experiment_service: ExperimentService | None = None,
    logger: logging.Logger | None = None,
) -> CreativePackagingService:
    return CreativePackagingService(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        catalog_service=catalog_service,
        analytics_repository=analytics_repository,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        experiment_service=experiment_service,
        logger=logger,
    )
