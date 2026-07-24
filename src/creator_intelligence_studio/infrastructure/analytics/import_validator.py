"""Validacion de filas importadas de analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsContentType, AnalyticsImportRowStatus


@dataclass(frozen=True, slots=True)
class RowValidationOutcome:
    status: AnalyticsImportRowStatus
    warning_codes: tuple[str, ...]
    error_codes: tuple[str, ...]
    message: str | None = None


def validate_row(*, publication_payload: dict[str, object] | None, content_type: AnalyticsContentType | None, published_at: datetime | None, warnings: list[str], errors: list[str]) -> RowValidationOutcome:
    if publication_payload is None:
        errors.append("missing_required_field")
    if published_at is None:
        errors.append("invalid_date")
    if content_type is None:
        errors.append("missing_required_field")
    if errors:
        return RowValidationOutcome(AnalyticsImportRowStatus.REJECTED, tuple(dict.fromkeys(warnings)), tuple(dict.fromkeys(errors)))
    status = AnalyticsImportRowStatus.ACCEPTED_WITH_WARNINGS if warnings else AnalyticsImportRowStatus.ACCEPTED
    return RowValidationOutcome(status, tuple(dict.fromkeys(warnings)), tuple())
