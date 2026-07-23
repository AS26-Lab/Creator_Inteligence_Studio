"""Estrategia determinista de splits para datasets de personalizacion."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from creator_intelligence_studio.domain.personalization_data.entities import CreatorDatasetExample
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetOptions, PersonalizationSplitName


@dataclass(frozen=True, slots=True)
class SplitAssignment:
    example_id: str
    split_name: PersonalizationSplitName


def _stable_bucket(value: str, seed: int) -> int:
    payload = f"{seed}:{value}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16) % 10


def assign_dataset_splits(
    examples: list[CreatorDatasetExample],
    *,
    options: PersonalizationDatasetOptions,
) -> dict[str, PersonalizationSplitName]:
    if not examples:
        return {}
    video_groups: dict[str, list[CreatorDatasetExample]] = {}
    for example in examples:
        video_groups.setdefault(example.video_asset_id, []).append(example)
    if len(video_groups) < options.minimum_videos_for_evaluation:
        return {example.id: PersonalizationSplitName.TRAIN for example in examples}
    assignments: dict[str, PersonalizationSplitName] = {}
    for video_id in sorted(video_groups):
        bucket = _stable_bucket(video_id, options.split_seed)
        if bucket < int(options.train_ratio * 10):
            split = PersonalizationSplitName.TRAIN
        elif bucket < int((options.train_ratio + options.validation_ratio) * 10):
            split = PersonalizationSplitName.VALIDATION
        else:
            split = PersonalizationSplitName.TEST
        for example in video_groups[video_id]:
            assignments[example.id] = split
    if PersonalizationSplitName.VALIDATION not in assignments.values():
        first_video = sorted(video_groups)[0]
        for example in video_groups[first_video]:
            assignments[example.id] = PersonalizationSplitName.VALIDATION
    if PersonalizationSplitName.TEST not in assignments.values() and len(video_groups) > 2:
        last_video = sorted(video_groups)[-1]
        for example in video_groups[last_video]:
            assignments[example.id] = PersonalizationSplitName.TEST
    return assignments
