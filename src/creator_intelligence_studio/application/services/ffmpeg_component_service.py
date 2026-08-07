"""Boundary administrado para FFmpeg y FFprobe."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import wave
import zipfile
import stat
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterator
from uuid import uuid4

from creator_intelligence_studio.domain.components.entities import (
    ComponentEvent,
    ComponentEventType,
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.downloads import VerifiedComponentArtifact
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.media.value_objects import MediaToolInfo
from creator_intelligence_studio.infrastructure.audio.ffmpeg_audio_extractor import FFmpegAudioExtractionError
from creator_intelligence_studio.infrastructure.media.ffprobe_client import FFprobeClient
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaTools
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


MAX_ARCHIVE_MEMBERS = 256
MAX_ARCHIVE_EXTRACTED_BYTES = 256 * 1024 * 1024
MAX_VERSION_TEXT_BYTES = 1024
FFMPEG_COMPONENT_ID = "ffmpeg"
FFPROBE_COMPONENT_ID = "ffprobe"
FFMPEG_BUNDLE_ROOT = "ffmpeg"
FFMPEG_PACKAGE_KIND = "local_package"


@dataclass(frozen=True, slots=True)
class FFmpegVersionInfo:
    raw_line: str | None
    parsed_version: str | None
    build_metadata: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_line": self.raw_line,
            "parsed_version": self.parsed_version,
            "build_metadata": self.build_metadata,
        }


@dataclass(frozen=True, slots=True)
class FFmpegHealthCheckResult:
    state: str
    ffmpeg_exists: bool
    ffprobe_exists: bool
    ffmpeg_version: FFmpegVersionInfo | None
    ffprobe_version: FFmpegVersionInfo | None
    ffmpeg_path: str | None
    ffprobe_path: str | None
    fixture_path: str | None
    warnings: tuple[str, ...] = ()
    error_message: str | None = None
    detected_architecture: str | None = None
    verified_at: datetime | None = None

    @property
    def healthy(self) -> bool:
        return self.state in {"ready", "ready_with_warnings"}

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "ffmpeg_exists": self.ffmpeg_exists,
            "ffprobe_exists": self.ffprobe_exists,
            "ffmpeg_version": self.ffmpeg_version.to_dict() if self.ffmpeg_version else None,
            "ffprobe_version": self.ffprobe_version.to_dict() if self.ffprobe_version else None,
            "ffmpeg_path": self.ffmpeg_path,
            "ffprobe_path": self.ffprobe_path,
            "fixture_path": self.fixture_path,
            "warnings": list(self.warnings),
            "error_message": self.error_message,
            "detected_architecture": self.detected_architecture,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


@dataclass(frozen=True, slots=True)
class FFmpegResolutionReport:
    state: str
    installation_type: str
    source: str
    reason: str
    ffmpeg: MediaToolInfo
    ffprobe: MediaToolInfo
    ffmpeg_path: str | None
    ffprobe_path: str | None
    version: str | None
    managed_location: str | None
    health: FFmpegHealthCheckResult
    warnings: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.health.healthy and self.ffmpeg.available and self.ffprobe.available

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "installation_type": self.installation_type,
            "source": self.source,
            "reason": self.reason,
            "ffmpeg": self.ffmpeg.to_dict(),
            "ffprobe": self.ffprobe.to_dict(),
            "ffmpeg_path": self.ffmpeg_path,
            "ffprobe_path": self.ffprobe_path,
            "version": self.version,
            "managed_location": self.managed_location,
            "health": self.health.to_dict(),
            "warnings": list(self.warnings),
            "alternatives": list(self.alternatives),
            "available": self.available,
        }


@dataclass(frozen=True, slots=True)
class FFmpegInstallResult:
    state: str
    source_path: str | None
    staged_path: str | None
    active_path: str | None
    installation: ComponentInstallation | None
    health: FFmpegHealthCheckResult | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "source_path": self.source_path,
            "staged_path": self.staged_path,
            "active_path": self.active_path,
            "installation": self.installation.to_dict() if self.installation else None,
            "health": self.health.to_dict() if self.health else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class FFmpegRemovalResult:
    state: str
    removed_path: str | None
    removed_records: tuple[str, ...]
    fallback: FFmpegResolutionReport | None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "removed_path": self.removed_path,
            "removed_records": list(self.removed_records),
            "fallback": self.fallback.to_dict() if self.fallback else None,
            "reason": self.reason,
        }


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _detect_architecture() -> str | None:
    architecture = os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ.get("PROCESSOR_ARCHITECTURE")
    if architecture:
        return architecture
    try:
        return os.uname().machine  # type: ignore[attr-defined]
    except AttributeError:
        return None


def _normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    return normalized or None


def _parse_version_line(output: str | None) -> FFmpegVersionInfo:
    first_line = _normalize_text(output.splitlines()[0] if output else None)
    if not first_line:
        return FFmpegVersionInfo(raw_line=None, parsed_version=None, build_metadata=None)
    version_match = re.search(r"(?:ffmpeg|ffprobe)\s+version\s+([^\s]+)", first_line, re.IGNORECASE)
    parsed_version = version_match.group(1) if version_match else None
    build_metadata = None
    if parsed_version:
        tail = first_line.split(parsed_version, 1)[1].strip()
        build_metadata = tail or None
    return FFmpegVersionInfo(raw_line=first_line[:MAX_VERSION_TEXT_BYTES], parsed_version=parsed_version, build_metadata=build_metadata)


def _safe_resolve(path: Path) -> Path:
    return path.resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        return _safe_resolve(path).is_relative_to(_safe_resolve(root))
    except Exception:
        return False


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Symlink no permitido: {path}")


def _copy_directory_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for current_root, dirnames, filenames in os.walk(source):
        current_root_path = Path(current_root)
        _reject_symlink(current_root_path)
        relative_root = current_root_path.relative_to(source)
        target_root = destination / relative_root
        target_root.mkdir(parents=True, exist_ok=True)
        for dirname in list(dirnames):
            source_dir = current_root_path / dirname
            _reject_symlink(source_dir)
        for filename in filenames:
            source_file = current_root_path / filename
            _reject_symlink(source_file)
            target_file = target_root / filename
            shutil.copy2(source_file, target_file)


def _safe_extract_zip(source: Path, destination: Path) -> int:
    extracted_size = 0
    seen_paths: set[str] = set()
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("El archivo contiene demasiados elementos.")
        for member in members:
            if member.is_dir():
                continue
            member_name = member.filename.replace("\\", "/")
            pure = PurePosixPath(member_name)
            if pure.is_absolute() or member_name.startswith("/") or re.match(r"^[a-zA-Z]:", member_name):
                raise ValueError(f"Ruta absoluta no permitida: {member.filename}")
            if ".." in pure.parts:
                raise ValueError(f"Traversal no permitido: {member.filename}")
            normalized = str(pure)
            if normalized in seen_paths:
                raise ValueError(f"Nombre duplicado conflictivo: {member.filename}")
            seen_paths.add(normalized)
            if member.file_size < 0:
                raise ValueError(f"Tamano invalido: {member.filename}")
            extracted_size += int(member.file_size)
            if extracted_size > MAX_ARCHIVE_EXTRACTED_BYTES:
                raise ValueError("El archivo excede el tamano maximo permitido.")
            external_attr = member.external_attr >> 16
            if external_attr and stat.S_ISLNK(external_attr):  # type: ignore[name-defined]
                raise ValueError(f"Symlink no permitido: {member.filename}")
            target_path = _safe_resolve(destination / pure)
            if not _is_within(target_path, destination):
                raise ValueError(f"Extraccion fuera del staging: {member.filename}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return extracted_size


def _snapshot_fixture(root: Path) -> Path:
    fixture_dir = root / "health-fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = fixture_dir / "ffmpeg_health.wav"
    if fixture_path.exists():
        return fixture_path
    with wave.open(str(fixture_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 1600)
    return fixture_path


class FFmpegHealthChecker:
    """Verifica FFmpeg y FFprobe sin trabajo pesado."""

    def __init__(self, *, timeout_seconds: float = 8.0) -> None:
        self.timeout_seconds = timeout_seconds

    def _run_version(self, executable: Path) -> tuple[FFmpegVersionInfo | None, str | None]:
        try:
            completed = subprocess.run(
                [str(executable), "-version"],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return None, f"timeout:{exc}"
        except (FileNotFoundError, OSError) as exc:
            return None, str(exc)
        if completed.returncode != 0:
            message = _normalize_text(completed.stderr) or _normalize_text(completed.stdout) or "codigo de salida distinto de cero"
            return None, message
        return _parse_version_line(completed.stdout), None

    def _run_ffprobe_fixture(self, ffprobe_path: Path, fixture_path: Path) -> tuple[bool, str | None]:
        try:
            completed = subprocess.run(
                [
                    str(ffprobe_path),
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(fixture_path),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return False, f"timeout:{exc}"
        except (FileNotFoundError, OSError) as exc:
            return False, str(exc)
        if completed.returncode != 0:
            message = _normalize_text(completed.stderr) or _normalize_text(completed.stdout) or "ffprobe fallo"
            return False, message
        return True, None

    def _run_ffmpeg_minimal(self, ffmpeg_path: Path, fixture_path: Path) -> tuple[bool, str | None]:
        try:
            completed = subprocess.run(
                [
                    str(ffmpeg_path),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(fixture_path),
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return False, f"timeout:{exc}"
        except (FileNotFoundError, OSError) as exc:
            return False, str(exc)
        if completed.returncode != 0:
            message = _normalize_text(completed.stderr) or _normalize_text(completed.stdout) or "ffmpeg fallo"
            return False, message
        return True, None

    def check_bundle(self, *, ffmpeg_path: Path, ffprobe_path: Path, fixture_root: Path) -> FFmpegHealthCheckResult:
        verified_at = _utc_now()
        fixture_path = _snapshot_fixture(fixture_root)
        ffmpeg_exists = ffmpeg_path.exists() and ffmpeg_path.is_file()
        ffprobe_exists = ffprobe_path.exists() and ffprobe_path.is_file()
        if not ffmpeg_exists or not ffprobe_exists:
            state = "partial" if ffmpeg_exists or ffprobe_exists else "missing"
            return FFmpegHealthCheckResult(
                state=state,
                ffmpeg_exists=ffmpeg_exists,
                ffprobe_exists=ffprobe_exists,
                ffmpeg_version=None,
                ffprobe_version=None,
                ffmpeg_path=str(ffmpeg_path) if ffmpeg_exists else None,
                ffprobe_path=str(ffprobe_path) if ffprobe_exists else None,
                fixture_path=str(fixture_path),
                warnings=(),
                error_message="Falta ffmpeg o ffprobe.",
                detected_architecture=_detect_architecture(),
                verified_at=verified_at,
            )
        ffmpeg_version, ffmpeg_error = self._run_version(ffmpeg_path)
        ffprobe_version, ffprobe_error = self._run_version(ffprobe_path)
        if ffmpeg_error or ffprobe_error:
            state = "corrupt"
            if ffmpeg_version is not None and ffprobe_version is not None:
                state = "ready_with_warnings"
            return FFmpegHealthCheckResult(
                state=state,
                ffmpeg_exists=True,
                ffprobe_exists=True,
                ffmpeg_version=ffmpeg_version,
                ffprobe_version=ffprobe_version,
                ffmpeg_path=str(ffmpeg_path),
                ffprobe_path=str(ffprobe_path),
                fixture_path=str(fixture_path),
                warnings=tuple(filter(None, (ffmpeg_error, ffprobe_error))),
                error_message=ffmpeg_error or ffprobe_error,
                detected_architecture=_detect_architecture(),
                verified_at=verified_at,
            )
        probe_ok, probe_error = self._run_ffprobe_fixture(ffprobe_path, fixture_path)
        if not probe_ok:
            return FFmpegHealthCheckResult(
                state="probe_failed",
                ffmpeg_exists=True,
                ffprobe_exists=True,
                ffmpeg_version=ffmpeg_version,
                ffprobe_version=ffprobe_version,
                ffmpeg_path=str(ffmpeg_path),
                ffprobe_path=str(ffprobe_path),
                fixture_path=str(fixture_path),
                warnings=(probe_error,) if probe_error else (),
                error_message=probe_error,
                detected_architecture=_detect_architecture(),
                verified_at=verified_at,
            )
        ffmpeg_ok, ffmpeg_error = self._run_ffmpeg_minimal(ffmpeg_path, fixture_path)
        if not ffmpeg_ok:
            return FFmpegHealthCheckResult(
                state="executable_failed",
                ffmpeg_exists=True,
                ffprobe_exists=True,
                ffmpeg_version=ffmpeg_version,
                ffprobe_version=ffprobe_version,
                ffmpeg_path=str(ffmpeg_path),
                ffprobe_path=str(ffprobe_path),
                fixture_path=str(fixture_path),
                warnings=(ffmpeg_error,) if ffmpeg_error else (),
                error_message=ffmpeg_error,
                detected_architecture=_detect_architecture(),
                verified_at=verified_at,
            )
        warnings: list[str] = []
        state = "ready"
        if ffmpeg_version is not None and ffmpeg_version.parsed_version is None:
            warnings.append("ffmpeg_version_parse_failed")
            state = "ready_with_warnings"
        if ffprobe_version is not None and ffprobe_version.parsed_version is None:
            warnings.append("ffprobe_version_parse_failed")
            state = "ready_with_warnings"
        return FFmpegHealthCheckResult(
            state=state,
            ffmpeg_exists=True,
            ffprobe_exists=True,
            ffmpeg_version=ffmpeg_version,
            ffprobe_version=ffprobe_version,
            ffmpeg_path=str(ffmpeg_path),
            ffprobe_path=str(ffprobe_path),
            fixture_path=str(fixture_path),
            warnings=tuple(warnings),
            error_message=None,
            detected_architecture=_detect_architecture(),
            verified_at=verified_at,
        )


class FFmpegManagedComponentService:
    """Boundary administrado para local install, health, removal y resolución."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: ComponentManagerRepository,
        logger=None,
        health_checker: FFmpegHealthChecker | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.logger = logger
        self.health_checker = health_checker or FFmpegHealthChecker()
        self._lease_lock = threading.Lock()
        self._active_leases: dict[str, int] = {}

    @property
    def components_root(self) -> Path:
        return self.paths.components_directory

    @property
    def managed_root(self) -> Path:
        return self.components_root / FFMPEG_BUNDLE_ROOT

    def _component_dir(self, version: str, install_id: str) -> Path:
        return self.managed_root / version / install_id

    def _managed_installations(self) -> tuple[ComponentInstallation, ...]:
        return tuple(
            installation
            for installation in self.repository.list_installations()
            if installation.component_id in {FFMPEG_COMPONENT_ID, FFPROBE_COMPONENT_ID} and installation.managed
        )

    def _active_managed_installation(self) -> ComponentInstallation | None:
        managed = [installation for installation in self._managed_installations() if installation.installation_status in {ComponentInstallationStatus.READY, ComponentInstallationStatus.MANAGED}]
        if not managed:
            return None
        managed.sort(key=lambda item: item.verified_at or item.detected_at or item.updated_at or _utc_now(), reverse=True)
        return managed[0]

    def _active_paths(self) -> tuple[Path | None, Path | None, ComponentInstallation | None]:
        installation = self._active_managed_installation()
        if installation is None or not installation.location_path:
            return None, None, installation
        root = Path(installation.location_path)
        return root / "ffmpeg.exe", root / "ffprobe.exe", installation

    def _installation_payload(
        self,
        *,
        installation_status: ComponentInstallationStatus,
        health_status: RuntimeCheckStatus,
        location_path: str | None,
        location_reference: str | None,
        installed_version: str | None,
        source: str,
        managed: bool,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ComponentInstallation:
        now = _utc_now()
        return ComponentInstallation(
            component_id=FFMPEG_COMPONENT_ID,
            installation_status=installation_status,
            installed_version=installed_version,
            revision=installed_version,
            install_type=ComponentInstallKind.MANAGED if managed else ComponentInstallKind.EXTERNALLY_DETECTED,
            location_path=location_path,
            location_reference=location_reference,
            detected_at=now,
            verified_at=now,
            health_status=health_status,
            source=source,
            managed=managed,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

    def _mirror_ffprobe_installation(self, ffmpeg_installation: ComponentInstallation) -> None:
        if ffmpeg_installation.location_path is None:
            return
        now = _utc_now()
        ffprobe_installation = ComponentInstallation(
            component_id=FFPROBE_COMPONENT_ID,
            installation_status=ffmpeg_installation.installation_status,
            installed_version=ffmpeg_installation.installed_version,
            revision=ffmpeg_installation.revision,
            install_type=ffmpeg_installation.install_type,
            location_path=ffmpeg_installation.location_path,
            location_reference=ffmpeg_installation.location_reference,
            detected_at=ffmpeg_installation.detected_at or now,
            verified_at=ffmpeg_installation.verified_at or now,
            health_status=ffmpeg_installation.health_status,
            source=ffmpeg_installation.source,
            managed=ffmpeg_installation.managed,
            last_error_code=ffmpeg_installation.last_error_code,
            last_error_message=ffmpeg_installation.last_error_message,
            metadata=dict(ffmpeg_installation.metadata),
            created_at=now,
            updated_at=now,
        )
        self.repository.upsert_installation(ffprobe_installation)

    def _cleanup_path(self, path: Path | None) -> None:
        if path is None:
            return
        shutil.rmtree(path, ignore_errors=True)

    @contextmanager
    def acquire_lease(self, component_id: str = FFMPEG_COMPONENT_ID) -> Iterator[None]:
        normalized = component_id.strip().lower()
        with self._lease_lock:
            self._active_leases[normalized] = self._active_leases.get(normalized, 0) + 1
        try:
            yield
        finally:
            with self._lease_lock:
                current = self._active_leases.get(normalized, 0) - 1
                if current <= 0:
                    self._active_leases.pop(normalized, None)
                else:
                    self._active_leases[normalized] = current

    def is_in_use(self, component_id: str = FFMPEG_COMPONENT_ID) -> bool:
        with self._lease_lock:
            return self._active_leases.get(component_id.strip().lower(), 0) > 0

    def _event(self, event_type: ComponentEventType, message_safe: str, *, payload: dict[str, object] | None = None, severity: str = "info", technical_reference: str | None = None) -> None:
        self.repository.append_event(
            ComponentEvent(
                event_type=event_type,
                message_safe=message_safe,
                component_id=FFMPEG_COMPONENT_ID,
                installation_component_id=FFMPEG_COMPONENT_ID,
                severity=severity,
                technical_reference=technical_reference,
                payload=payload or {},
                created_at=utc_now(),
            )
        )

    def _build_media_tools(
        self,
        *,
        ffmpeg_path: Path | None,
        ffprobe_path: Path | None,
        source: str,
        installation_type: str,
        health: FFmpegHealthCheckResult,
        reason: str,
        managed_location: str | None,
        version: str | None,
        warnings: tuple[str, ...] = (),
        alternatives: tuple[str, ...] = (),
    ) -> MediaTools:
        ffmpeg_info = MediaToolInfo(
            name="ffmpeg",
            path=str(ffmpeg_path) if ffmpeg_path else None,
            version=health.ffmpeg_version.parsed_version if health.ffmpeg_version and health.ffmpeg_version.parsed_version else (health.ffmpeg_version.raw_line if health.ffmpeg_version else version),
            available=health.healthy and ffmpeg_path is not None and health.ffmpeg_exists,
            error_message=health.error_message,
            installation_type=installation_type,
            source=source,
            health_status=health.state,
            managed=installation_type == "managed",
            component_id=FFMPEG_COMPONENT_ID,
            reason=reason,
        )
        ffprobe_info = MediaToolInfo(
            name="ffprobe",
            path=str(ffprobe_path) if ffprobe_path else None,
            version=health.ffprobe_version.parsed_version if health.ffprobe_version and health.ffprobe_version.parsed_version else (health.ffprobe_version.raw_line if health.ffprobe_version else version),
            available=health.healthy and ffprobe_path is not None and health.ffprobe_exists,
            error_message=health.error_message,
            installation_type=installation_type,
            source=source,
            health_status=health.state,
            managed=installation_type == "managed",
            component_id=FFPROBE_COMPONENT_ID,
            reason=reason,
        )
        return MediaTools(
            ffmpeg=ffmpeg_info,
            ffprobe=ffprobe_info,
            resolution=FFmpegResolutionReport(
                state=health.state,
                installation_type=installation_type,
                source=source,
                reason=reason,
                ffmpeg=ffmpeg_info,
                ffprobe=ffprobe_info,
                ffmpeg_path=ffmpeg_info.path,
                ffprobe_path=ffprobe_info.path,
                version=version,
                managed_location=managed_location,
                health=health,
                warnings=warnings,
                alternatives=alternatives,
            ),
        )

    def _discover_external(self) -> MediaTools:
        from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator

        locator = MediaToolLocator(settings=None, project_root=self.paths.project_root, env=os.environ)
        ffmpeg = locator.locate("ffmpeg")
        ffprobe = locator.locate("ffprobe")
        state = "unavailable"
        health = FFmpegHealthCheckResult(
            state=state,
            ffmpeg_exists=bool(ffmpeg.available and ffmpeg.path),
            ffprobe_exists=bool(ffprobe.available and ffprobe.path),
            ffmpeg_version=None,
            ffprobe_version=None,
            ffmpeg_path=ffmpeg.path,
            ffprobe_path=ffprobe.path,
            fixture_path=None,
            warnings=(),
            error_message=ffmpeg.error_message or ffprobe.error_message,
            detected_architecture=_detect_architecture(),
            verified_at=_utc_now(),
        )
        source = "external"
        reason = "external_discovery"
        if ffmpeg.available and ffprobe.available:
            health = self.health_checker.check_bundle(
                ffmpeg_path=Path(ffmpeg.path or ""),
                ffprobe_path=Path(ffprobe.path or ""),
                fixture_root=self.paths.components_directory,
            )
            state = health.state
        elif ffmpeg.available or ffprobe.available:
            state = "partial"
            health = FFmpegHealthCheckResult(
                state=state,
                ffmpeg_exists=bool(ffmpeg.available and ffmpeg.path),
                ffprobe_exists=bool(ffprobe.available and ffprobe.path),
                ffmpeg_version=None,
                ffprobe_version=None,
                ffmpeg_path=ffmpeg.path,
                ffprobe_path=ffprobe.path,
                fixture_path=None,
                warnings=(),
                error_message=ffmpeg.error_message or ffprobe.error_message or "Falta ffmpeg o ffprobe.",
                detected_architecture=_detect_architecture(),
                verified_at=_utc_now(),
            )
        return self._build_media_tools(
            ffmpeg_path=Path(ffmpeg.path) if ffmpeg.path else None,
            ffprobe_path=Path(ffprobe.path) if ffprobe.path else None,
            source=source,
            installation_type="externally_detected",
            health=health,
            reason=reason,
            managed_location=None,
            version=ffmpeg.version or ffprobe.version,
            warnings=health.warnings,
        )

    def _resolve_managed(self) -> MediaTools | None:
        ffmpeg_path, ffprobe_path, installation = self._active_paths()
        if installation is None or ffmpeg_path is None or ffprobe_path is None:
            return None
        health = self.health_checker.check_bundle(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            fixture_root=self.paths.components_directory,
        )
        source = "managed"
        reason = "managed_active"
        if not health.healthy:
            reason = "managed_health_check_failed"
        installation_type = "managed"
        version = installation.installed_version or (health.ffmpeg_version.parsed_version if health.ffmpeg_version else None)
        return self._build_media_tools(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            source=source,
            installation_type=installation_type,
            health=health,
            reason=reason,
            managed_location=installation.location_path,
            version=version,
            warnings=health.warnings,
        )

    def resolve_media_tools(self, *, prefer_external: bool = False) -> MediaTools:
        managed = None if prefer_external else self._resolve_managed()
        if managed is not None and managed.available:
            return managed
        external = self._discover_external()
        if external.available:
            if managed is not None and not managed.available:
                external = self._decorate_fallback(external=external, managed=managed)
            return external
        if managed is not None:
            return managed
        return external

    def _decorate_fallback(self, *, external: MediaTools, managed: MediaTools | None) -> MediaTools:
        if managed is None:
            return external
        resolution = external.resolution
        if resolution is None:
            return external
        warnings = tuple(dict.fromkeys((*resolution.warnings, "managed_fallback_to_external")))
        report = FFmpegResolutionReport(
            state=resolution.state,
            installation_type=resolution.installation_type,
            source=resolution.source,
            reason="external_fallback_selected",
            ffmpeg=resolution.ffmpeg,
            ffprobe=resolution.ffprobe,
            ffmpeg_path=resolution.ffmpeg_path,
            ffprobe_path=resolution.ffprobe_path,
            version=resolution.version,
            managed_location=resolution.managed_location,
            health=resolution.health,
            warnings=warnings,
            alternatives=tuple(dict.fromkeys((*resolution.alternatives, "managed"))),
        )
        return MediaTools(ffmpeg=external.ffmpeg, ffprobe=external.ffprobe, resolution=report)

    def status(self) -> FFmpegResolutionReport:
        resolution = self.resolve_media_tools().resolution
        if resolution is None:
            raise RuntimeError("La resolucion de FFmpeg no devolvio un reporte.")
        return resolution

    def verify(self) -> FFmpegHealthCheckResult:
        resolution = self.resolve_media_tools().resolution
        if resolution is None:
            raise RuntimeError("La resolucion de FFmpeg no devolvio un reporte.")
        return resolution.health

    def verify_local(self) -> FFmpegInstallResult:
        installation = self._active_managed_installation()
        if installation is None or not installation.location_path:
            health = self.verify()
            return FFmpegInstallResult(
                state=health.state,
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health=health,
                warnings=health.warnings,
                errors=(health.error_message,) if health.error_message else (),
                reason="not_installed",
            )
        ffmpeg_path = Path(installation.location_path) / "ffmpeg.exe"
        ffprobe_path = Path(installation.location_path) / "ffprobe.exe"
        health = self.health_checker.check_bundle(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            fixture_root=self.paths.components_directory,
        )
        status = ComponentInstallationStatus.READY if health.healthy else ComponentInstallationStatus.REPAIR_REQUIRED
        refreshed = ComponentInstallation(
            component_id=installation.component_id,
            installation_status=status,
            installed_version=installation.installed_version,
            revision=installation.revision,
            install_type=installation.install_type,
            location_path=installation.location_path,
            location_reference=installation.location_reference,
            detected_at=installation.detected_at,
            verified_at=health.verified_at or _utc_now(),
            health_status=RuntimeCheckStatus.READY if health.healthy else RuntimeCheckStatus.FAILED,
            source=installation.source,
            managed=installation.managed,
            last_error_code=None if health.healthy else "health_check_failed",
            last_error_message=None if health.healthy else health.error_message,
            metadata={
                **dict(installation.metadata),
                "health": health.to_dict(),
                "verification": "local",
            },
            created_at=installation.created_at,
            updated_at=_utc_now(),
        )
        refreshed = self.repository.upsert_installation(refreshed)
        self.repository.upsert_installation(
            ComponentInstallation(
                component_id=FFPROBE_COMPONENT_ID,
                installation_status=refreshed.installation_status,
                installed_version=refreshed.installed_version,
                revision=refreshed.revision,
                install_type=refreshed.install_type,
                location_path=refreshed.location_path,
                location_reference=refreshed.location_reference,
                detected_at=refreshed.detected_at,
                verified_at=refreshed.verified_at,
                health_status=refreshed.health_status,
                source=refreshed.source,
                managed=refreshed.managed,
                last_error_code=refreshed.last_error_code,
                last_error_message=refreshed.last_error_message,
                metadata=dict(refreshed.metadata),
                created_at=refreshed.created_at,
                updated_at=refreshed.updated_at,
            )
        )
        return FFmpegInstallResult(
            state="ready" if health.healthy else "failed",
            source_path=installation.source,
            staged_path=None,
            active_path=installation.location_path,
            installation=refreshed,
            health=health,
            warnings=health.warnings,
            errors=(health.error_message,) if health.error_message else (),
            reason="verified" if health.healthy else "health_check_failed",
        )

    def _staging_root(self) -> Path:
        root = self.components_root / ".staging"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _normalize_package_version(self, version: str | None) -> str:
        normalized = _normalize_text(version) or "unversioned"
        return re.sub(r"[^A-Za-z0-9._-]+", "_", normalized)

    def _copy_source_to_staging(self, source_path: Path, staging_dir: Path) -> Path:
        if source_path.is_dir():
            _copy_directory_tree(source_path, staging_dir)
            return staging_dir
        if source_path.suffix.lower() != ".zip":
            raise ValueError("Solo se aceptan paquetes ZIP o directorios locales.")
        staging_dir.mkdir(parents=True, exist_ok=False)
        _safe_extract_zip(source_path, staging_dir)
        return staging_dir

    def _require_bundle(self, root: Path) -> tuple[Path, Path]:
        ffmpeg_path = root / "ffmpeg.exe"
        ffprobe_path = root / "ffprobe.exe"
        if not ffmpeg_path.exists():
            raise ValueError("Falta ffmpeg.exe en el paquete local.")
        if not ffprobe_path.exists():
            raise ValueError("Falta ffprobe.exe en el paquete local.")
        return ffmpeg_path, ffprobe_path

    def _persist_managed_installation(
        self,
        *,
        final_root: Path,
        health: FFmpegHealthCheckResult,
        source_path: Path,
        source_kind: str,
        source_label: str | None,
        warning_messages: tuple[str, ...] = (),
    ) -> ComponentInstallation:
        now = _utc_now()
        installation = ComponentInstallation(
            component_id=FFMPEG_COMPONENT_ID,
            installation_status=ComponentInstallationStatus.READY if health.healthy else ComponentInstallationStatus.REPAIR_REQUIRED,
            installed_version=health.ffmpeg_version.parsed_version if health.ffmpeg_version else None,
            revision=health.ffmpeg_version.parsed_version if health.ffmpeg_version else None,
            install_type=ComponentInstallKind.MANAGED,
            location_path=str(final_root),
            location_reference="managed_root",
            detected_at=now,
            verified_at=health.verified_at or now,
            health_status=RuntimeCheckStatus.READY if health.healthy else RuntimeCheckStatus.FAILED,
            source=source_kind,
            managed=True,
            last_error_code=None if health.healthy else "health_check_failed",
            last_error_message=None if health.healthy else health.error_message,
            metadata={
                "source_path": str(source_path),
                "source_kind": source_kind,
                "source_label": source_label,
                "health": health.to_dict(),
                "warnings": list(warning_messages or health.warnings),
            },
            created_at=now,
            updated_at=now,
        )
        self.repository.upsert_installation(installation)
        self._mirror_ffprobe_installation(installation)
        return installation

    def install_local(self, source_path: str | Path | VerifiedComponentArtifact, *, source_label: str | None = None) -> FFmpegInstallResult:
        if isinstance(source_path, VerifiedComponentArtifact):
            source = Path(source_path.verified_artifact_path)
            source_label = source_label or source_path.download_id
        else:
            source = Path(source_path)
        self._event(ComponentEventType.FFMPEG_MANAGED_INSTALL_STARTED, "Inicio de instalacion local de FFmpeg.", payload={"source_path": str(source)})
        if not source.exists():
            return FFmpegInstallResult(
                state="source_missing",
                source_path=str(source),
                staged_path=None,
                active_path=None,
                installation=None,
                health=None,
                errors=("La fuente local no existe.",),
                reason="source_missing",
            )
        if self.is_in_use():
            return FFmpegInstallResult(
                state="in_use",
                source_path=str(source),
                staged_path=None,
                active_path=None,
                installation=None,
                health=None,
                errors=("FFmpeg esta en uso y no se puede instalar ahora.",),
                reason="in_use",
            )
        install_id = uuid4().hex
        version_dir = self._normalize_package_version(source_label or source.stem)
        final_root = self._component_dir(version_dir, install_id)
        staging_root = self._staging_root() / install_id
        if staging_root.exists():
            shutil.rmtree(staging_root, ignore_errors=True)
        staging_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._copy_source_to_staging(source, staging_root)
            self._event(ComponentEventType.FFMPEG_MANAGED_INSTALL_STAGED, "Paquete local extraido a staging.", payload={"staging_path": str(staging_root)})
            ffmpeg_path, ffprobe_path = self._require_bundle(staging_root)
            health = self.health_checker.check_bundle(
                ffmpeg_path=ffmpeg_path,
                ffprobe_path=ffprobe_path,
                fixture_root=self.paths.components_directory,
            )
            if not health.healthy:
                raise FFmpegAudioExtractionError(health.error_message or "La validacion de FFmpeg fallo.")
            final_root.parent.mkdir(parents=True, exist_ok=True)
            if final_root.exists():
                shutil.rmtree(final_root, ignore_errors=True)
            staging_root.replace(final_root)
            installation = self._persist_managed_installation(
                final_root=final_root,
                health=health,
                source_path=source,
                source_kind=FFMPEG_PACKAGE_KIND,
                source_label=source_label,
            )
            self._event(
                ComponentEventType.FFMPEG_MANAGED_ACTIVATED,
                "FFmpeg administrado activado.",
                payload={"active_path": str(final_root), "version": health.ffmpeg_version.parsed_version if health.ffmpeg_version else None},
            )
            return FFmpegInstallResult(
                state="ready",
                source_path=str(source),
                staged_path=str(staging_root),
                active_path=str(final_root),
                installation=installation,
                health=health,
                warnings=health.warnings,
            )
        except Exception as exc:
            shutil.rmtree(staging_root, ignore_errors=True)
            self._event(
                ComponentEventType.FFMPEG_MANAGED_INSTALL_FAILED,
                "La instalacion administrada de FFmpeg fallo.",
                severity="error",
                payload={"source_path": str(source), "error": str(exc)},
            )
            return FFmpegInstallResult(
                state="failed",
                source_path=str(source),
                staged_path=str(staging_root),
                active_path=str(final_root),
                installation=None,
                health=None,
                errors=(str(exc),),
                reason="install_failed",
            )

    def repair_local(self, source_path: str | Path | None = None, *, source_label: str | None = None) -> FFmpegInstallResult:
        installation = self._active_managed_installation()
        if installation is None:
            return FFmpegInstallResult(
                state="repair_source_unavailable",
                source_path=str(source_path) if source_path else None,
                staged_path=None,
                active_path=None,
                installation=None,
                health=None,
                errors=("No existe una instalacion administrada para reparar.",),
                reason="repair_source_unavailable",
            )
        old_root = Path(installation.location_path) if installation.location_path else None
        if source_path is None:
            stored_source = installation.metadata.get("source_path") if installation.metadata else None
            if not stored_source:
                return FFmpegInstallResult(
                    state="repair_source_unavailable",
                    source_path=None,
                    staged_path=None,
                    active_path=installation.location_path,
                    installation=installation,
                    health=None,
                    errors=("No hay una fuente local conservada para reparar.",),
                    reason="repair_source_unavailable",
                )
            source_path = str(stored_source)
        self._event(ComponentEventType.FFMPEG_REPAIR_STARTED, "Inicio de reparacion local de FFmpeg.", payload={"source_path": str(source_path)})
        result = self.install_local(source_path, source_label=source_label)
        if result.health and result.health.healthy:
            if old_root is not None and old_root.exists():
                shutil.rmtree(old_root, ignore_errors=True)
            self._event(ComponentEventType.FFMPEG_REPAIR_COMPLETED, "Reparacion local de FFmpeg completada.", payload={"active_path": result.active_path, "source_path": str(source_path)})
        return result

    def relocate(self, destination_components_root: str | Path) -> FFmpegInstallResult:
        installation = self._active_managed_installation()
        if installation is None or not installation.location_path:
            return FFmpegInstallResult(
                state="relocation_unavailable",
                source_path=None,
                staged_path=None,
                active_path=None,
                installation=None,
                health=None,
                errors=("No existe una instalacion administrada activa para mover.",),
                reason="relocation_unavailable",
            )
        destination_root = Path(destination_components_root)
        if self.is_in_use():
            return FFmpegInstallResult(
                state="in_use",
                source_path=installation.location_path,
                staged_path=None,
                active_path=installation.location_path,
                installation=installation,
                health=None,
                errors=("FFmpeg esta en uso y no se puede mover ahora.",),
                reason="in_use",
            )
        source_root = Path(installation.location_path)
        target_root = destination_root / FFMPEG_BUNDLE_ROOT / source_root.parent.name / source_root.name
        staged_root = destination_root / ".staging" / uuid4().hex
        try:
            if staged_root.exists():
                shutil.rmtree(staged_root, ignore_errors=True)
            shutil.copytree(source_root, staged_root)
            ffmpeg_path, ffprobe_path = self._require_bundle(staged_root)
            health = self.health_checker.check_bundle(
                ffmpeg_path=ffmpeg_path,
                ffprobe_path=ffprobe_path,
                fixture_root=destination_root,
            )
            if not health.healthy:
                raise FFmpegAudioExtractionError(health.error_message or "La validacion tras mover fallo.")
            target_root.parent.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(target_root, ignore_errors=True)
            staged_root.replace(target_root)
            moved = self._persist_managed_installation(
                final_root=target_root,
                health=health,
                source_path=Path(installation.metadata.get("source_path") or source_root),
                source_kind=str(installation.source or FFMPEG_PACKAGE_KIND),
                source_label=source_root.name,
            )
            shutil.rmtree(source_root, ignore_errors=True)
            return FFmpegInstallResult(
                state="ready",
                source_path=str(source_root),
                staged_path=str(staged_root),
                active_path=str(target_root),
                installation=moved,
                health=health,
                warnings=health.warnings,
            )
        except Exception as exc:
            shutil.rmtree(staged_root, ignore_errors=True)
            return FFmpegInstallResult(
                state="failed",
                source_path=str(source_root),
                staged_path=str(staged_root),
                active_path=str(source_root),
                installation=installation,
                health=None,
                errors=(str(exc),),
                reason="relocation_failed",
            )

    def remove(self) -> FFmpegRemovalResult:
        installation = self._active_managed_installation()
        if installation is None:
            return FFmpegRemovalResult(
                state="missing",
                removed_path=None,
                removed_records=(),
                fallback=self.resolve_media_tools(),
                reason="not_installed",
            )
        if self.is_in_use():
            return FFmpegRemovalResult(
                state="in_use",
                removed_path=installation.location_path,
                removed_records=(),
                fallback=None,
                reason="in_use",
            )
        removed_records: list[str] = []
        if installation.location_path:
            shutil.rmtree(Path(installation.location_path), ignore_errors=True)
            removed_records.append(installation.component_id)
        missing = ComponentInstallation(
            component_id=FFMPEG_COMPONENT_ID,
            installation_status=ComponentInstallationStatus.MISSING,
            installed_version=None,
            revision=None,
            install_type=ComponentInstallKind.MANAGED,
            location_path=None,
            location_reference=None,
            detected_at=_utc_now(),
            verified_at=_utc_now(),
            health_status=RuntimeCheckStatus.NOT_CHECKED,
            source=None,
            managed=True,
            last_error_code="removed",
            last_error_message="La instalacion administrada fue eliminada.",
            metadata={},
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        self.repository.upsert_installation(missing)
        self.repository.upsert_installation(
            ComponentInstallation(
                component_id=FFPROBE_COMPONENT_ID,
                installation_status=ComponentInstallationStatus.MISSING,
                installed_version=None,
                revision=None,
                install_type=ComponentInstallKind.MANAGED,
                location_path=None,
                location_reference=None,
                detected_at=_utc_now(),
                verified_at=_utc_now(),
                health_status=RuntimeCheckStatus.NOT_CHECKED,
                source=None,
                managed=True,
                last_error_code="removed",
                last_error_message="La instalacion administrada fue eliminada.",
                metadata={},
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
        )
        self._event(ComponentEventType.FFMPEG_REMOVED, "FFmpeg administrado eliminado.", payload={"removed_path": installation.location_path})
        fallback = self.resolve_media_tools(prefer_external=True)
        if fallback.available:
            self._event(ComponentEventType.FFMPEG_FALLBACK_SELECTED, "Se selecciono una instalacion externa tras eliminar FFmpeg administrado.", payload={"fallback_path": fallback.ffmpeg.path})
        return FFmpegRemovalResult(
            state="removed" if not fallback.available else "fallback_selected",
            removed_path=installation.location_path,
            removed_records=tuple(removed_records),
            fallback=fallback if fallback.available else None,
            reason="removed",
        )
