"""Value objects y definiciones del modelo de audiencia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audience_types import AudienceConfidenceLevel, AudienceLifecycleStage, AudienceSignalType, AudienceStatus
from .lifecycle_types import AudienceContentRole, AudiencePlatformRole
from .segment_types import AudienceSegmentScope, AudienceSegmentType


@dataclass(frozen=True, slots=True)
class AudienceSignalBasis:
    metric_key: str
    metric_value: float | str | None
    platform: str
    content_type: str | None
    publication_id: str | None
    source_type: str
    dimensions: dict[str, Any]

