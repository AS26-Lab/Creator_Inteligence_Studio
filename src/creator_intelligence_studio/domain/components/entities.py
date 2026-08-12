"""Entidades del catalogo de componentes locales."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z


class ComponentCategory(str, Enum):
    """Categorias iniciales del catalogo."""

    FFMPEG = "ffmpeg"
    TRANSCRIPTION_RUNTIME = "transcription_runtime"
    TRANSCRIPTION_MODEL = "transcription_model"
    SEMANTIC_MODEL = "semantic_model"
    OPTIONAL_SUPPORT = "optional_support"


class ComponentCatalogStatus(str, Enum):
    """Estado de curacion del catalogo."""

    VERIFIED = "verified"
    PENDING_VERIFICATION = "pending_verification"
    LEGACY = "legacy"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ComponentInstallationStatus(str, Enum):
    """Estado de una instalacion o deteccion local."""

    MANAGED = "managed"
    EXTERNALLY_DETECTED = "externally_detected"
    MISSING = "missing"
    UNKNOWN = "unknown"
    INVALID = "invalid"
    REPAIR_REQUIRED = "repair_required"
    INCOMPATIBLE = "incompatible"
    READY = "ready"


class ComponentInstallKind(str, Enum):
    """Tipo de instalacion registrado."""

    MANAGED = "managed"
    EXTERNALLY_DETECTED = "externally_detected"


class RuntimeCheckStatus(str, Enum):
    """Estado de una comprobacion de runtime."""

    NOT_CHECKED = "not_checked"
    CHECKING = "checking"
    READY = "ready"
    DEGRADED = "degraded"
    INCOMPATIBLE = "incompatible"
    FAILED = "failed"


class ComponentEventType(str, Enum):
    """Tipos de eventos de trazabilidad."""

    CATALOG_LOADED = "catalog_loaded"
    COMPONENT_DETECTED = "component_detected"
    COMPONENT_MISSING = "component_missing"
    COMPONENT_HEALTH_CHECK_STARTED = "component_health_check_started"
    COMPONENT_HEALTH_CHECK_COMPLETED = "component_health_check_completed"
    HARDWARE_INVENTORY_STARTED = "hardware_inventory_started"
    HARDWARE_INVENTORY_COMPLETED = "hardware_inventory_completed"
    TRANSCRIPTION_CAPABILITY_RESOLVED = "transcription_capability_resolved"
    HIDDEN_DOWNLOAD_BLOCKED = "hidden_download_blocked"
    FFMPEG_DETECTION_STARTED = "ffmpeg_detection_started"
    FFMPEG_DETECTED_EXTERNAL = "ffmpeg_detected_external"
    FFMPEG_MANAGED_INSTALL_STARTED = "ffmpeg_managed_install_started"
    FFMPEG_MANAGED_INSTALL_STAGED = "ffmpeg_managed_install_staged"
    FFMPEG_HEALTH_CHECK_STARTED = "ffmpeg_health_check_started"
    FFMPEG_HEALTH_CHECK_COMPLETED = "ffmpeg_health_check_completed"
    FFMPEG_MANAGED_ACTIVATED = "ffmpeg_managed_activated"
    FFMPEG_MANAGED_INSTALL_FAILED = "ffmpeg_managed_install_failed"
    FFMPEG_REPAIR_STARTED = "ffmpeg_repair_started"
    FFMPEG_REPAIR_COMPLETED = "ffmpeg_repair_completed"
    FFMPEG_REMOVED = "ffmpeg_removed"
    FFMPEG_FALLBACK_SELECTED = "ffmpeg_fallback_selected"
    COMPONENT_DOWNLOAD_REQUESTED = "component_download_requested"
    COMPONENT_DOWNLOAD_QUEUED = "component_download_queued"
    COMPONENT_DOWNLOAD_STARTED = "component_download_started"
    COMPONENT_DOWNLOAD_PROGRESS = "component_download_progress"
    COMPONENT_DOWNLOAD_PAUSE_REQUESTED = "component_download_pause_requested"
    COMPONENT_DOWNLOAD_PAUSED = "component_download_paused"
    COMPONENT_DOWNLOAD_RESUME_REQUESTED = "component_download_resume_requested"
    COMPONENT_DOWNLOAD_RESUMED = "component_download_resumed"
    COMPONENT_DOWNLOAD_RETRY_SCHEDULED = "component_download_retry_scheduled"
    COMPONENT_DOWNLOAD_INTERRUPTED = "component_download_interrupted"
    COMPONENT_DOWNLOAD_VERIFICATION_STARTED = "component_download_verification_started"
    COMPONENT_DOWNLOAD_VERIFIED = "component_download_verified"
    COMPONENT_DOWNLOAD_HASH_MISMATCH = "component_download_hash_mismatch"
    COMPONENT_DOWNLOAD_CANCEL_REQUESTED = "component_download_cancel_requested"
    COMPONENT_DOWNLOAD_CANCELLED = "component_download_cancelled"
    COMPONENT_DOWNLOAD_FAILED = "component_download_failed"
    COMPONENT_DOWNLOAD_COMPLETED = "component_download_completed"
    COMPONENT_DOWNLOAD_RECOVERED_AFTER_RESTART = "component_download_recovered_after_restart"
    TRANSCRIPTION_RUNTIME_INSTALL_REQUESTED = "transcription_runtime_install_requested"
    TRANSCRIPTION_RUNTIME_INSTALL_STARTED = "transcription_runtime_install_started"
    TRANSCRIPTION_RUNTIME_HEALTH_CHECK_STARTED = "transcription_runtime_health_check_started"
    TRANSCRIPTION_RUNTIME_HEALTH_CHECK_COMPLETED = "transcription_runtime_health_check_completed"
    TRANSCRIPTION_RUNTIME_ACTIVATED = "transcription_runtime_activated"
    TRANSCRIPTION_RUNTIME_INSTALL_FAILED = "transcription_runtime_install_failed"
    TRANSCRIPTION_RUNTIME_REMOVED = "transcription_runtime_removed"
    TRANSCRIPTION_MODEL_INSTALL_REQUESTED = "transcription_model_install_requested"
    TRANSCRIPTION_MODEL_INSTALL_STARTED = "transcription_model_install_started"
    TRANSCRIPTION_MODEL_VALIDATION_STARTED = "transcription_model_validation_started"
    TRANSCRIPTION_MODEL_VALIDATION_COMPLETED = "transcription_model_validation_completed"
    TRANSCRIPTION_MODEL_HEALTH_CHECK_STARTED = "transcription_model_health_check_started"
    TRANSCRIPTION_MODEL_HEALTH_CHECK_COMPLETED = "transcription_model_health_check_completed"
    TRANSCRIPTION_MODEL_ACTIVATED = "transcription_model_activated"
    TRANSCRIPTION_MODEL_INSTALL_FAILED = "transcription_model_install_failed"
    TRANSCRIPTION_MODEL_REPAIR_STARTED = "transcription_model_repair_started"
    TRANSCRIPTION_MODEL_REPAIR_COMPLETED = "transcription_model_repair_completed"
    TRANSCRIPTION_MODEL_REMOVED = "transcription_model_removed"
    TRANSCRIPTION_MODEL_ROLLBACK_COMPLETED = "transcription_model_rollback_completed"
    LEGACY_MODEL_DETECTED = "legacy_model_detected"
    LEGACY_MODEL_REGISTERED = "legacy_model_registered"


@dataclass(frozen=True, slots=True)
class ComponentCatalogEntry:
    """Entrada versionada del catalogo de componentes."""

    component_id: str
    display_name: str
    category: ComponentCategory
    version: str | None
    revision: str | None
    platform: str | None
    architecture: str | None
    source_type: str
    source_identifier: str | None
    source_provider: str | None = None
    upstream_project: str | None = None
    source_url: str | None = None
    release_tag: str | None = None
    asset_name: str | None = None
    expected_sha256: str | None = None
    upstream_version: str | None = None
    build_revision: str | None = None
    license_variant: str | None = None
    source_page_reference: str | None = None
    verified_at: datetime | None = None
    allowed_domains: tuple[str, ...] = ()
    expected_download_bytes: int | None = None
    expected_installed_bytes: int | None = None
    temporary_space_bytes: int | None = None
    sha256: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    attribution: str | None = None
    dependencies: tuple[str, ...] = ()
    capabilities_enabled: tuple[str, ...] = ()
    minimum_requirements: dict[str, Any] = field(default_factory=dict)
    recommended_requirements: dict[str, Any] = field(default_factory=dict)
    install_strategy: str | None = None
    health_check: str | None = None
    rollback_supported: bool = False
    catalog_version: int = 1
    reviewed_at: datetime | None = None
    status: ComponentCatalogStatus = ComponentCatalogStatus.UNKNOWN
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "display_name": self.display_name,
            "category": self.category.value,
            "version": self.version,
            "revision": self.revision,
            "platform": self.platform,
            "architecture": self.architecture,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "source_provider": self.source_provider,
            "upstream_project": self.upstream_project,
            "source_url": self.source_url,
            "release_tag": self.release_tag,
            "asset_name": self.asset_name,
            "expected_sha256": self.expected_sha256,
            "upstream_version": self.upstream_version,
            "build_revision": self.build_revision,
            "license_variant": self.license_variant,
            "source_page_reference": self.source_page_reference,
            "verified_at": to_iso_z(self.verified_at),
            "allowed_domains": list(self.allowed_domains),
            "expected_download_bytes": self.expected_download_bytes,
            "expected_installed_bytes": self.expected_installed_bytes,
            "temporary_space_bytes": self.temporary_space_bytes,
            "sha256": self.sha256,
            "license_name": self.license_name,
            "license_url": self.license_url,
            "attribution": self.attribution,
            "dependencies": list(self.dependencies),
            "capabilities_enabled": list(self.capabilities_enabled),
            "minimum_requirements": dict(self.minimum_requirements),
            "recommended_requirements": dict(self.recommended_requirements),
            "install_strategy": self.install_strategy,
            "health_check": self.health_check,
            "rollback_supported": self.rollback_supported,
            "catalog_version": self.catalog_version,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ComponentCatalog:
    """Catalogo versionado de componentes."""

    catalog_version: int
    entries: tuple[ComponentCatalogEntry, ...]
    reviewed_at: datetime | None = None

    def list_entries(self) -> tuple[ComponentCatalogEntry, ...]:
        return self.entries

    def get_entry(self, component_id: str) -> ComponentCatalogEntry | None:
        normalized = component_id.strip().lower()
        for entry in self.entries:
            if entry.component_id.lower() == normalized:
                return entry
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class ComponentInstallation:
    """Instalacion o deteccion local de un componente."""

    component_id: str
    installation_status: ComponentInstallationStatus
    installed_version: str | None
    revision: str | None
    install_type: ComponentInstallKind
    location_path: str | None
    location_reference: str | None
    detected_at: datetime | None
    verified_at: datetime | None
    health_status: RuntimeCheckStatus
    source: str | None
    managed: bool
    last_error_code: str | None = None
    last_error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "installation_status": self.installation_status.value,
            "installed_version": self.installed_version,
            "revision": self.revision,
            "install_type": self.install_type.value,
            "location_path": self.location_path,
            "location_reference": self.location_reference,
            "detected_at": to_iso_z(self.detected_at),
            "verified_at": to_iso_z(self.verified_at),
            "health_status": self.health_status.value,
            "source": self.source,
            "managed": self.managed,
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
            "metadata": dict(self.metadata),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class RuntimeCheckRecord:
    """Resultado persistido de una comprobacion de runtime."""

    component_id: str
    status: RuntimeCheckStatus
    runtime_importable: bool | None
    runtime_version: str | None
    device_count: int | None
    supported_compute_types: tuple[str, ...] = ()
    notes: str | None = None
    warning_message: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "status": self.status.value,
            "runtime_importable": self.runtime_importable,
            "runtime_version": self.runtime_version,
            "device_count": self.device_count,
            "supported_compute_types": list(self.supported_compute_types),
            "notes": self.notes,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
            "checked_at": to_iso_z(self.checked_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ComponentEvent:
    """Evento minimo de trazabilidad de componentes."""

    event_type: ComponentEventType
    message_safe: str
    component_id: str | None = None
    installation_component_id: str | None = None
    hardware_profile_id: str | None = None
    profile_id: str | None = None
    severity: str = "info"
    technical_reference: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "message_safe": self.message_safe,
            "component_id": self.component_id,
            "installation_component_id": self.installation_component_id,
            "hardware_profile_id": self.hardware_profile_id,
            "profile_id": self.profile_id,
            "severity": self.severity,
            "technical_reference": self.technical_reference,
            "payload": dict(self.payload),
            "created_at": to_iso_z(self.created_at),
        }
