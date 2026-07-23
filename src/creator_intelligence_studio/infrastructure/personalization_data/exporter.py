"""Exportacion de snapshots de personalizacion."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from creator_intelligence_studio.domain.personalization_data.entities import (
    CreatorDatasetConflict,
    CreatorDatasetExample,
    CreatorDatasetQualityReport,
    CreatorDatasetSnapshot,
    CreatorFeatureSchema,
)
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetOptions


def _json_default(value):
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def export_dataset_json(
    *,
    snapshot: CreatorDatasetSnapshot,
    feature_schema: CreatorFeatureSchema,
    examples: list[CreatorDatasetExample],
    conflicts: list[CreatorDatasetConflict],
    quality_report: CreatorDatasetQualityReport,
    options: PersonalizationDatasetOptions,
    include_sensitive: bool = False,
) -> str:
    payload = {
        "snapshot": snapshot.to_dict(),
        "feature_schema": feature_schema.to_dict(),
        "examples": [example.to_dict() for example in examples],
        "conflicts": [conflict.to_dict() for conflict in conflicts],
        "quality_report": quality_report.to_dict(),
        "options": options.to_dict(),
    }
    if not include_sensitive:
        for example in payload["examples"]:
            example.pop("human_tags", None)
    return json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)


def export_dataset_csv(
    *,
    snapshot: CreatorDatasetSnapshot,
    feature_schema: CreatorFeatureSchema,
    examples: list[CreatorDatasetExample],
    include_sensitive: bool = False,
) -> str:
    buffer = io.StringIO()
    fieldnames = [
        "id",
        "snapshot_id",
        "creator_id",
        "video_asset_id",
        "ranking_run_id",
        "ranked_clip_candidate_id",
        "multimodal_candidate_id",
        "group_key",
        "start_seconds",
        "end_seconds",
        "duration_seconds",
        "label",
        "label_source",
        "label_confidence",
        "human_review_status",
        "human_rating",
        "split_name",
        "sample_weight",
        "exclusion_reason",
    ] + list(feature_schema.feature_names)
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for example in examples:
        row = example.to_dict()
        row["label_source"] = "|".join(example.label_source)
        row["human_tags"] = "|".join(example.human_tags)
        if not include_sensitive:
            row.pop("human_tags", None)
        for feature_name in feature_schema.feature_names:
            row[feature_name] = example.feature_vector.get(feature_name)
        writer.writerow(row)
    return buffer.getvalue()


def export_dataset_jsonl(
    *,
    snapshot: CreatorDatasetSnapshot,
    feature_schema: CreatorFeatureSchema,
    examples: list[CreatorDatasetExample],
    include_sensitive: bool = False,
) -> str:
    lines: list[str] = []
    for example in examples:
        payload = {
            "snapshot_id": snapshot.id,
            "creator_id": snapshot.creator_id,
            "project_id": snapshot.project_id,
            "feature_schema_version": feature_schema.schema_version,
            "label_schema_version": snapshot.label_schema_version,
            "group_key": example.group_key,
            "split_name": example.split_name.value,
            "label": example.label.value,
            "sample_weight": example.sample_weight,
            "quality_flags": dict(example.quality_flags),
            "feature_vector": {name: example.feature_vector.get(name) for name in feature_schema.feature_names},
            "label_source": list(example.label_source),
            "human_review_status": example.human_review_status,
            "human_rating": example.human_rating,
            "human_tags": list(example.human_tags) if include_sensitive else None,
            "exclusion_reason": example.exclusion_reason,
        }
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_default))
    return "\n".join(lines)


def write_export(destination: Path, content: str) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination
