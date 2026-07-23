"""Mapeo centralizado de errores tecnicos a mensajes de usuario."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.audio.errors import AudioPreparationError, AudioStateError, AudioToolUnavailableError, AudioValidationError
from creator_intelligence_studio.domain.errors import ConflictError, DomainError, NotFoundError, StateError, ValidationError
from creator_intelligence_studio.domain.media.errors import MediaInspectionError, MediaToolUnavailableError
from creator_intelligence_studio.domain.personalization_data.errors import PersonalizationDataStateError, PersonalizationDataValidationError
from creator_intelligence_studio.domain.personalization_models.errors import PersonalizationModelArtifactError, PersonalizationModelStateError, PersonalizationModelValidationError
from creator_intelligence_studio.domain.transcription.errors import TranscriptionBackendError, TranscriptionStateError, TranscriptionValidationError


@dataclass(frozen=True, slots=True)
class UserFacingError:
    title: str
    explanation: str
    cause: str | None
    recommended_action: str
    technical_code: str
    details: str | None = None


def map_error(exc: Exception) -> UserFacingError:
    if isinstance(exc, (MediaToolUnavailableError, AudioToolUnavailableError, TranscriptionBackendError)):
        return UserFacingError(
            title="Herramienta no disponible",
            explanation=str(exc),
            cause="Falta una dependencia o el backend local no responde.",
            recommended_action="Verifica FFmpeg, CUDA y el modelo de transcripcion.",
            technical_code=exc.__class__.__name__,
            details=repr(exc),
        )
    if isinstance(exc, NotFoundError):
        return UserFacingError(
            title="Elemento no encontrado",
            explanation=str(exc),
            cause="El recurso fue eliminado o no pertenece al contexto actual.",
            recommended_action="Actualiza la vista y verifica el creador o proyecto activo.",
            technical_code=exc.__class__.__name__,
            details=repr(exc),
        )
    if isinstance(exc, (ConflictError, PersonalizationDataValidationError, PersonalizationModelValidationError, TranscriptionValidationError, AudioValidationError, ValidationError)):
        return UserFacingError(
            title="Entrada no valida",
            explanation=str(exc),
            cause="La accion no cumple las reglas actuales del pipeline.",
            recommended_action="Revisa los datos de entrada o el estado previo antes de reintentar.",
            technical_code=exc.__class__.__name__,
            details=repr(exc),
        )
    if isinstance(exc, (StateError, AudioStateError, TranscriptionStateError, PersonalizationDataStateError, PersonalizationModelStateError)):
        return UserFacingError(
            title="La accion no esta disponible",
            explanation=str(exc),
            cause="Falta un paso previo o el estado quedo desactualizado.",
            recommended_action="Ejecuta la etapa previa o regenera el resultado stale.",
            technical_code=exc.__class__.__name__,
            details=repr(exc),
        )
    if isinstance(exc, (AudioPreparationError, MediaInspectionError, PersonalizationModelArtifactError)):
        return UserFacingError(
            title="Operacion fallida",
            explanation=str(exc),
            cause=None,
            recommended_action="Reintenta la etapa o revisa el detalle tecnico expandible.",
            technical_code=exc.__class__.__name__,
            details=repr(exc),
        )
    return UserFacingError(
        title="Error inesperado",
        explanation=str(exc),
        cause=None,
        recommended_action="Reintenta la accion o revisa el detalle tecnico.",
        technical_code=exc.__class__.__name__,
        details=repr(exc),
    )

