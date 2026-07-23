"""Validacion de tiempos para subtitulos."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.subtitles.services import validate_subtitle_cue
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleCueDraft, SubtitleCueValidationStatus, SubtitleGenerationOptions


@dataclass(frozen=True, slots=True)
class SubtitleTimingValidationResult:
    cue_statuses: tuple[SubtitleCueValidationStatus, ...]
    cue_warnings: tuple[tuple[str, ...], ...]
    blocking_errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.blocking_errors


class SubtitleTimingValidator:
    def validate(
        self,
        cues: list[SubtitleCueDraft],
        *,
        options: SubtitleGenerationOptions,
        source_duration_seconds: float | None = None,
    ) -> SubtitleTimingValidationResult:
        statuses: list[SubtitleCueValidationStatus] = []
        warnings: list[tuple[str, ...]] = []
        blocking_errors: list[str] = []
        aggregate_warnings: list[str] = []
        previous_end = None
        previous_text = None
        for cue in cues:
            status, cue_warnings = validate_subtitle_cue(
                cue,
                options=options,
                source_duration_seconds=source_duration_seconds,
                previous_end_seconds=previous_end,
            )
            if previous_text is not None and previous_text == cue.text:
                cue_warnings = tuple(dict.fromkeys((*cue_warnings, "duplicate_text")))
                if status != SubtitleCueValidationStatus.INVALID:
                    status = SubtitleCueValidationStatus.WARNING
            if status == SubtitleCueValidationStatus.INVALID:
                blocking_errors.append("invalid_cue")
            statuses.append(status)
            warnings.append(cue_warnings)
            aggregate_warnings.extend(cue_warnings)
            previous_end = cue.end_seconds
            previous_text = cue.text
        return SubtitleTimingValidationResult(
            cue_statuses=tuple(statuses),
            cue_warnings=tuple(warnings),
            blocking_errors=tuple(dict.fromkeys(blocking_errors)),
            warnings=tuple(dict.fromkeys(aggregate_warnings)),
        )

