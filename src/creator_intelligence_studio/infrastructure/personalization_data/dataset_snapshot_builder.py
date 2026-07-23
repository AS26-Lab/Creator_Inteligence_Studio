"""Utilidades para construir snapshots de datasets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from creator_intelligence_studio.domain.personalization_data.entities import CreatorDatasetExample, CreatorDatasetSnapshot
from creator_intelligence_studio.domain.personalization_data.value_objects import (
    PersonalizationDatasetOptions,
    PersonalizationDatasetStatus,
    PersonalizationLabel,
    PersonalizationReadinessStatus,
)
from creator_intelligence_studio.shared.dates import utc_now


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_snapshot_name(creator_id: str, project_id: str | None) -> str:
    return f"dataset-{creator_id}" + (f"-{project_id}" if project_id else "")


def build_snapshot_version(latest_version: str | None, options: PersonalizationDatasetOptions) -> str:
    if latest_version is None:
        return f"{options.dataset_version_prefix}-1"
    prefix, _, suffix = latest_version.partition("-")
    if not suffix.isdigit():
        return f"{options.dataset_version_prefix}-1"
    return f"{prefix}-{int(suffix) + 1}"


def build_snapshot_group_key(video_id: str, ranking_run_id: str | None) -> str:
    return f"{video_id}:{ranking_run_id or 'no-run'}"


def build_snapshot_source_payload(
    *,
    creator_id: str,
    project_id: str | None,
    options: PersonalizationDatasetOptions,
    examples: list[CreatorDatasetExample],
    videos: list[str],
) -> dict[str, object]:
    return {
        "creator_id": creator_id,
        "project_id": project_id,
        "options": options.to_dict(),
        "video_ids": sorted(videos),
        "example_signatures": [
            {
                "id": example.id,
                "video_asset_id": example.video_asset_id,
                "candidate_id": example.ranked_clip_candidate_id,
                "start_seconds": example.start_seconds,
                "end_seconds": example.end_seconds,
                "label": example.label.value,
                "split": example.split_name.value,
                "feature_hash": hashlib.sha256(_json_dumps(example.feature_vector).encode("utf-8")).hexdigest(),
            }
            for example in sorted(examples, key=lambda item: (item.video_asset_id, item.start_seconds, item.end_seconds, item.id))
        ],
    }


def build_empty_snapshot(
    *,
    creator_id: str,
    project_id: str | None,
    options: PersonalizationDatasetOptions,
    source_fingerprint: str,
    configuration_fingerprint: str,
) -> CreatorDatasetSnapshot:
    now = utc_now()
    return CreatorDatasetSnapshot(
        id="",
        creator_id=creator_id,
        project_id=project_id,
        name=build_snapshot_name(creator_id, project_id),
        status=PersonalizationDatasetStatus.BUILDING,
        dataset_version=f"{options.dataset_version_prefix}-1",
        feature_schema_version=options.feature_schema_version,
        label_schema_version=options.label_schema_version,
        source_fingerprint=source_fingerprint,
        configuration_fingerprint=configuration_fingerprint,
        example_count=0,
        positive_count=0,
        negative_count=0,
        neutral_count=0,
        excluded_count=0,
        conflict_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
        readiness_status=PersonalizationReadinessStatus.NOT_READY,
        readiness_score=0.0,
        started_at=now,
        completed_at=now,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
