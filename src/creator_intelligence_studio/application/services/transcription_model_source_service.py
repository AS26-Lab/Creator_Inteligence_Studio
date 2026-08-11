"""Descarga productiva de modelos de transcripcion basada en manifiestos."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from creator_intelligence_studio.application.services.download_manager_service import ComponentDownloadManagerService
from creator_intelligence_studio.domain.components.downloads import (
    ComponentDownloadOverwritePolicy,
    ComponentDownloadPriority,
    ComponentDownloadRequest,
    ComponentDownloadRetryPolicy,
    ComponentDownloadRecord,
    ComponentDownloadProgress,
    ComponentDownloadStatus,
    VerifiedComponentArtifact,
)
from creator_intelligence_studio.domain.components.entities import ComponentCatalogEntry, ComponentInstallationStatus
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.transcription.model_sources import (
    TranscriptionModelSourceFile,
    TranscriptionModelSourceManifest,
    get_transcription_model_source_manifest,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


@dataclass(frozen=True, slots=True)
class ProductModelDownloadProgress:
    total_files: int
    completed_files: int
    downloaded_bytes: int
    total_bytes: int
    stage: str

    def to_dict(self) -> dict[str, object]:
        return {
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "stage": self.stage,
        }


@dataclass(frozen=True, slots=True)
class ProductModelDownloadResult:
    download_id: str
    component_id: str
    manifest_revision: str
    source_repository: str
    source_page: str
    status: str
    verified_artifact: VerifiedComponentArtifact | None
    total_bytes: int
    downloaded_bytes: int
    source_files: tuple[dict[str, object], ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "download_id": self.download_id,
            "component_id": self.component_id,
            "manifest_revision": self.manifest_revision,
            "source_repository": self.source_repository,
            "source_page": self.source_page,
            "status": self.status,
            "verified_artifact": self.verified_artifact.to_dict() if self.verified_artifact else None,
            "total_bytes": self.total_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "source_files": list(self.source_files),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "reason": self.reason,
        }


class TranscriptionModelProductSourceService:
    """Orquesta la descarga productiva de modelos desde un manifiesto exacto."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: ComponentManagerRepository,
        download_service: ComponentDownloadManagerService,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.download_service = download_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.transcription.model_source")

    def manifest_for(self, component_id: str) -> TranscriptionModelSourceManifest | None:
        manifest = get_transcription_model_source_manifest(component_id)
        if manifest is None:
            return None
        entry = self.repository.get_catalog_entry(component_id)
        if entry is None or (entry.source_type or "").strip().lower() != "approved_product_source":
            return None
        return manifest

    def product_source_supported(self, component_id: str) -> bool:
        return self.manifest_for(component_id) is not None

    def _component_entry(self, component_id: str) -> ComponentCatalogEntry:
        entry = self.repository.get_catalog_entry(component_id)
        if entry is None:
            raise ValueError("El componente no existe en el catalogo.")
        return entry

    def _downloads_root(self, component_id: str) -> Path:
        return self.paths.downloads_directory / "transcription-models" / component_id.strip().lower()

    def _staging_root(self, component_id: str, download_id: str) -> Path:
        return self._downloads_root(component_id) / f".staging-{download_id}"

    def _model_source_download_request(self, *, component_id: str, file_entry: TranscriptionModelSourceFile, catalog_version: int) -> ComponentDownloadRequest:
        entry = self._component_entry(component_id)
        return ComponentDownloadRequest(
            component_id=f"{component_id}.{Path(file_entry.relative_path).name}",
            catalog_version=catalog_version,
            source_url=file_entry.source_url,
            expected_sha256=file_entry.expected_sha256,
            expected_download_bytes=file_entry.expected_bytes,
            destination_logical_location=f"model_source:{component_id}:{file_entry.relative_path}",
            priority=ComponentDownloadPriority.NORMAL,
            user_initiated=True,
            retry_policy=ComponentDownloadRetryPolicy(),
            overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
            allowed_domains=entry.allowed_domains,
            allow_localhost=False,
            test_mode=False,
            connect_timeout_seconds=30.0,
            read_timeout_seconds=120.0,
            stalled_timeout_seconds=600.0,
        )

    def _write_zip(self, source_root: Path, destination_zip: Path) -> None:
        destination_zip.parent.mkdir(parents=True, exist_ok=True)
        if destination_zip.exists():
            destination_zip.unlink()
        with zipfile.ZipFile(destination_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(source_root).as_posix())

    def download(
        self,
        component_id: str,
        *,
        progress_callback: Callable[[ProductModelDownloadProgress], None] | None = None,
        cancellation_token=None,
    ) -> ProductModelDownloadResult:
        component_id = component_id.strip().lower()
        manifest = self.manifest_for(component_id)
        if manifest is None:
            raise ValueError("La fuente productiva del modelo no esta disponible.")
        catalog_entry = self._component_entry(component_id)
        download_id = uuid4().hex
        staging_root = self._staging_root(component_id, download_id)
        source_root = staging_root / manifest.repository / "snapshots" / manifest.revision
        source_root.mkdir(parents=True, exist_ok=True)
        downloaded_bytes = 0
        warnings: list[str] = []
        errors: list[str] = []

        try:
            for index, file_entry in enumerate(manifest.files, start=1):
                if cancellation_token is not None and cancellation_token.cancelled():
                    raise RuntimeError("cancelled")
                request = self._model_source_download_request(
                    component_id=component_id,
                    file_entry=file_entry,
                    catalog_version=catalog_entry.catalog_version,
                )
                record = self.download_service.start_download(request)
                terminal = self.download_service.wait_for_terminal(record.download_id, timeout_seconds=3600.0)
                if terminal is None:
                    raise RuntimeError("La descarga del archivo excedio el tiempo de espera.")
                if terminal.status.value != "completed":
                    error_text = terminal.error.message_safe if terminal.error else "La descarga del archivo fallo."
                    errors.append(error_text)
                    raise RuntimeError(error_text)
                artifact = self.download_service.verified_artifact(record.download_id)
                if artifact is None:
                    raise RuntimeError("No se pudo recuperar el artefacto verificado del archivo.")
                source_file = Path(artifact.verified_artifact_path)
                if not source_file.exists():
                    raise FileNotFoundError(f"Falta el archivo verificado descargado: {source_file}")
                destination_file = staging_root / file_entry.relative_path
                _copy_file(source_file, destination_file)
                if _sha256_file(destination_file).lower() != file_entry.expected_sha256.lower():
                    raise RuntimeError(f"El archivo descargado no coincide: {file_entry.relative_path}")
                downloaded_bytes += file_entry.expected_bytes
                if progress_callback is not None:
                    progress_callback(
                        ProductModelDownloadProgress(
                            total_files=len(manifest.files),
                            completed_files=index,
                            downloaded_bytes=downloaded_bytes,
                            total_bytes=manifest.total_expected_bytes,
                            stage=file_entry.relative_path,
                        )
                    )

            zip_path = self._downloads_root(component_id) / f"{download_id}.verified.zip"
            self._write_zip(staging_root, zip_path)
            zip_sha256 = _sha256_file(zip_path)
            artifact = VerifiedComponentArtifact(
                download_id=download_id,
                component_id=component_id,
                verified_artifact_path=str(zip_path),
                partial_path=None,
                sha256=zip_sha256,
                size_bytes=zip_path.stat().st_size,
                created_at=_now(),
                verified_at=_now(),
                source_url=manifest.source_page,
            )
            record_now = _now()
            record = ComponentDownloadRecord(
                download_id=download_id,
                identity_key=request.identity_key(),
                component_id=component_id,
                catalog_version=catalog_entry.catalog_version,
                source_url=manifest.source_page,
                expected_sha256=manifest.expected_sha256,
                expected_download_bytes=manifest.total_expected_bytes,
                destination_logical_location=f"model_source:{component_id}",
                priority=ComponentDownloadPriority.NORMAL,
                user_initiated=True,
                retry_policy=ComponentDownloadRetryPolicy(),
                overwrite_policy=ComponentDownloadOverwritePolicy.REJECT,
                allowed_domains=catalog_entry.allowed_domains,
                allow_localhost=False,
                test_mode=False,
                max_redirects=3,
                connect_timeout_seconds=10.0,
                read_timeout_seconds=10.0,
                stalled_timeout_seconds=30.0,
                chunk_size_bytes=1024 * 256,
                safety_margin_bytes=8 * 1024 * 1024,
                status=ComponentDownloadStatus.COMPLETED,
                progress=ComponentDownloadProgress(
                    downloaded_bytes=manifest.total_expected_bytes,
                    total_bytes=manifest.total_expected_bytes,
                    percentage=100.0,
                    started_at=record_now,
                    updated_at=record_now,
                ),
                partial_path=str(self._downloads_root(component_id) / f"{download_id}.partial"),
                verified_artifact_path=str(zip_path),
                bytes_received=manifest.total_expected_bytes,
                attempts=1,
                max_attempts=1,
                verification_status="verified",
                verified_sha256=zip_sha256,
                verified_size_bytes=zip_path.stat().st_size,
                created_at=record_now,
                updated_at=record_now,
                completed_at=record_now,
                verified_at=record_now,
                metadata={
                    "source_repository": manifest.repository,
                    "source_page": manifest.source_page,
                    "source_files": [file.to_dict() for file in manifest.files],
                    "product_source": True,
                },
            )
            self.download_service.repository.save_record(record)
            return ProductModelDownloadResult(
                download_id=download_id,
                component_id=component_id,
                manifest_revision=manifest.revision,
                source_repository=manifest.repository,
                source_page=manifest.source_page,
                status="completed",
                verified_artifact=artifact,
                total_bytes=manifest.total_expected_bytes,
                downloaded_bytes=downloaded_bytes,
                source_files=tuple(file.to_dict() for file in manifest.files),
            )
        except Exception as exc:
            self.logger.warning("No se pudo descargar la fuente productiva del modelo %s: %s", component_id, exc)
            warnings.append("La descarga del modelo no pudo completarse.")
            errors.append(str(exc))
            return ProductModelDownloadResult(
                download_id=download_id,
                component_id=component_id,
                manifest_revision=manifest.revision,
                source_repository=manifest.repository,
                source_page=manifest.source_page,
                status="failed",
                verified_artifact=None,
                total_bytes=manifest.total_expected_bytes,
                downloaded_bytes=downloaded_bytes,
                source_files=tuple(file.to_dict() for file in manifest.files),
                warnings=tuple(warnings),
                errors=tuple(errors),
                reason=str(exc),
            )
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
