"""Repositorio SQLite para el foundation de componentes locales."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentCatalogStatus,
    ComponentCategory,
    ComponentEvent,
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.hardware.entities import DiskVolumeSummary, GpuSummary, HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.hardware.repositories import HardwareInventoryRepository
from creator_intelligence_studio.domain.transcription.profiles import (
    TranscriptionProfileDefinition,
    TranscriptionProfileStatus,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_load(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _bool_from_db(value: object | None) -> bool:
    return bool(int(value or 0))


def _bool_to_db(value: bool) -> int:
    return 1 if value else 0


def _status_or_unknown(value: str | None, enum_cls):
    if not value:
        return enum_cls.UNKNOWN
    try:
        return enum_cls(value)
    except ValueError:
        return enum_cls.UNKNOWN


def _component_catalog_row(entry: ComponentCatalogEntry) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "component_id": entry.component_id,
        "display_name": entry.display_name,
        "category": entry.category.value,
        "version": entry.version,
        "revision": entry.revision,
        "platform": entry.platform,
        "architecture": entry.architecture,
        "source_type": entry.source_type,
        "source_identifier": entry.source_identifier,
        "source_provider": entry.source_provider,
        "upstream_project": entry.upstream_project,
        "source_url": entry.source_url,
        "release_tag": entry.release_tag,
        "asset_name": entry.asset_name,
        "expected_sha256": entry.expected_sha256,
        "upstream_version": entry.upstream_version,
        "build_revision": entry.build_revision,
        "license_variant": entry.license_variant,
        "source_page_reference": entry.source_page_reference,
        "verified_at": entry.verified_at.isoformat() if entry.verified_at else None,
        "allowed_domains_json": _json_dump(list(entry.allowed_domains)),
        "expected_download_bytes": entry.expected_download_bytes,
        "expected_installed_bytes": entry.expected_installed_bytes,
        "temporary_space_bytes": entry.temporary_space_bytes,
        "sha256": entry.sha256,
        "license_name": entry.license_name,
        "license_url": entry.license_url,
        "attribution": entry.attribution,
        "dependencies_json": _json_dump(list(entry.dependencies)),
        "capabilities_enabled_json": _json_dump(list(entry.capabilities_enabled)),
        "minimum_requirements_json": _json_dump(entry.minimum_requirements),
        "recommended_requirements_json": _json_dump(entry.recommended_requirements),
        "install_strategy": entry.install_strategy,
        "health_check": entry.health_check,
        "rollback_supported": _bool_to_db(entry.rollback_supported),
        "catalog_version": entry.catalog_version,
        "reviewed_at": entry.reviewed_at.isoformat() if entry.reviewed_at else None,
        "status": entry.status.value,
        "created_at": (entry.created_at or utc_now()).isoformat(),
        "updated_at": (entry.updated_at or utc_now()).isoformat(),
    }


def _row_to_component_catalog(row: sqlite3.Row) -> ComponentCatalogEntry:
    return ComponentCatalogEntry(
        component_id=row["component_id"],
        display_name=row["display_name"],
        category=ComponentCategory(row["category"]),
        version=row["version"],
        revision=row["revision"],
        platform=row["platform"],
        architecture=row["architecture"],
        source_type=row["source_type"],
        source_identifier=row["source_identifier"],
        source_provider=row["source_provider"],
        upstream_project=row["upstream_project"],
        source_url=row["source_url"],
        release_tag=row["release_tag"],
        asset_name=row["asset_name"],
        expected_sha256=row["expected_sha256"],
        upstream_version=row["upstream_version"],
        build_revision=row["build_revision"],
        license_variant=row["license_variant"],
        source_page_reference=row["source_page_reference"],
        verified_at=from_iso_z(row["verified_at"]),
        allowed_domains=tuple(_json_load(row["allowed_domains_json"], [])),
        expected_download_bytes=row["expected_download_bytes"],
        expected_installed_bytes=row["expected_installed_bytes"],
        temporary_space_bytes=row["temporary_space_bytes"],
        sha256=row["sha256"],
        license_name=row["license_name"],
        license_url=row["license_url"],
        attribution=row["attribution"],
        dependencies=tuple(_json_load(row["dependencies_json"], [])),
        capabilities_enabled=tuple(_json_load(row["capabilities_enabled_json"], [])),
        minimum_requirements=dict(_json_load(row["minimum_requirements_json"], {})),
        recommended_requirements=dict(_json_load(row["recommended_requirements_json"], {})),
        install_strategy=row["install_strategy"],
        health_check=row["health_check"],
        rollback_supported=_bool_from_db(row["rollback_supported"]),
        catalog_version=row["catalog_version"],
        reviewed_at=from_iso_z(row["reviewed_at"]),
        status=_status_or_unknown(row["status"], ComponentCatalogStatus),
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
    )


def _installation_row(installation: ComponentInstallation) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "component_id": installation.component_id,
        "installation_status": installation.installation_status.value,
        "installed_version": installation.installed_version,
        "revision": installation.revision,
        "install_type": installation.install_type.value,
        "location_path": installation.location_path,
        "location_reference": installation.location_reference,
        "detected_at": installation.detected_at.isoformat() if installation.detected_at else None,
        "verified_at": installation.verified_at.isoformat() if installation.verified_at else None,
        "health_status": installation.health_status.value,
        "source": installation.source,
        "managed": _bool_to_db(installation.managed),
        "last_error_code": installation.last_error_code,
        "last_error_message": installation.last_error_message,
        "metadata_json": _json_dump(installation.metadata),
        "created_at": (installation.created_at or utc_now()).isoformat(),
        "updated_at": (installation.updated_at or utc_now()).isoformat(),
    }


def _row_to_installation(row: sqlite3.Row) -> ComponentInstallation:
    return ComponentInstallation(
        component_id=row["component_id"],
        installation_status=_status_or_unknown(row["installation_status"], ComponentInstallationStatus),
        installed_version=row["installed_version"],
        revision=row["revision"],
        install_type=ComponentInstallKind(row["install_type"]) if row["install_type"] else ComponentInstallKind.EXTERNALLY_DETECTED,
        location_path=row["location_path"],
        location_reference=row["location_reference"],
        detected_at=from_iso_z(row["detected_at"]),
        verified_at=from_iso_z(row["verified_at"]),
        health_status=_status_or_unknown(row["health_status"], RuntimeCheckStatus),
        source=row["source"],
        managed=_bool_from_db(row["managed"]),
        last_error_code=row["last_error_code"],
        last_error_message=row["last_error_message"],
        metadata=dict(_json_load(row["metadata_json"], {})),
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
    )


def _hardware_row(profile: HardwareProfile) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "generated_at": profile.generated_at.isoformat(),
        "platform": profile.platform,
        "architecture": profile.architecture,
        "cpu_logical_count": profile.cpu_logical_count,
        "cpu_summary": profile.cpu_summary,
        "ram_total_bytes": profile.ram_total_bytes,
        "ram_available_bytes": profile.ram_available_bytes,
        "gpu_vendor": profile.gpu.vendor,
        "gpu_name": profile.gpu.name,
        "gpu_driver_version": profile.gpu.driver_version,
        "gpu_vram_total_bytes": profile.gpu.vram_total_bytes,
        "gpu_cuda_visible": _bool_to_db(profile.gpu.cuda_visible),
        "gpu_cuda_runtime_reported": profile.gpu.cuda_runtime_reported,
        "gpu_ctranslate2_cuda_available": None if profile.gpu.ctranslate2_cuda_available is None else _bool_to_db(profile.gpu.ctranslate2_cuda_available),
        "gpu_status": profile.gpu.status.value,
        "gpu_notes": profile.gpu.notes,
        "driver_summary": profile.driver_summary,
        "cuda_reported": profile.cuda_reported,
        "ctranslate2_cuda_status": profile.ctranslate2_cuda_status.value,
        "disk_volumes_json": _json_dump([volume.to_dict() for volume in profile.disk_volumes]),
        "detection_source": profile.detection_source,
        "status": profile.status.value,
        "warnings_json": _json_dump(list(profile.warnings)),
        "errors_json": _json_dump(list(profile.errors)),
        "created_at": (profile.created_at or profile.generated_at).isoformat(),
        "updated_at": (profile.updated_at or profile.generated_at).isoformat(),
    }


def _row_to_hardware(row: sqlite3.Row) -> HardwareProfile:
    gpu = GpuSummary(
        vendor=row["gpu_vendor"],
        name=row["gpu_name"],
        driver_version=row["gpu_driver_version"],
        vram_total_bytes=row["gpu_vram_total_bytes"],
        cuda_visible=_bool_from_db(row["gpu_cuda_visible"]),
        cuda_runtime_reported=row["gpu_cuda_runtime_reported"],
        ctranslate2_cuda_available=(
            None if row["gpu_ctranslate2_cuda_available"] is None else _bool_from_db(row["gpu_ctranslate2_cuda_available"])
        ),
        status=_status_or_unknown(row["gpu_status"], HardwareCapabilityState),
        notes=row["gpu_notes"],
    )
    volumes = []
    for raw in _json_load(row["disk_volumes_json"], []):
        volumes.append(
            DiskVolumeSummary(
                path=str(raw.get("path", "")),
                free_bytes=raw.get("free_bytes"),
                total_bytes=raw.get("total_bytes"),
                status=_status_or_unknown(raw.get("status"), HardwareCapabilityState),
                notes=raw.get("notes"),
            )
        )
    return HardwareProfile(
        generated_at=from_iso_z(row["generated_at"]) or utc_now(),
        platform=row["platform"],
        architecture=row["architecture"],
        cpu_logical_count=row["cpu_logical_count"],
        cpu_summary=row["cpu_summary"],
        ram_total_bytes=row["ram_total_bytes"],
        ram_available_bytes=row["ram_available_bytes"],
        gpu=gpu,
        driver_summary=row["driver_summary"],
        cuda_reported=row["cuda_reported"],
        ctranslate2_cuda_status=_status_or_unknown(row["ctranslate2_cuda_status"], HardwareCapabilityState),
        disk_volumes=tuple(volumes),
        detection_source=row["detection_source"],
        status=_status_or_unknown(row["status"], HardwareCapabilityState),
        warnings=tuple(_json_load(row["warnings_json"], [])),
        errors=tuple(_json_load(row["errors_json"], [])),
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
    )


def _profile_row(profile: TranscriptionProfileDefinition) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "profile_id": profile.profile_id,
        "display_name": profile.display_name,
        "description": profile.description,
        "model_component_id": profile.model_component_id,
        "model_revision": profile.model_revision,
        "device_policy": profile.device_policy,
        "cpu_compute_type": profile.cpu_compute_type,
        "gpu_compute_type": profile.gpu_compute_type,
        "beam_size": profile.beam_size,
        "vad_policy": profile.vad_policy,
        "language_detection": profile.language_detection,
        "word_timestamps": None if profile.word_timestamps is None else _bool_to_db(profile.word_timestamps),
        "segment_timestamps": None if profile.segment_timestamps is None else _bool_to_db(profile.segment_timestamps),
        "batching_policy": profile.batching_policy,
        "minimum_ram_gb": profile.minimum_ram_gb,
        "minimum_vram_gb": profile.minimum_vram_gb,
        "recommended_vram_gb": profile.recommended_vram_gb,
        "estimated_disk_bytes": profile.estimated_disk_bytes,
        "status": profile.status.value,
        "version": profile.version,
        "reviewed_at": profile.reviewed_at.isoformat() if profile.reviewed_at else None,
        "created_at": (profile.created_at or utc_now()).isoformat(),
        "updated_at": (profile.updated_at or utc_now()).isoformat(),
    }


def _row_to_profile(row: sqlite3.Row) -> TranscriptionProfileDefinition:
    return TranscriptionProfileDefinition(
        profile_id=row["profile_id"],
        display_name=row["display_name"],
        description=row["description"],
        model_component_id=row["model_component_id"],
        model_revision=row["model_revision"],
        device_policy=row["device_policy"],
        cpu_compute_type=row["cpu_compute_type"],
        gpu_compute_type=row["gpu_compute_type"],
        beam_size=row["beam_size"],
        vad_policy=row["vad_policy"],
        language_detection=row["language_detection"],
        word_timestamps=None if row["word_timestamps"] is None else _bool_from_db(row["word_timestamps"]),
        segment_timestamps=None if row["segment_timestamps"] is None else _bool_from_db(row["segment_timestamps"]),
        batching_policy=row["batching_policy"],
        minimum_ram_gb=row["minimum_ram_gb"],
        minimum_vram_gb=row["minimum_vram_gb"],
        recommended_vram_gb=row["recommended_vram_gb"],
        estimated_disk_bytes=row["estimated_disk_bytes"],
        status=TranscriptionProfileStatus(row["status"]) if row["status"] else TranscriptionProfileStatus.UNKNOWN,
        version=row["version"],
        reviewed_at=from_iso_z(row["reviewed_at"]),
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
    )


def _runtime_row(record: RuntimeCheckRecord) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "component_id": record.component_id,
        "status": record.status.value,
        "runtime_importable": None if record.runtime_importable is None else _bool_to_db(record.runtime_importable),
        "runtime_version": record.runtime_version,
        "device_count": record.device_count,
        "supported_compute_types_json": _json_dump(list(record.supported_compute_types)),
        "notes": record.notes,
        "warning_message": record.warning_message,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "metadata_json": _json_dump(record.metadata),
        "checked_at": record.checked_at.isoformat() if record.checked_at else None,
        "created_at": (record.created_at or utc_now()).isoformat(),
        "updated_at": (record.updated_at or utc_now()).isoformat(),
    }


def _row_to_runtime(row: sqlite3.Row) -> RuntimeCheckRecord:
    return RuntimeCheckRecord(
        component_id=row["component_id"],
        status=_status_or_unknown(row["status"], RuntimeCheckStatus),
        runtime_importable=None if row["runtime_importable"] is None else _bool_from_db(row["runtime_importable"]),
        runtime_version=row["runtime_version"],
        device_count=row["device_count"],
        supported_compute_types=tuple(_json_load(row["supported_compute_types_json"], [])),
        notes=row["notes"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        metadata=dict(_json_load(row["metadata_json"], {})),
        checked_at=from_iso_z(row["checked_at"]),
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
    )


def _row_to_event(row: sqlite3.Row) -> ComponentEvent:
    from creator_intelligence_studio.domain.components.entities import ComponentEventType

    return ComponentEvent(
        event_type=ComponentEventType(row["event_type"]),
        message_safe=row["message_safe"],
        component_id=row["component_id"],
        installation_component_id=row["installation_component_id"],
        hardware_profile_id=row["hardware_profile_id"],
        profile_id=row["profile_id"],
        severity=row["severity"],
        technical_reference=row["technical_reference"],
        payload=dict(_json_load(row["payload_json"], {})),
        created_at=from_iso_z(row["created_at"]),
    )


class SQLiteComponentManagerRepository(ComponentManagerRepository, HardwareInventoryRepository):
    """Repositorio SQLite para catalogo, inventario y trazabilidad."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def get_catalog(self) -> ComponentCatalog:
        entries = self.list_catalog_entries()
        reviewed_at = max((entry.reviewed_at for entry in entries if entry.reviewed_at is not None), default=None)
        version = max((entry.catalog_version for entry in entries), default=1)
        return ComponentCatalog(catalog_version=version, entries=entries, reviewed_at=reviewed_at)

    def list_catalog_entries(self) -> tuple[ComponentCatalogEntry, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM component_catalog ORDER BY component_id ASC, catalog_version DESC, updated_at DESC"
            ).fetchall()
        latest: dict[str, ComponentCatalogEntry] = {}
        for row in rows:
            entry = _row_to_component_catalog(row)
            latest.setdefault(entry.component_id, entry)
        return tuple(latest.values())

    def get_catalog_entry(self, component_id: str) -> ComponentCatalogEntry | None:
        normalized = component_id.strip().lower()
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM component_catalog
                WHERE lower(component_id) = ?
                ORDER BY catalog_version DESC, updated_at DESC
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
        return _row_to_component_catalog(row) if row else None

    def upsert_catalog_entry(self, entry: ComponentCatalogEntry) -> ComponentCatalogEntry:
        payload = _component_catalog_row(entry)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO component_catalog (
                    id, component_id, display_name, category, version, revision, platform,
                    architecture, source_type, source_identifier, source_provider,
                    upstream_project, source_url, release_tag, asset_name, expected_sha256,
                    upstream_version, build_revision, license_variant, source_page_reference,
                    verified_at, allowed_domains_json, expected_download_bytes,
                    expected_installed_bytes, temporary_space_bytes, sha256, license_name,
                    license_url, attribution, dependencies_json, capabilities_enabled_json,
                    minimum_requirements_json, recommended_requirements_json, install_strategy,
                    health_check, rollback_supported, catalog_version, reviewed_at, status,
                    created_at, updated_at
                ) VALUES (
                    :id, :component_id, :display_name, :category, :version, :revision, :platform,
                    :architecture, :source_type, :source_identifier, :source_provider,
                    :upstream_project, :source_url, :release_tag, :asset_name, :expected_sha256,
                    :upstream_version, :build_revision, :license_variant, :source_page_reference,
                    :verified_at, :allowed_domains_json, :expected_download_bytes,
                    :expected_installed_bytes, :temporary_space_bytes, :sha256, :license_name,
                    :license_url, :attribution, :dependencies_json, :capabilities_enabled_json,
                    :minimum_requirements_json, :recommended_requirements_json, :install_strategy,
                    :health_check, :rollback_supported, :catalog_version, :reviewed_at, :status,
                    :created_at, :updated_at
                )
                ON CONFLICT(component_id, catalog_version) DO UPDATE SET
                    display_name = excluded.display_name,
                    category = excluded.category,
                    version = excluded.version,
                    revision = excluded.revision,
                    platform = excluded.platform,
                    architecture = excluded.architecture,
                    source_type = excluded.source_type,
                    source_identifier = excluded.source_identifier,
                    source_provider = excluded.source_provider,
                    upstream_project = excluded.upstream_project,
                    source_url = excluded.source_url,
                    release_tag = excluded.release_tag,
                    asset_name = excluded.asset_name,
                    expected_sha256 = excluded.expected_sha256,
                    upstream_version = excluded.upstream_version,
                    build_revision = excluded.build_revision,
                    license_variant = excluded.license_variant,
                    source_page_reference = excluded.source_page_reference,
                    verified_at = excluded.verified_at,
                    allowed_domains_json = excluded.allowed_domains_json,
                    expected_download_bytes = excluded.expected_download_bytes,
                    expected_installed_bytes = excluded.expected_installed_bytes,
                    temporary_space_bytes = excluded.temporary_space_bytes,
                    sha256 = excluded.sha256,
                    license_name = excluded.license_name,
                    license_url = excluded.license_url,
                    attribution = excluded.attribution,
                    dependencies_json = excluded.dependencies_json,
                    capabilities_enabled_json = excluded.capabilities_enabled_json,
                    minimum_requirements_json = excluded.minimum_requirements_json,
                    recommended_requirements_json = excluded.recommended_requirements_json,
                    install_strategy = excluded.install_strategy,
                    health_check = excluded.health_check,
                    rollback_supported = excluded.rollback_supported,
                    reviewed_at = excluded.reviewed_at,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            row = connection.execute(
                "SELECT * FROM component_catalog WHERE component_id = ? AND catalog_version = ?",
                (entry.component_id, entry.catalog_version),
            ).fetchone()
        return _row_to_component_catalog(row) if row else entry

    def list_installations(self) -> tuple[ComponentInstallation, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM component_installations ORDER BY component_id ASC, updated_at DESC"
            ).fetchall()
        return tuple(_row_to_installation(row) for row in rows)

    def get_installation(self, component_id: str) -> ComponentInstallation | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM component_installations WHERE lower(component_id) = ? ORDER BY updated_at DESC LIMIT 1",
                (component_id.strip().lower(),),
            ).fetchone()
        return _row_to_installation(row) if row else None

    def upsert_installation(self, installation: ComponentInstallation) -> ComponentInstallation:
        payload = _installation_row(installation)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO component_installations (
                    id, component_id, installation_status, installed_version, revision,
                    install_type, location_path, location_reference, detected_at, verified_at,
                    health_status, source, managed, last_error_code, last_error_message,
                    metadata_json, created_at, updated_at
                ) VALUES (
                    :id, :component_id, :installation_status, :installed_version, :revision,
                    :install_type, :location_path, :location_reference, :detected_at, :verified_at,
                    :health_status, :source, :managed, :last_error_code, :last_error_message,
                    :metadata_json, :created_at, :updated_at
                )
                ON CONFLICT(component_id) DO UPDATE SET
                    installation_status = excluded.installation_status,
                    installed_version = excluded.installed_version,
                    revision = excluded.revision,
                    install_type = excluded.install_type,
                    location_path = excluded.location_path,
                    location_reference = excluded.location_reference,
                    detected_at = excluded.detected_at,
                    verified_at = excluded.verified_at,
                    health_status = excluded.health_status,
                    source = excluded.source,
                    managed = excluded.managed,
                    last_error_code = excluded.last_error_code,
                    last_error_message = excluded.last_error_message,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            row = connection.execute(
                "SELECT * FROM component_installations WHERE component_id = ?",
                (installation.component_id,),
            ).fetchone()
        return _row_to_installation(row) if row else installation

    def list_hardware_profiles(self) -> tuple[HardwareProfile, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hardware_profiles ORDER BY generated_at DESC, id DESC"
            ).fetchall()
        return tuple(_row_to_hardware(row) for row in rows)

    def upsert_hardware_profile(self, profile: HardwareProfile) -> HardwareProfile:
        payload = _hardware_row(profile)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO hardware_profiles (
                    id, generated_at, platform, architecture, cpu_logical_count, cpu_summary,
                    ram_total_bytes, ram_available_bytes, gpu_vendor, gpu_name,
                    gpu_driver_version, gpu_vram_total_bytes, gpu_cuda_visible,
                    gpu_cuda_runtime_reported, gpu_ctranslate2_cuda_available, gpu_status,
                    gpu_notes, driver_summary, cuda_reported, ctranslate2_cuda_status,
                    disk_volumes_json, detection_source, status, warnings_json, errors_json,
                    created_at, updated_at
                ) VALUES (
                    :id, :generated_at, :platform, :architecture, :cpu_logical_count, :cpu_summary,
                    :ram_total_bytes, :ram_available_bytes, :gpu_vendor, :gpu_name,
                    :gpu_driver_version, :gpu_vram_total_bytes, :gpu_cuda_visible,
                    :gpu_cuda_runtime_reported, :gpu_ctranslate2_cuda_available, :gpu_status,
                    :gpu_notes, :driver_summary, :cuda_reported, :ctranslate2_cuda_status,
                    :disk_volumes_json, :detection_source, :status, :warnings_json, :errors_json,
                    :created_at, :updated_at
                )
                """,
                payload,
            )
        return profile

    def latest_hardware_profile(self) -> HardwareProfile | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM hardware_profiles ORDER BY generated_at DESC, id DESC LIMIT 1"
            ).fetchone()
        return _row_to_hardware(row) if row else None

    def list_transcription_profiles(self) -> tuple[TranscriptionProfileDefinition, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcription_profiles ORDER BY profile_id ASC, version DESC, updated_at DESC"
            ).fetchall()
        latest: dict[str, TranscriptionProfileDefinition] = {}
        for row in rows:
            profile = _row_to_profile(row)
            latest.setdefault(profile.profile_id, profile)
        return tuple(latest.values())

    def get_transcription_profile(self, profile_id: str) -> TranscriptionProfileDefinition | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM transcription_profiles
                WHERE lower(profile_id) = ?
                ORDER BY version DESC, updated_at DESC
                LIMIT 1
                """,
                (profile_id.strip().lower(),),
            ).fetchone()
        return _row_to_profile(row) if row else None

    def upsert_transcription_profile(self, profile: TranscriptionProfileDefinition) -> TranscriptionProfileDefinition:
        payload = _profile_row(profile)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO transcription_profiles (
                    id, profile_id, display_name, description, model_component_id,
                    model_revision, device_policy, cpu_compute_type, gpu_compute_type,
                    beam_size, vad_policy, language_detection, word_timestamps,
                    segment_timestamps, batching_policy, minimum_ram_gb, minimum_vram_gb,
                    recommended_vram_gb, estimated_disk_bytes, status, version,
                    reviewed_at, created_at, updated_at
                ) VALUES (
                    :id, :profile_id, :display_name, :description, :model_component_id,
                    :model_revision, :device_policy, :cpu_compute_type, :gpu_compute_type,
                    :beam_size, :vad_policy, :language_detection, :word_timestamps,
                    :segment_timestamps, :batching_policy, :minimum_ram_gb, :minimum_vram_gb,
                    :recommended_vram_gb, :estimated_disk_bytes, :status, :version,
                    :reviewed_at, :created_at, :updated_at
                )
                ON CONFLICT(profile_id, version) DO UPDATE SET
                    display_name = excluded.display_name,
                    description = excluded.description,
                    model_component_id = excluded.model_component_id,
                    model_revision = excluded.model_revision,
                    device_policy = excluded.device_policy,
                    cpu_compute_type = excluded.cpu_compute_type,
                    gpu_compute_type = excluded.gpu_compute_type,
                    beam_size = excluded.beam_size,
                    vad_policy = excluded.vad_policy,
                    language_detection = excluded.language_detection,
                    word_timestamps = excluded.word_timestamps,
                    segment_timestamps = excluded.segment_timestamps,
                    batching_policy = excluded.batching_policy,
                    minimum_ram_gb = excluded.minimum_ram_gb,
                    minimum_vram_gb = excluded.minimum_vram_gb,
                    recommended_vram_gb = excluded.recommended_vram_gb,
                    estimated_disk_bytes = excluded.estimated_disk_bytes,
                    status = excluded.status,
                    reviewed_at = excluded.reviewed_at,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            row = connection.execute(
                "SELECT * FROM transcription_profiles WHERE profile_id = ? AND version = ?",
                (profile.profile_id, profile.version),
            ).fetchone()
        return _row_to_profile(row) if row else profile

    def list_runtime_checks(self) -> tuple[RuntimeCheckRecord, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcription_runtime_checks ORDER BY checked_at DESC, id DESC"
            ).fetchall()
        return tuple(_row_to_runtime(row) for row in rows)

    def upsert_runtime_check(self, record: RuntimeCheckRecord) -> RuntimeCheckRecord:
        payload = _runtime_row(record)
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO transcription_runtime_checks (
                    id, component_id, status, runtime_importable, runtime_version,
                    device_count, supported_compute_types_json, notes, warning_message,
                    error_code, error_message, metadata_json, checked_at, created_at,
                    updated_at
                ) VALUES (
                    :id, :component_id, :status, :runtime_importable, :runtime_version,
                    :device_count, :supported_compute_types_json, :notes, :warning_message,
                    :error_code, :error_message, :metadata_json, :checked_at, :created_at,
                    :updated_at
                )
                """,
                payload,
            )
        return record

    def append_event(self, event: ComponentEvent) -> ComponentEvent:
        payload = {
            "id": str(uuid4()),
            "event_type": event.event_type.value,
            "message_safe": event.message_safe,
            "component_id": event.component_id,
            "installation_component_id": event.installation_component_id,
            "hardware_profile_id": event.hardware_profile_id,
            "profile_id": event.profile_id,
            "severity": event.severity,
            "technical_reference": event.technical_reference,
            "payload_json": _json_dump(event.payload),
            "created_at": (event.created_at or utc_now()).isoformat(),
        }
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO component_events (
                    id, event_type, message_safe, component_id, installation_component_id,
                    hardware_profile_id, profile_id, severity, technical_reference,
                    payload_json, created_at
                ) VALUES (
                    :id, :event_type, :message_safe, :component_id, :installation_component_id,
                    :hardware_profile_id, :profile_id, :severity, :technical_reference,
                    :payload_json, :created_at
                )
                """,
                payload,
            )
        return event

    def list_events(self) -> tuple[ComponentEvent, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM component_events ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return tuple(_row_to_event(row) for row in rows)

    def latest_hardware_profile(self) -> HardwareProfile | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM hardware_profiles ORDER BY generated_at DESC, id DESC LIMIT 1"
            ).fetchone()
        return _row_to_hardware(row) if row else None
