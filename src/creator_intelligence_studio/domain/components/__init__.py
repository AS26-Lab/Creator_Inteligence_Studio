"""Dominio de componentes locales y catalogo versionado."""

from .catalog import (
    DEFAULT_COMPONENT_CATALOG_VERSION,
    DEFAULT_TRANSCRIPTION_PROFILE_VERSION,
    build_default_component_catalog,
    build_default_transcription_profiles,
)
from .entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentCatalogStatus,
    ComponentCategory,
    ComponentEvent,
    ComponentEventType,
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from .repositories import ComponentManagerRepository

__all__ = [
    "ComponentCatalog",
    "ComponentCatalogEntry",
    "ComponentCatalogStatus",
    "ComponentCategory",
    "ComponentEvent",
    "ComponentEventType",
    "ComponentInstallation",
    "ComponentInstallationStatus",
    "ComponentInstallKind",
    "ComponentManagerRepository",
    "RuntimeCheckRecord",
    "RuntimeCheckStatus",
    "DEFAULT_COMPONENT_CATALOG_VERSION",
    "DEFAULT_TRANSCRIPTION_PROFILE_VERSION",
    "build_default_component_catalog",
    "build_default_transcription_profiles",
]
