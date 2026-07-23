"""Errores del dominio de modelos personalizados."""

from __future__ import annotations


class PersonalizationModelValidationError(ValueError):
    """Datos invalidos para entrenamiento o inferencia."""


class PersonalizationModelStateError(RuntimeError):
    """Estado incompatible para entrenar, activar o puntuar modelos."""


class PersonalizationModelArtifactError(RuntimeError):
    """Error con un artefacto local de modelo."""
