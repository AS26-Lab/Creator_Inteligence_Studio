"""Repositorio SQLite para packaging creativo."""

from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from creator_intelligence_studio.domain.creative_packaging.entities import (
    CreativeConcept,
    CreativePrompt,
    CreativePromptReference,
    PackagingAsset,
    PackagingBrandProfile,
    PackagingDecision,
    PackagingExperimentLink,
    PackagingReferenceAsset,
    PackagingPairEvaluation,
    ThumbnailFrameCandidate,
    ThumbnailReview,
    ThumbnailVersion,
    TitleAnalysisMetric,
    TitleAnalysisRun,
    TitleVersion,
    ThumbnailAnalysisMetric,
    ThumbnailAnalysisRun,
)
from creator_intelligence_studio.domain.creative_packaging.repositories import CreativePackagingRepository
from creator_intelligence_studio.domain.creative_packaging.value_objects import (
    PackagingAssetStatus,
    PackagingAssetType,
    PackagingDecisionType,
    PackagingPromptTargetTool,
    PackagingRecommendationStatus,
    PackagingReviewDecision,
    PackagingRunStatus,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


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


def _row_to_asset(row: sqlite3.Row) -> PackagingAsset:
    return PackagingAsset(
        id=row["id"],
        creator_id=row["creator_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        asset_type=PackagingAssetType(row["asset_type"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        status=PackagingAssetStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_title_version(row: sqlite3.Row) -> TitleVersion:
    return TitleVersion(
        id=row["id"],
        packaging_asset_id=row["packaging_asset_id"],
        version_number=row["version_number"],
        title_text=row["title_text"],
        source_type=row["source_type"],
        language=row["language"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        is_published=bool(row["is_published"]),
        is_selected=bool(row["is_selected"]),
        creator_approval_status=row["creator_approval_status"],
        creator_feedback=row["creator_feedback"],
        source_fingerprint=row["source_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_thumbnail_version(row: sqlite3.Row) -> ThumbnailVersion:
    return ThumbnailVersion(
        id=row["id"],
        packaging_asset_id=row["packaging_asset_id"],
        version_number=row["version_number"],
        image_path=row["image_path"],
        source_type=row["source_type"],
        width=row["width"],
        height=row["height"],
        file_fingerprint=row["file_fingerprint"],
        concept_id=row["concept_id"],
        is_published=bool(row["is_published"]),
        is_selected=bool(row["is_selected"]),
        creator_approval_status=row["creator_approval_status"],
        creator_feedback=row["creator_feedback"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_reference_asset(row: sqlite3.Row) -> PackagingReferenceAsset:
    return PackagingReferenceAsset(
        id=row["id"],
        creator_id=row["creator_id"],
        reference_type=row["reference_type"],
        image_path=row["image_path"],
        text_content=row["text_content"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        source_type=row["source_type"],
        source_creator_name=row["source_creator_name"],
        source_url=row["source_url"],
        usage_permission=row["usage_permission"],
        represents_creator=bool(row["represents_creator"]),
        approval_status=row["approval_status"],
        reference_purpose=row["reference_purpose"],
        notes=row["notes"],
        file_fingerprint=row["file_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_brand_profile(row: sqlite3.Row) -> PackagingBrandProfile:
    return PackagingBrandProfile(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_version=row["profile_version"],
        brand_summary=row["brand_summary"],
        visual_identity_json=row["visual_identity_json"],
        preferred_composition_json=row["preferred_composition_json"],
        preferred_palette_json=row["preferred_palette_json"],
        typography_guidance_json=row["typography_guidance_json"],
        subject_guidance_json=row["subject_guidance_json"],
        expression_guidance_json=row["expression_guidance_json"],
        approved_patterns_json=row["approved_patterns_json"],
        rejected_patterns_json=row["rejected_patterns_json"],
        prohibited_elements_json=row["prohibited_elements_json"],
        platform_differences_json=row["platform_differences_json"],
        source_fingerprint=row["source_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_title_run(row: sqlite3.Row) -> TitleAnalysisRun:
    return TitleAnalysisRun(
        id=row["id"],
        creator_id=row["creator_id"],
        title_version_id=row["title_version_id"],
        analyzer_version=row["analyzer_version"],
        status=PackagingRunStatus(row["status"]),
        configuration_json=row["configuration_json"],
        creator_memory_snapshot_id=row["creator_memory_snapshot_id"],
        creator_language_snapshot_id=row["creator_language_snapshot_id"],
        brand_profile_version=row["brand_profile_version"],
        source_fingerprint=row["source_fingerprint"],
        warning_count=row["warning_count"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
    )


def _row_to_title_metric(row: sqlite3.Row) -> TitleAnalysisMetric:
    return TitleAnalysisMetric(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        metric_key=row["metric_key"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        confidence_level=row["confidence_level"],
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_thumbnail_run(row: sqlite3.Row) -> ThumbnailAnalysisRun:
    return ThumbnailAnalysisRun(
        id=row["id"],
        creator_id=row["creator_id"],
        thumbnail_version_id=row["thumbnail_version_id"],
        analyzer_version=row["analyzer_version"],
        status=PackagingRunStatus(row["status"]),
        configuration_json=row["configuration_json"],
        creator_memory_snapshot_id=row["creator_memory_snapshot_id"],
        creator_language_snapshot_id=row["creator_language_snapshot_id"],
        brand_profile_version=row["brand_profile_version"],
        source_fingerprint=row["source_fingerprint"],
        warning_count=row["warning_count"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
    )


def _row_to_thumbnail_metric(row: sqlite3.Row) -> ThumbnailAnalysisMetric:
    return ThumbnailAnalysisMetric(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        metric_key=row["metric_key"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        confidence_level=row["confidence_level"],
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_pair_evaluation(row: sqlite3.Row) -> PackagingPairEvaluation:
    return PackagingPairEvaluation(
        id=row["id"],
        creator_id=row["creator_id"],
        title_version_id=row["title_version_id"],
        thumbnail_version_id=row["thumbnail_version_id"],
        publication_id=row["publication_id"],
        status=PackagingRunStatus(row["status"]),
        visual_quality_score=row["visual_quality_score"],
        content_alignment_score=row["content_alignment_score"],
        creator_brand_alignment_score=row["creator_brand_alignment_score"],
        audience_fit_score=row["audience_fit_score"],
        platform_fit_score=row["platform_fit_score"],
        historical_fit_score=row["historical_fit_score"],
        niche_fit_score=row["niche_fit_score"],
        differentiation_score=row["differentiation_score"],
        clarity_score=row["clarity_score"],
        curiosity_score=row["curiosity_score"],
        hierarchy_score=row["hierarchy_score"],
        complement_score=row["complement_score"],
        authenticity_score=row["authenticity_score"],
        promise_alignment_score=row["promise_alignment_score"],
        evidence_json=row["evidence_json"],
        warnings_json=row["warnings_json"],
        risks_json=row["risks_json"],
        limitations_json=row["limitations_json"],
        recommendation_status=PackagingRecommendationStatus(row["recommendation_status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_frame_candidate(row: sqlite3.Row) -> ThumbnailFrameCandidate:
    return ThumbnailFrameCandidate(
        id=row["id"],
        creator_id=row["creator_id"],
        video_asset_id=row["video_asset_id"],
        timestamp_seconds=row["timestamp_seconds"],
        frame_path=row["frame_path"],
        frame_fingerprint=row["frame_fingerprint"],
        width=row["width"],
        height=row["height"],
        sharpness_score=row["sharpness_score"],
        brightness_score=row["brightness_score"],
        contrast_score=row["contrast_score"],
        face_presence=None if row["face_presence"] is None else bool(row["face_presence"]),
        motion_blur_score=row["motion_blur_score"],
        quality_status=row["quality_status"],
        warning_codes_json=row["warning_codes_json"],
        creator_decision=row["creator_decision"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_concept(row: sqlite3.Row) -> CreativeConcept:
    return CreativeConcept(
        id=row["id"],
        creator_id=row["creator_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        concept_type=row["concept_type"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        title=row["title"],
        premise=row["premise"],
        subject_description=row["subject_description"],
        action_description=row["action_description"],
        composition_description=row["composition_description"],
        emotion_description=row["emotion_description"],
        background_description=row["background_description"],
        color_guidance=row["color_guidance"],
        text_guidance=row["text_guidance"],
        visual_hierarchy=row["visual_hierarchy"],
        relation_to_title=row["relation_to_title"],
        brand_alignment_notes=row["brand_alignment_notes"],
        audience_fit_notes=row["audience_fit_notes"],
        platform_fit_notes=row["platform_fit_notes"],
        differentiation_notes=row["differentiation_notes"],
        authenticity_notes=row["authenticity_notes"],
        risks_json=row["risks_json"],
        reference_requirements_json=row["reference_requirements_json"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_prompt(row: sqlite3.Row) -> CreativePrompt:
    return CreativePrompt(
        id=row["id"],
        concept_id=row["concept_id"],
        target_tool=PackagingPromptTargetTool(row["target_tool"]),
        prompt_text=row["prompt_text"],
        negative_guidance=row["negative_guidance"],
        reference_instructions_json=row["reference_instructions_json"],
        tool_usage_notes_json=row["tool_usage_notes_json"],
        expected_output_notes=row["expected_output_notes"],
        version_number=row["version_number"],
        creator_approval_status=row["creator_approval_status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_prompt_reference(row: sqlite3.Row) -> CreativePromptReference:
    return CreativePromptReference(
        id=row["id"],
        prompt_id=row["prompt_id"],
        reference_asset_id=row["reference_asset_id"],
        reference_role=row["reference_role"],
        required_level=row["required_level"],
        instruction=row["instruction"],
        risk_notes=row["risk_notes"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_review(row: sqlite3.Row) -> ThumbnailReview:
    return ThumbnailReview(
        id=row["id"],
        creator_id=row["creator_id"],
        thumbnail_version_id=row["thumbnail_version_id"],
        title_version_id=row["title_version_id"],
        publication_id=row["publication_id"],
        review_type=row["review_type"],
        overall_status=row["overall_status"],
        visual_quality_json=row["visual_quality_json"],
        content_alignment_json=row["content_alignment_json"],
        brand_alignment_json=row["brand_alignment_json"],
        audience_fit_json=row["audience_fit_json"],
        platform_fit_json=row["platform_fit_json"],
        historical_fit_json=row["historical_fit_json"],
        niche_fit_json=row["niche_fit_json"],
        differentiation_json=row["differentiation_json"],
        strengths_json=row["strengths_json"],
        weaknesses_json=row["weaknesses_json"],
        keep_json=row["keep_json"],
        change_json=row["change_json"],
        risks_json=row["risks_json"],
        final_recommendation=row["final_recommendation"],
        confidence_level=row["confidence_level"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_decision(row: sqlite3.Row) -> PackagingDecision:
    return PackagingDecision(
        id=row["id"],
        creator_id=row["creator_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        decision=PackagingDecisionType(row["decision"]),
        reason=row["reason"],
        modified_value_json=row["modified_value_json"],
        decided_at=from_iso_z(row["decided_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_link(row: sqlite3.Row) -> PackagingExperimentLink:
    return PackagingExperimentLink(
        id=row["id"],
        packaging_asset_id=row["packaging_asset_id"],
        experiment_id=row["experiment_id"],
        assignment_id=row["assignment_id"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteCreativePackagingRepository(CreativePackagingRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchall()

    def upsert_asset(self, asset: PackagingAsset) -> PackagingAsset:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO packaging_assets (
                    id, creator_id, publication_id, video_asset_id, asset_type, platform,
                    content_type, topic, status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :publication_id, :video_asset_id, :asset_type, :platform,
                    :content_type, :topic, :status, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    publication_id = excluded.publication_id,
                    video_asset_id = excluded.video_asset_id,
                    asset_type = excluded.asset_type,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                asset.to_dict() | {"asset_type": asset.asset_type.value, "status": asset.status.value},
            )
        row = self._fetch_one("SELECT * FROM packaging_assets WHERE id = ?", (asset.id,))
        return _row_to_asset(row)

    def get_asset(self, asset_id: str) -> PackagingAsset | None:
        row = self._fetch_one("SELECT * FROM packaging_assets WHERE id = ?", (asset_id,))
        return _row_to_asset(row) if row else None

    def list_assets(self, creator_id: str) -> list[PackagingAsset]:
        rows = self._fetch_all("SELECT * FROM packaging_assets WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_asset(row) for row in rows]

    def upsert_title_version(self, title: TitleVersion) -> TitleVersion:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO title_versions (
                    id, packaging_asset_id, version_number, title_text, source_type, language,
                    platform, content_type, topic, is_published, is_selected,
                    creator_approval_status, creator_feedback, source_fingerprint,
                    created_at, updated_at
                ) VALUES (
                    :id, :packaging_asset_id, :version_number, :title_text, :source_type, :language,
                    :platform, :content_type, :topic, :is_published, :is_selected,
                    :creator_approval_status, :creator_feedback, :source_fingerprint,
                    :created_at, :updated_at
                )
                ON CONFLICT(packaging_asset_id, version_number) DO UPDATE SET
                    title_text = excluded.title_text,
                    source_type = excluded.source_type,
                    language = excluded.language,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    is_published = excluded.is_published,
                    is_selected = excluded.is_selected,
                    creator_approval_status = excluded.creator_approval_status,
                    creator_feedback = excluded.creator_feedback,
                    source_fingerprint = excluded.source_fingerprint,
                    updated_at = excluded.updated_at
                """,
                title.to_dict() | {
                    "creator_approval_status": title.creator_approval_status,
                    "is_published": 1 if title.is_published else 0,
                    "is_selected": 1 if title.is_selected else 0,
                },
            )
        row = self._fetch_one(
            "SELECT * FROM title_versions WHERE packaging_asset_id = ? AND version_number = ?",
            (title.packaging_asset_id, title.version_number),
        )
        return _row_to_title_version(row)

    def get_title_version(self, title_version_id: str) -> TitleVersion | None:
        row = self._fetch_one("SELECT * FROM title_versions WHERE id = ?", (title_version_id,))
        return _row_to_title_version(row) if row else None

    def list_title_versions(self, packaging_asset_id: str) -> list[TitleVersion]:
        rows = self._fetch_all("SELECT * FROM title_versions WHERE packaging_asset_id = ? ORDER BY version_number DESC, created_at DESC", (packaging_asset_id,))
        return [_row_to_title_version(row) for row in rows]

    def upsert_thumbnail_version(self, thumbnail: ThumbnailVersion) -> ThumbnailVersion:
        existing = self._fetch_one(
            "SELECT * FROM thumbnail_versions WHERE packaging_asset_id = ? AND file_fingerprint = ?",
            (thumbnail.packaging_asset_id, thumbnail.file_fingerprint),
        )
        if existing is not None:
            return _row_to_thumbnail_version(existing)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO thumbnail_versions (
                    id, packaging_asset_id, version_number, image_path, source_type, width,
                    height, file_fingerprint, concept_id, is_published, is_selected,
                    creator_approval_status, creator_feedback, created_at, updated_at
                ) VALUES (
                    :id, :packaging_asset_id, :version_number, :image_path, :source_type, :width,
                    :height, :file_fingerprint, :concept_id, :is_published, :is_selected,
                    :creator_approval_status, :creator_feedback, :created_at, :updated_at
                )
                ON CONFLICT(packaging_asset_id, version_number) DO UPDATE SET
                    image_path = excluded.image_path,
                    source_type = excluded.source_type,
                    width = excluded.width,
                    height = excluded.height,
                    file_fingerprint = excluded.file_fingerprint,
                    concept_id = excluded.concept_id,
                    is_published = excluded.is_published,
                    is_selected = excluded.is_selected,
                    creator_approval_status = excluded.creator_approval_status,
                    creator_feedback = excluded.creator_feedback,
                    updated_at = excluded.updated_at
                """,
                thumbnail.to_dict() | {
                    "creator_approval_status": thumbnail.creator_approval_status,
                    "is_published": 1 if thumbnail.is_published else 0,
                    "is_selected": 1 if thumbnail.is_selected else 0,
                },
            )
        row = self._fetch_one(
            "SELECT * FROM thumbnail_versions WHERE packaging_asset_id = ? AND version_number = ?",
            (thumbnail.packaging_asset_id, thumbnail.version_number),
        )
        return _row_to_thumbnail_version(row)

    def get_thumbnail_version(self, thumbnail_version_id: str) -> ThumbnailVersion | None:
        row = self._fetch_one("SELECT * FROM thumbnail_versions WHERE id = ?", (thumbnail_version_id,))
        return _row_to_thumbnail_version(row) if row else None

    def list_thumbnail_versions(self, packaging_asset_id: str) -> list[ThumbnailVersion]:
        rows = self._fetch_all("SELECT * FROM thumbnail_versions WHERE packaging_asset_id = ? ORDER BY version_number DESC, created_at DESC", (packaging_asset_id,))
        return [_row_to_thumbnail_version(row) for row in rows]

    def upsert_reference_asset(self, reference: PackagingReferenceAsset) -> PackagingReferenceAsset:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO packaging_reference_assets (
                    id, creator_id, reference_type, image_path, text_content, platform,
                    content_type, topic, source_type, source_creator_name, source_url,
                    usage_permission, represents_creator, approval_status, reference_purpose,
                    notes, file_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :reference_type, :image_path, :text_content, :platform,
                    :content_type, :topic, :source_type, :source_creator_name, :source_url,
                    :usage_permission, :represents_creator, :approval_status, :reference_purpose,
                    :notes, :file_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    image_path = excluded.image_path,
                    text_content = excluded.text_content,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    source_type = excluded.source_type,
                    source_creator_name = excluded.source_creator_name,
                    source_url = excluded.source_url,
                    usage_permission = excluded.usage_permission,
                    represents_creator = excluded.represents_creator,
                    approval_status = excluded.approval_status,
                    reference_purpose = excluded.reference_purpose,
                    notes = excluded.notes,
                    file_fingerprint = excluded.file_fingerprint,
                    updated_at = excluded.updated_at
                """,
                {**reference.to_dict(), "represents_creator": 1 if reference.represents_creator else 0},
            )
        row = self._fetch_one("SELECT * FROM packaging_reference_assets WHERE id = ?", (reference.id,))
        return _row_to_reference_asset(row)

    def get_reference_asset(self, reference_id: str) -> PackagingReferenceAsset | None:
        row = self._fetch_one("SELECT * FROM packaging_reference_assets WHERE id = ?", (reference_id,))
        return _row_to_reference_asset(row) if row else None

    def list_reference_assets(self, creator_id: str) -> list[PackagingReferenceAsset]:
        rows = self._fetch_all("SELECT * FROM packaging_reference_assets WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,))
        return [_row_to_reference_asset(row) for row in rows]

    def upsert_brand_profile(self, profile: PackagingBrandProfile) -> PackagingBrandProfile:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO packaging_brand_profiles (
                    id, creator_id, profile_version, brand_summary, visual_identity_json,
                    preferred_composition_json, preferred_palette_json, typography_guidance_json,
                    subject_guidance_json, expression_guidance_json, approved_patterns_json,
                    rejected_patterns_json, prohibited_elements_json, platform_differences_json,
                    source_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :profile_version, :brand_summary, :visual_identity_json,
                    :preferred_composition_json, :preferred_palette_json, :typography_guidance_json,
                    :subject_guidance_json, :expression_guidance_json, :approved_patterns_json,
                    :rejected_patterns_json, :prohibited_elements_json, :platform_differences_json,
                    :source_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, profile_version) DO UPDATE SET
                    brand_summary = excluded.brand_summary,
                    visual_identity_json = excluded.visual_identity_json,
                    preferred_composition_json = excluded.preferred_composition_json,
                    preferred_palette_json = excluded.preferred_palette_json,
                    typography_guidance_json = excluded.typography_guidance_json,
                    subject_guidance_json = excluded.subject_guidance_json,
                    expression_guidance_json = excluded.expression_guidance_json,
                    approved_patterns_json = excluded.approved_patterns_json,
                    rejected_patterns_json = excluded.rejected_patterns_json,
                    prohibited_elements_json = excluded.prohibited_elements_json,
                    platform_differences_json = excluded.platform_differences_json,
                    source_fingerprint = excluded.source_fingerprint,
                    updated_at = excluded.updated_at
                """,
                profile.to_dict(),
            )
        row = self._fetch_one(
            "SELECT * FROM packaging_brand_profiles WHERE creator_id = ? AND profile_version = ?",
            (profile.creator_id, profile.profile_version),
        )
        return _row_to_brand_profile(row)

    def get_brand_profile(self, creator_id: str) -> PackagingBrandProfile | None:
        row = self._fetch_one("SELECT * FROM packaging_brand_profiles WHERE creator_id = ? ORDER BY profile_version DESC LIMIT 1", (creator_id,))
        return _row_to_brand_profile(row) if row else None

    def list_brand_profiles(self, creator_id: str) -> list[PackagingBrandProfile]:
        rows = self._fetch_all("SELECT * FROM packaging_brand_profiles WHERE creator_id = ? ORDER BY profile_version DESC", (creator_id,))
        return [_row_to_brand_profile(row) for row in rows]

    def upsert_title_analysis_run(self, run: TitleAnalysisRun) -> TitleAnalysisRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO title_analysis_runs (
                    id, creator_id, title_version_id, analyzer_version, status,
                    configuration_json, creator_memory_snapshot_id, creator_language_snapshot_id,
                    brand_profile_version, source_fingerprint, warning_count, created_at, completed_at
                ) VALUES (
                    :id, :creator_id, :title_version_id, :analyzer_version, :status,
                    :configuration_json, :creator_memory_snapshot_id, :creator_language_snapshot_id,
                    :brand_profile_version, :source_fingerprint, :warning_count, :created_at, :completed_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    creator_memory_snapshot_id = excluded.creator_memory_snapshot_id,
                    creator_language_snapshot_id = excluded.creator_language_snapshot_id,
                    brand_profile_version = excluded.brand_profile_version,
                    source_fingerprint = excluded.source_fingerprint,
                    warning_count = excluded.warning_count,
                    completed_at = excluded.completed_at
                """,
                {**run.to_dict(), "status": run.status.value},
            )
        row = self._fetch_one("SELECT * FROM title_analysis_runs WHERE id = ?", (run.id,))
        return _row_to_title_run(row)

    def get_title_analysis_run(self, run_id: str) -> TitleAnalysisRun | None:
        row = self._fetch_one("SELECT * FROM title_analysis_runs WHERE id = ?", (run_id,))
        return _row_to_title_run(row) if row else None

    def list_title_analysis_runs(self, creator_id: str) -> list[TitleAnalysisRun]:
        rows = self._fetch_all("SELECT * FROM title_analysis_runs WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_title_run(row) for row in rows]

    def upsert_title_analysis_metric(self, metric: TitleAnalysisMetric) -> TitleAnalysisMetric:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO title_analysis_metrics (
                    id, analysis_run_id, metric_key, numeric_value, text_value,
                    unit, confidence_level, warning_codes_json, created_at
                ) VALUES (
                    :id, :analysis_run_id, :metric_key, :numeric_value, :text_value,
                    :unit, :confidence_level, :warning_codes_json, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    confidence_level = excluded.confidence_level,
                    warning_codes_json = excluded.warning_codes_json
                """,
                metric.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM title_analysis_metrics WHERE id = ?", (metric.id,))
        return _row_to_title_metric(row)

    def list_title_analysis_metrics(self, run_id: str) -> list[TitleAnalysisMetric]:
        rows = self._fetch_all("SELECT * FROM title_analysis_metrics WHERE analysis_run_id = ? ORDER BY created_at ASC", (run_id,))
        return [_row_to_title_metric(row) for row in rows]

    def upsert_thumbnail_analysis_run(self, run: ThumbnailAnalysisRun) -> ThumbnailAnalysisRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO thumbnail_analysis_runs (
                    id, creator_id, thumbnail_version_id, analyzer_version, status,
                    configuration_json, creator_memory_snapshot_id, creator_language_snapshot_id,
                    brand_profile_version, source_fingerprint, warning_count, created_at, completed_at
                ) VALUES (
                    :id, :creator_id, :thumbnail_version_id, :analyzer_version, :status,
                    :configuration_json, :creator_memory_snapshot_id, :creator_language_snapshot_id,
                    :brand_profile_version, :source_fingerprint, :warning_count, :created_at, :completed_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    creator_memory_snapshot_id = excluded.creator_memory_snapshot_id,
                    creator_language_snapshot_id = excluded.creator_language_snapshot_id,
                    brand_profile_version = excluded.brand_profile_version,
                    source_fingerprint = excluded.source_fingerprint,
                    warning_count = excluded.warning_count,
                    completed_at = excluded.completed_at
                """,
                {**run.to_dict(), "status": run.status.value},
            )
        row = self._fetch_one("SELECT * FROM thumbnail_analysis_runs WHERE id = ?", (run.id,))
        return _row_to_thumbnail_run(row)

    def get_thumbnail_analysis_run(self, run_id: str) -> ThumbnailAnalysisRun | None:
        row = self._fetch_one("SELECT * FROM thumbnail_analysis_runs WHERE id = ?", (run_id,))
        return _row_to_thumbnail_run(row) if row else None

    def list_thumbnail_analysis_runs(self, creator_id: str) -> list[ThumbnailAnalysisRun]:
        rows = self._fetch_all("SELECT * FROM thumbnail_analysis_runs WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_thumbnail_run(row) for row in rows]

    def upsert_thumbnail_analysis_metric(self, metric: ThumbnailAnalysisMetric) -> ThumbnailAnalysisMetric:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO thumbnail_analysis_metrics (
                    id, analysis_run_id, metric_key, numeric_value, text_value,
                    unit, confidence_level, warning_codes_json, created_at
                ) VALUES (
                    :id, :analysis_run_id, :metric_key, :numeric_value, :text_value,
                    :unit, :confidence_level, :warning_codes_json, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    confidence_level = excluded.confidence_level,
                    warning_codes_json = excluded.warning_codes_json
                """,
                metric.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM thumbnail_analysis_metrics WHERE id = ?", (metric.id,))
        return _row_to_thumbnail_metric(row)

    def list_thumbnail_analysis_metrics(self, run_id: str) -> list[ThumbnailAnalysisMetric]:
        rows = self._fetch_all("SELECT * FROM thumbnail_analysis_metrics WHERE analysis_run_id = ? ORDER BY created_at ASC", (run_id,))
        return [_row_to_thumbnail_metric(row) for row in rows]

    def upsert_pair_evaluation(self, evaluation: PackagingPairEvaluation) -> PackagingPairEvaluation:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO packaging_pair_evaluations (
                    id, creator_id, title_version_id, thumbnail_version_id, publication_id, status,
                    visual_quality_score, content_alignment_score, creator_brand_alignment_score,
                    audience_fit_score, platform_fit_score, historical_fit_score, niche_fit_score,
                    differentiation_score, clarity_score, curiosity_score, hierarchy_score,
                    complement_score, authenticity_score, promise_alignment_score, evidence_json,
                    warnings_json, risks_json, limitations_json, recommendation_status, created_at
                ) VALUES (
                    :id, :creator_id, :title_version_id, :thumbnail_version_id, :publication_id, :status,
                    :visual_quality_score, :content_alignment_score, :creator_brand_alignment_score,
                    :audience_fit_score, :platform_fit_score, :historical_fit_score, :niche_fit_score,
                    :differentiation_score, :clarity_score, :curiosity_score, :hierarchy_score,
                    :complement_score, :authenticity_score, :promise_alignment_score, :evidence_json,
                    :warnings_json, :risks_json, :limitations_json, :recommendation_status, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    visual_quality_score = excluded.visual_quality_score,
                    content_alignment_score = excluded.content_alignment_score,
                    creator_brand_alignment_score = excluded.creator_brand_alignment_score,
                    audience_fit_score = excluded.audience_fit_score,
                    platform_fit_score = excluded.platform_fit_score,
                    historical_fit_score = excluded.historical_fit_score,
                    niche_fit_score = excluded.niche_fit_score,
                    differentiation_score = excluded.differentiation_score,
                    clarity_score = excluded.clarity_score,
                    curiosity_score = excluded.curiosity_score,
                    hierarchy_score = excluded.hierarchy_score,
                    complement_score = excluded.complement_score,
                    authenticity_score = excluded.authenticity_score,
                    promise_alignment_score = excluded.promise_alignment_score,
                    evidence_json = excluded.evidence_json,
                    warnings_json = excluded.warnings_json,
                    risks_json = excluded.risks_json,
                    limitations_json = excluded.limitations_json,
                    recommendation_status = excluded.recommendation_status
                """,
                evaluation.to_dict() | {"status": evaluation.status.value, "recommendation_status": evaluation.recommendation_status.value},
            )
        row = self._fetch_one("SELECT * FROM packaging_pair_evaluations WHERE id = ?", (evaluation.id,))
        return _row_to_pair_evaluation(row)

    def get_pair_evaluation(self, evaluation_id: str) -> PackagingPairEvaluation | None:
        row = self._fetch_one("SELECT * FROM packaging_pair_evaluations WHERE id = ?", (evaluation_id,))
        return _row_to_pair_evaluation(row) if row else None

    def list_pair_evaluations(self, creator_id: str) -> list[PackagingPairEvaluation]:
        rows = self._fetch_all("SELECT * FROM packaging_pair_evaluations WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_pair_evaluation(row) for row in rows]

    def upsert_frame_candidate(self, candidate: ThumbnailFrameCandidate) -> ThumbnailFrameCandidate:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO thumbnail_frame_candidates (
                    id, creator_id, video_asset_id, timestamp_seconds, frame_path, frame_fingerprint,
                    width, height, sharpness_score, brightness_score, contrast_score, face_presence,
                    motion_blur_score, quality_status, warning_codes_json, creator_decision, created_at
                ) VALUES (
                    :id, :creator_id, :video_asset_id, :timestamp_seconds, :frame_path, :frame_fingerprint,
                    :width, :height, :sharpness_score, :brightness_score, :contrast_score, :face_presence,
                    :motion_blur_score, :quality_status, :warning_codes_json, :creator_decision, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    frame_path = excluded.frame_path,
                    frame_fingerprint = excluded.frame_fingerprint,
                    width = excluded.width,
                    height = excluded.height,
                    sharpness_score = excluded.sharpness_score,
                    brightness_score = excluded.brightness_score,
                    contrast_score = excluded.contrast_score,
                    face_presence = excluded.face_presence,
                    motion_blur_score = excluded.motion_blur_score,
                    quality_status = excluded.quality_status,
                    warning_codes_json = excluded.warning_codes_json,
                    creator_decision = excluded.creator_decision
                """,
                candidate.to_dict() | {"face_presence": None if candidate.face_presence is None else 1 if candidate.face_presence else 0},
            )
        row = self._fetch_one("SELECT * FROM thumbnail_frame_candidates WHERE id = ?", (candidate.id,))
        return _row_to_frame_candidate(row)

    def list_frame_candidates(self, creator_id: str, video_asset_id: str | None = None) -> list[ThumbnailFrameCandidate]:
        query = "SELECT * FROM thumbnail_frame_candidates WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if video_asset_id:
            query += " AND video_asset_id = ?"
            params.append(video_asset_id)
        query += " ORDER BY timestamp_seconds ASC"
        rows = self._fetch_all(query, tuple(params))
        return [_row_to_frame_candidate(row) for row in rows]

    def upsert_concept(self, concept: CreativeConcept) -> CreativeConcept:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creative_concepts (
                    id, creator_id, publication_id, video_asset_id, concept_type, platform,
                    content_type, topic, title, premise, subject_description, action_description,
                    composition_description, emotion_description, background_description, color_guidance,
                    text_guidance, visual_hierarchy, relation_to_title, brand_alignment_notes,
                    audience_fit_notes, platform_fit_notes, differentiation_notes, authenticity_notes,
                    risks_json, reference_requirements_json, status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :publication_id, :video_asset_id, :concept_type, :platform,
                    :content_type, :topic, :title, :premise, :subject_description, :action_description,
                    :composition_description, :emotion_description, :background_description, :color_guidance,
                    :text_guidance, :visual_hierarchy, :relation_to_title, :brand_alignment_notes,
                    :audience_fit_notes, :platform_fit_notes, :differentiation_notes, :authenticity_notes,
                    :risks_json, :reference_requirements_json, :status, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    premise = excluded.premise,
                    subject_description = excluded.subject_description,
                    action_description = excluded.action_description,
                    composition_description = excluded.composition_description,
                    emotion_description = excluded.emotion_description,
                    background_description = excluded.background_description,
                    color_guidance = excluded.color_guidance,
                    text_guidance = excluded.text_guidance,
                    visual_hierarchy = excluded.visual_hierarchy,
                    relation_to_title = excluded.relation_to_title,
                    brand_alignment_notes = excluded.brand_alignment_notes,
                    audience_fit_notes = excluded.audience_fit_notes,
                    platform_fit_notes = excluded.platform_fit_notes,
                    differentiation_notes = excluded.differentiation_notes,
                    authenticity_notes = excluded.authenticity_notes,
                    risks_json = excluded.risks_json,
                    reference_requirements_json = excluded.reference_requirements_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                concept.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM creative_concepts WHERE id = ?", (concept.id,))
        return _row_to_concept(row)

    def get_concept(self, concept_id: str) -> CreativeConcept | None:
        row = self._fetch_one("SELECT * FROM creative_concepts WHERE id = ?", (concept_id,))
        return _row_to_concept(row) if row else None

    def list_concepts(self, creator_id: str) -> list[CreativeConcept]:
        rows = self._fetch_all("SELECT * FROM creative_concepts WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_concept(row) for row in rows]

    def upsert_prompt(self, prompt: CreativePrompt) -> CreativePrompt:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creative_prompts (
                    id, concept_id, target_tool, prompt_text, negative_guidance,
                    reference_instructions_json, tool_usage_notes_json, expected_output_notes,
                    version_number, creator_approval_status, created_at
                ) VALUES (
                    :id, :concept_id, :target_tool, :prompt_text, :negative_guidance,
                    :reference_instructions_json, :tool_usage_notes_json, :expected_output_notes,
                    :version_number, :creator_approval_status, :created_at
                )
                ON CONFLICT(concept_id, version_number) DO UPDATE SET
                    prompt_text = excluded.prompt_text,
                    negative_guidance = excluded.negative_guidance,
                    reference_instructions_json = excluded.reference_instructions_json,
                    tool_usage_notes_json = excluded.tool_usage_notes_json,
                    expected_output_notes = excluded.expected_output_notes,
                    creator_approval_status = excluded.creator_approval_status
                """,
                prompt.to_dict() | {"target_tool": prompt.target_tool.value},
            )
        row = self._fetch_one("SELECT * FROM creative_prompts WHERE concept_id = ? AND version_number = ?", (prompt.concept_id, prompt.version_number))
        return _row_to_prompt(row)

    def get_prompt(self, prompt_id: str) -> CreativePrompt | None:
        row = self._fetch_one("SELECT * FROM creative_prompts WHERE id = ?", (prompt_id,))
        return _row_to_prompt(row) if row else None

    def list_prompts(self, concept_id: str) -> list[CreativePrompt]:
        rows = self._fetch_all("SELECT * FROM creative_prompts WHERE concept_id = ? ORDER BY version_number DESC", (concept_id,))
        return [_row_to_prompt(row) for row in rows]

    def upsert_prompt_reference(self, reference: CreativePromptReference) -> CreativePromptReference:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creative_prompt_references (
                    id, prompt_id, reference_asset_id, reference_role, required_level,
                    instruction, risk_notes, created_at
                ) VALUES (
                    :id, :prompt_id, :reference_asset_id, :reference_role, :required_level,
                    :instruction, :risk_notes, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    reference_asset_id = excluded.reference_asset_id,
                    reference_role = excluded.reference_role,
                    required_level = excluded.required_level,
                    instruction = excluded.instruction,
                    risk_notes = excluded.risk_notes
                """,
                reference.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM creative_prompt_references WHERE id = ?", (reference.id,))
        return _row_to_prompt_reference(row)

    def list_prompt_references(self, prompt_id: str) -> list[CreativePromptReference]:
        rows = self._fetch_all("SELECT * FROM creative_prompt_references WHERE prompt_id = ? ORDER BY created_at ASC", (prompt_id,))
        return [_row_to_prompt_reference(row) for row in rows]

    def upsert_thumbnail_review(self, review: ThumbnailReview) -> ThumbnailReview:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO thumbnail_reviews (
                    id, creator_id, thumbnail_version_id, title_version_id, publication_id, review_type,
                    overall_status, visual_quality_json, content_alignment_json, brand_alignment_json,
                    audience_fit_json, platform_fit_json, historical_fit_json, niche_fit_json,
                    differentiation_json, strengths_json, weaknesses_json, keep_json, change_json,
                    risks_json, final_recommendation, confidence_level, created_at
                ) VALUES (
                    :id, :creator_id, :thumbnail_version_id, :title_version_id, :publication_id, :review_type,
                    :overall_status, :visual_quality_json, :content_alignment_json, :brand_alignment_json,
                    :audience_fit_json, :platform_fit_json, :historical_fit_json, :niche_fit_json,
                    :differentiation_json, :strengths_json, :weaknesses_json, :keep_json, :change_json,
                    :risks_json, :final_recommendation, :confidence_level, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    overall_status = excluded.overall_status,
                    visual_quality_json = excluded.visual_quality_json,
                    content_alignment_json = excluded.content_alignment_json,
                    brand_alignment_json = excluded.brand_alignment_json,
                    audience_fit_json = excluded.audience_fit_json,
                    platform_fit_json = excluded.platform_fit_json,
                    historical_fit_json = excluded.historical_fit_json,
                    niche_fit_json = excluded.niche_fit_json,
                    differentiation_json = excluded.differentiation_json,
                    strengths_json = excluded.strengths_json,
                    weaknesses_json = excluded.weaknesses_json,
                    keep_json = excluded.keep_json,
                    change_json = excluded.change_json,
                    risks_json = excluded.risks_json,
                    final_recommendation = excluded.final_recommendation,
                    confidence_level = excluded.confidence_level
                """,
                review.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM thumbnail_reviews WHERE id = ?", (review.id,))
        return _row_to_review(row)

    def get_thumbnail_review(self, review_id: str) -> ThumbnailReview | None:
        row = self._fetch_one("SELECT * FROM thumbnail_reviews WHERE id = ?", (review_id,))
        return _row_to_review(row) if row else None

    def list_thumbnail_reviews(self, creator_id: str) -> list[ThumbnailReview]:
        rows = self._fetch_all("SELECT * FROM thumbnail_reviews WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_review(row) for row in rows]

    def upsert_decision(self, decision: PackagingDecision) -> PackagingDecision:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO packaging_decisions (
                    id, creator_id, target_type, target_id, decision, reason,
                    modified_value_json, decided_at, created_at
                ) VALUES (
                    :id, :creator_id, :target_type, :target_id, :decision, :reason,
                    :modified_value_json, :decided_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    reason = excluded.reason,
                    modified_value_json = excluded.modified_value_json,
                    decided_at = excluded.decided_at
                """,
                decision.to_dict() | {"decision": decision.decision.value},
            )
        row = self._fetch_one("SELECT * FROM packaging_decisions WHERE id = ?", (decision.id,))
        return _row_to_decision(row)

    def list_decisions(self, creator_id: str) -> list[PackagingDecision]:
        rows = self._fetch_all("SELECT * FROM packaging_decisions WHERE creator_id = ? ORDER BY decided_at DESC", (creator_id,))
        return [_row_to_decision(row) for row in rows]

    def upsert_experiment_link(self, link: PackagingExperimentLink) -> PackagingExperimentLink:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO packaging_experiment_links (
                    id, packaging_asset_id, experiment_id, assignment_id, created_at
                ) VALUES (
                    :id, :packaging_asset_id, :experiment_id, :assignment_id, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    assignment_id = excluded.assignment_id
                """,
                link.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM packaging_experiment_links WHERE id = ?", (link.id,))
        return _row_to_link(row)

    def list_experiment_links(self, packaging_asset_id: str) -> list[PackagingExperimentLink]:
        rows = self._fetch_all("SELECT * FROM packaging_experiment_links WHERE packaging_asset_id = ? ORDER BY created_at DESC", (packaging_asset_id,))
        return [_row_to_link(row) for row in rows]
