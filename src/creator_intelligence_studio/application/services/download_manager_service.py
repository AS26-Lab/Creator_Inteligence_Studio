"""Gestor resumible de descargas de componentes."""

from __future__ import annotations

import errno
import http.client
import hashlib
import ipaddress
import logging
import os
import re
import socket
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit
from uuid import uuid4

from creator_intelligence_studio.domain.components.downloads import (
    ALLOWED_DOWNLOAD_STATUS_TRANSITIONS,
    ComponentDownloadArtifact,
    ComponentDownloadError,
    ComponentDownloadErrorCategory,
    ComponentDownloadOverwritePolicy,
    ComponentDownloadProgress,
    ComponentDownloadRecord,
    ComponentDownloadRequest,
    ComponentDownloadStatus,
    ComponentDownloadRetryPolicy,
    VerifiedComponentArtifact,
    sanitize_download_url,
    validate_download_transition,
)
from creator_intelligence_studio.domain.components.entities import ComponentEvent, ComponentEventType
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.infrastructure.downloads.http_transport import (
    ComponentHTTPTransport,
    HTTPTransportError,
    HTTPTransportResponse,
    UrllibComponentHTTPTransport,
    join_redirect_url,
)
from creator_intelligence_studio.infrastructure.downloads.repository import FileSystemComponentDownloadRepository
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


DOWNLOAD_TERMINAL_STATES = {
    ComponentDownloadStatus.COMPLETED,
    ComponentDownloadStatus.CANCELLED,
    ComponentDownloadStatus.FAILED,
}

DOWNLOAD_ACTIVE_STATES = {
    ComponentDownloadStatus.QUEUED,
    ComponentDownloadStatus.PREPARING,
    ComponentDownloadStatus.DOWNLOADING,
    ComponentDownloadStatus.PAUSE_REQUESTED,
    ComponentDownloadStatus.PAUSED,
    ComponentDownloadStatus.RESUME_REQUESTED,
    ComponentDownloadStatus.VERIFYING,
    ComponentDownloadStatus.CANCEL_REQUESTED,
    ComponentDownloadStatus.INTERRUPTED,
}


@dataclass(frozen=True, slots=True)
class DownloadStatusSummary:
    record: ComponentDownloadRecord
    downloaded_bytes: int
    total_bytes: int | None
    percentage: float | None
    speed_bytes_per_second: float | None
    eta_seconds: float | None
    state: str
    source_summary: str | None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "record": self.record.to_dict(),
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "percentage": self.percentage,
            "speed_bytes_per_second": self.speed_bytes_per_second,
            "eta_seconds": self.eta_seconds,
            "state": self.state,
            "source_summary": self.source_summary,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DownloadDiskSpacePolicy:
    """Política de espacio libre para descargas."""

    safety_margin_bytes: int = 8 * 1024 * 1024

    def can_start(
        self,
        *,
        free_bytes: int | None,
        expected_download_bytes: int | None,
        partial_bytes: int = 0,
    ) -> bool:
        if free_bytes is None:
            return True
        required = max(expected_download_bytes or 0, 0) - max(partial_bytes, 0)
        required = max(required, 0) + self.safety_margin_bytes
        return free_bytes > required


class DownloadSourcePolicy:
    """Política SSRF/allowlist para orígenes de descarga."""

    def __init__(self, *, allow_localhost: bool = False, test_mode: bool = False) -> None:
        self.allow_localhost = allow_localhost
        self.test_mode = test_mode

    def _host_allowed(self, hostname: str | None, allowed_domains: tuple[str, ...]) -> bool:
        if not hostname:
            return False
        host = hostname.lower()
        if host in {"localhost", "127.0.0.1", "::1"}:
            return self.allow_localhost or self.test_mode
        if allowed_domains:
            for domain in allowed_domains:
                normalized = domain.lower().strip()
                if host == normalized or host.endswith(f".{normalized}"):
                    return True
            return False
        if self.test_mode:
            return True
        return False

    def validate(self, url: str, *, allowed_domains: tuple[str, ...]) -> None:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"}:
            raise ValueError(f"Esquema no permitido: {parts.scheme or 'vacio'}")
        if not self.test_mode and parts.scheme != "https":
            raise ValueError("En produccion solo se permiten URLs HTTPS.")
        if not self._host_allowed(parts.hostname, allowed_domains):
            raise ValueError("Destino bloqueado por la politica de origen.")
        if parts.hostname and not self.allow_localhost and not self.test_mode:
            try:
                addresses = socket.getaddrinfo(parts.hostname, None)
            except socket.gaierror as exc:
                raise ValueError(f"No se pudo resolver el destino: {parts.hostname}") from exc
            for family, *_rest, sockaddr in addresses:
                ip_text = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_text)
                except ValueError:
                    continue
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    raise ValueError("Destino bloqueado por la politica de red.")


def _utc_now() -> datetime:
    return utc_now()


def _safe_iso(dt: datetime | None) -> str | None:
    return dt.isoformat().replace("+00:00", "Z") if dt is not None else None


def _state_to_label(status: ComponentDownloadStatus) -> str:
    mapping = {
        ComponentDownloadStatus.QUEUED: "queued",
        ComponentDownloadStatus.PREPARING: "preparing",
        ComponentDownloadStatus.DOWNLOADING: "downloading",
        ComponentDownloadStatus.PAUSE_REQUESTED: "pause_requested",
        ComponentDownloadStatus.PAUSED: "paused",
        ComponentDownloadStatus.RESUME_REQUESTED: "resume_requested",
        ComponentDownloadStatus.VERIFYING: "verifying",
        ComponentDownloadStatus.COMPLETED: "completed_verified",
        ComponentDownloadStatus.CANCEL_REQUESTED: "cancel_requested",
        ComponentDownloadStatus.CANCELLED: "cancelled",
        ComponentDownloadStatus.INTERRUPTED: "interrupted",
        ComponentDownloadStatus.FAILED: "failed",
    }
    return mapping[status]


def _retryable_error_category(category: ComponentDownloadErrorCategory) -> bool:
    return category in {
        ComponentDownloadErrorCategory.CONNECTION_FAILED,
        ComponentDownloadErrorCategory.CONNECTION_TIMEOUT,
        ComponentDownloadErrorCategory.READ_TIMEOUT,
        ComponentDownloadErrorCategory.STALLED_TRANSFER,
        ComponentDownloadErrorCategory.TRUNCATED_RESPONSE,
        ComponentDownloadErrorCategory.HTTP_5XX,
        ComponentDownloadErrorCategory.RATE_LIMITED,
    }


def _error_from_exception(exc: Exception) -> ComponentDownloadError:
    if isinstance(exc, HTTPTransportError):
        message = str(exc)
        if "timed out" in message.lower():
            category = ComponentDownloadErrorCategory.CONNECTION_TIMEOUT
        else:
            category = ComponentDownloadErrorCategory.CONNECTION_FAILED
        return ComponentDownloadError(category=category, message_safe="No se pudo conectar con el origen.", details=message)
    if isinstance(exc, (http.client.IncompleteRead, http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
        return ComponentDownloadError(
            category=ComponentDownloadErrorCategory.TRUNCATED_RESPONSE,
            message_safe="La respuesta HTTP termino antes de tiempo.",
            details=str(exc),
        )
    if isinstance(exc, ValueError):
        return ComponentDownloadError(category=ComponentDownloadErrorCategory.INVALID_REQUEST, message_safe=str(exc), details=str(exc))
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.ENOSPC:
        return ComponentDownloadError(category=ComponentDownloadErrorCategory.DISK_FULL, message_safe="No hay suficiente espacio en disco.", details=str(exc))
    return ComponentDownloadError(category=ComponentDownloadErrorCategory.UNEXPECTED_ERROR, message_safe="Ocurrio un error inesperado durante la descarga.", details=str(exc))


def _parse_http_date(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip() or None


def _parse_content_range(value: str | None) -> tuple[int, int, int | None] | None:
    if not value:
        return None
    match = re.match(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", value.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2))
    total = None if match.group(3) == "*" else int(match.group(3))
    return start, end, total


class ComponentDownloadManagerService:
    """Gestion resumible y persistente de artefactos descargados."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: FileSystemComponentDownloadRepository,
        component_repository: ComponentManagerRepository | None = None,
        transport: ComponentHTTPTransport | None = None,
        logger: logging.Logger | None = None,
        max_concurrent_downloads: int = 2,
        recover_on_startup: bool = True,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.component_repository = component_repository
        self.transport = transport or UrllibComponentHTTPTransport()
        self.logger = logger or logging.getLogger("creator_intelligence_studio.downloads")
        self.max_concurrent_downloads = max(1, int(max_concurrent_downloads))
        self._semaphore = threading.BoundedSemaphore(self.max_concurrent_downloads)
        self._lock = threading.RLock()
        self._control_events: dict[str, dict[str, threading.Event]] = {}
        self._workers: dict[str, threading.Thread] = {}
        self._last_persist_at: dict[str, float] = {}
        if recover_on_startup:
            self.recover_interrupted_downloads()

    def _emit_event(
        self,
        event_type: ComponentEventType,
        message_safe: str,
        *,
        component_id: str | None = None,
        payload: dict[str, object] | None = None,
        severity: str = "info",
        technical_reference: str | None = None,
    ) -> None:
        if self.component_repository is None:
            return
        try:
            self.component_repository.append_event(
                ComponentEvent(
                    event_type=event_type,
                    message_safe=message_safe,
                    component_id=component_id,
                    severity=severity,
                    technical_reference=technical_reference,
                    payload=payload or {},
                    created_at=_utc_now(),
                )
            )
        except Exception:
            self.logger.exception("No se pudo persistir un evento de descarga.")

    def _create_paths(self, request: ComponentDownloadRequest, download_id: str) -> tuple[Path, Path, Path]:
        component_dir = self.repository.component_directory(request.component_id)
        partial_path = component_dir / f"{download_id}.partial"
        verified_path = component_dir / f"{download_id}.verified"
        metadata_path = component_dir / f"{download_id}.metadata.json"
        return partial_path, verified_path, metadata_path

    def _persist(self, record: ComponentDownloadRecord) -> ComponentDownloadRecord:
        saved = self.repository.save_record(record)
        return saved

    def _set_status(
        self,
        record: ComponentDownloadRecord,
        status: ComponentDownloadStatus,
        *,
        error: ComponentDownloadError | None = None,
        progress: ComponentDownloadProgress | None = None,
        verified_sha256: str | None = None,
        verified_size_bytes: int | None = None,
        source_etag: str | None = None,
        source_last_modified: str | None = None,
        bytes_received: int | None = None,
        attempts: int | None = None,
        verified_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        interrupted_at: datetime | None = None,
        pause_requested_at: datetime | None = None,
        resume_requested_at: datetime | None = None,
        cancel_requested_at: datetime | None = None,
        recovered_at: datetime | None = None,
        verification_status: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ComponentDownloadRecord:
        validate_download_transition(record.status, status)
        updated = replace(
            record,
            status=status,
            error=error if error is not None else record.error,
            progress=progress if progress is not None else record.progress,
            verified_sha256=verified_sha256 if verified_sha256 is not None else record.verified_sha256,
            verified_size_bytes=verified_size_bytes if verified_size_bytes is not None else record.verified_size_bytes,
            source_etag=source_etag if source_etag is not None else record.source_etag,
            source_last_modified=source_last_modified if source_last_modified is not None else record.source_last_modified,
            bytes_received=bytes_received if bytes_received is not None else record.bytes_received,
            attempts=attempts if attempts is not None else record.attempts,
            verified_at=verified_at if verified_at is not None else record.verified_at,
            completed_at=completed_at if completed_at is not None else record.completed_at,
            cancelled_at=cancelled_at if cancelled_at is not None else record.cancelled_at,
            interrupted_at=interrupted_at if interrupted_at is not None else record.interrupted_at,
            pause_requested_at=pause_requested_at if pause_requested_at is not None else record.pause_requested_at,
            resume_requested_at=resume_requested_at if resume_requested_at is not None else record.resume_requested_at,
            cancel_requested_at=cancel_requested_at if cancel_requested_at is not None else record.cancel_requested_at,
            recovered_at=recovered_at if recovered_at is not None else record.recovered_at,
            verification_status=verification_status if verification_status is not None else record.verification_status,
            metadata={**record.metadata, **(metadata or {})},
            updated_at=_utc_now(),
        )
        return self._persist(updated)

    def _control_for(self, download_id: str) -> dict[str, threading.Event]:
        with self._lock:
            control = self._control_events.get(download_id)
            if control is None:
                control = {
                    "pause": threading.Event(),
                    "cancel": threading.Event(),
                    "resume": threading.Event(),
                }
                self._control_events[download_id] = control
            return control

    def _worker_for(self, download_id: str) -> threading.Thread | None:
        with self._lock:
            return self._workers.get(download_id)

    def _register_worker(self, download_id: str, worker: threading.Thread) -> None:
        with self._lock:
            self._workers[download_id] = worker

    def _release_worker(self, download_id: str) -> None:
        with self._lock:
            self._workers.pop(download_id, None)
            self._control_events.pop(download_id, None)

    def _source_policy(self, record: ComponentDownloadRecord) -> DownloadSourcePolicy:
        return DownloadSourcePolicy(allow_localhost=record.allow_localhost, test_mode=record.test_mode)

    def _partial_size(self, partial_path: Path) -> int:
        try:
            return partial_path.stat().st_size
        except FileNotFoundError:
            return 0

    def _build_initial_record(self, request: ComponentDownloadRequest, download_id: str) -> ComponentDownloadRecord:
        partial_path, verified_path, _ = self._create_paths(request, download_id)
        now = _utc_now()
        return ComponentDownloadRecord(
            download_id=download_id,
            identity_key=request.identity_key(),
            component_id=request.component_id,
            catalog_version=request.catalog_version,
            source_url=sanitize_download_url(request.source_url),
            expected_sha256=request.expected_sha256,
            expected_download_bytes=request.expected_download_bytes,
            destination_logical_location=request.destination_logical_location,
            priority=request.priority,
            user_initiated=request.user_initiated,
            retry_policy=request.retry_policy,
            overwrite_policy=request.overwrite_policy,
            allowed_domains=request.allowed_domains,
            allow_localhost=request.allow_localhost,
            test_mode=request.test_mode,
            max_redirects=request.max_redirects,
            connect_timeout_seconds=request.connect_timeout_seconds,
            read_timeout_seconds=request.read_timeout_seconds,
            stalled_timeout_seconds=request.stalled_timeout_seconds,
            chunk_size_bytes=request.chunk_size_bytes,
            safety_margin_bytes=request.safety_margin_bytes,
            status=ComponentDownloadStatus.QUEUED,
            progress=ComponentDownloadProgress(started_at=now, updated_at=now),
            partial_path=str(partial_path),
            verified_artifact_path=str(verified_path),
            bytes_received=self._partial_size(partial_path),
            attempts=0,
            max_attempts=request.retry_policy.max_attempts,
            verification_status="pending_verification",
            created_at=now,
            updated_at=now,
        )

    def _find_duplicate(self, request: ComponentDownloadRequest) -> ComponentDownloadRecord | None:
        existing = self.repository.find_by_identity(request.identity_key())
        if existing is None:
            return None
        if existing.status in DOWNLOAD_ACTIVE_STATES:
            return existing
        if existing.status == ComponentDownloadStatus.COMPLETED and request.overwrite_policy == ComponentDownloadOverwritePolicy.REJECT:
            return existing
        return None

    def _sanitized_host(self, url: str) -> str | None:
        parts = urlsplit(url)
        return parts.hostname.lower() if parts.hostname else None

    def _validate_request(self, request: ComponentDownloadRequest) -> None:
        if not request.component_id.strip():
            raise ValueError("component_id es obligatorio.")
        if not request.source_url.strip():
            raise ValueError("source_url es obligatorio.")
        self._source_policy(request).validate(request.source_url, allowed_domains=request.allowed_domains)

    def _run_request(self, request: ComponentDownloadRequest, record: ComponentDownloadRecord) -> None:
        worker = threading.Thread(target=self._download_worker, args=(record.download_id,), daemon=True)
        self._register_worker(record.download_id, worker)
        worker.start()

    def start_download(self, request: ComponentDownloadRequest) -> ComponentDownloadRecord:
        self._validate_request(request)
        duplicate = self._find_duplicate(request)
        if duplicate is not None:
            return duplicate
        download_id = uuid4().hex
        record = self._build_initial_record(request, download_id)
        self._persist(record)
        self._emit_event(
            ComponentEventType.COMPONENT_DOWNLOAD_REQUESTED,
            "Se solicito una descarga de componente.",
            component_id=record.component_id,
            payload={"download_id": record.download_id, "source": self._sanitized_host(record.source_url)},
        )
        self._emit_event(
            ComponentEventType.COMPONENT_DOWNLOAD_QUEUED,
            "La descarga de componente quedo en cola.",
            component_id=record.component_id,
            payload={"download_id": record.download_id},
        )
        self._run_request(request, record)
        return record

    def get_download(self, download_id: str) -> ComponentDownloadRecord | None:
        return self.repository.get_record(download_id)

    def list_downloads(self) -> tuple[ComponentDownloadRecord, ...]:
        return self.repository.list_records()

    def status(self, download_id: str) -> DownloadStatusSummary | None:
        record = self.get_download(download_id)
        if record is None:
            return None
        total = record.progress.total_bytes or record.expected_download_bytes
        percentage = record.progress.percentage
        speed = record.progress.smoothed_speed_bytes_per_second or record.progress.speed_bytes_per_second
        eta = record.progress.eta_seconds
        source_summary = self._sanitized_host(record.source_url)
        return DownloadStatusSummary(
            record=record,
            downloaded_bytes=record.bytes_received,
            total_bytes=total,
            percentage=percentage,
            speed_bytes_per_second=speed,
            eta_seconds=eta,
            state=_state_to_label(record.status),
            source_summary=source_summary,
            reason=record.error.category.value if record.error else None,
        )

    def pause(self, download_id: str) -> ComponentDownloadRecord | None:
        record = self.get_download(download_id)
        if record is None:
            return None
        control = self._control_for(download_id)
        control["pause"].set()
        updated = self._set_status(
            record,
            ComponentDownloadStatus.PAUSE_REQUESTED,
            pause_requested_at=_utc_now(),
        )
        self._emit_event(
            ComponentEventType.COMPONENT_DOWNLOAD_PAUSE_REQUESTED,
            "Se solicito pausar una descarga.",
            component_id=record.component_id,
            payload={"download_id": download_id},
        )
        return updated

    def resume(self, download_id: str) -> ComponentDownloadRecord | None:
        record = self.get_download(download_id)
        if record is None:
            return None
        if record.status not in {ComponentDownloadStatus.PAUSED, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED}:
            raise ValueError("La descarga no puede reanudarse en su estado actual.")
        control = self._control_for(download_id)
        control["pause"].clear()
        control["cancel"].clear()
        control["resume"].set()
        updated = self._set_status(
            record,
            ComponentDownloadStatus.RESUME_REQUESTED,
            resume_requested_at=_utc_now(),
            metadata={"resumed_after_restart": False},
        )
        self._emit_event(
            ComponentEventType.COMPONENT_DOWNLOAD_RESUME_REQUESTED,
            "Se solicito reanudar una descarga.",
            component_id=record.component_id,
            payload={"download_id": download_id},
        )
        worker = threading.Thread(target=self._download_worker, args=(download_id,), daemon=True)
        self._register_worker(download_id, worker)
        worker.start()
        return updated

    def cancel(self, download_id: str) -> ComponentDownloadRecord | None:
        record = self.get_download(download_id)
        if record is None:
            return None
        control = self._control_for(download_id)
        control["cancel"].set()
        updated = self._set_status(
            record,
            ComponentDownloadStatus.CANCEL_REQUESTED,
            cancel_requested_at=_utc_now(),
        )
        self._emit_event(
            ComponentEventType.COMPONENT_DOWNLOAD_CANCEL_REQUESTED,
            "Se solicito cancelar una descarga.",
            component_id=record.component_id,
            payload={"download_id": download_id},
        )
        return updated

    def _finalize_terminal(
        self,
        record: ComponentDownloadRecord,
        *,
        status: ComponentDownloadStatus,
        error: ComponentDownloadError | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ComponentDownloadRecord:
        terminal_fields = {
            ComponentDownloadStatus.COMPLETED: {"completed_at": _utc_now(), "verified_at": _utc_now()},
            ComponentDownloadStatus.CANCELLED: {"cancelled_at": _utc_now()},
            ComponentDownloadStatus.INTERRUPTED: {"interrupted_at": _utc_now()},
            ComponentDownloadStatus.FAILED: {},
        }
        extra = terminal_fields.get(status, {})
        if status == ComponentDownloadStatus.CANCELLED:
            try:
                Path(record.partial_path).unlink(missing_ok=True)
            except Exception:
                pass
        final = replace(record, **extra)
        final = replace(final, status=status, error=error, metadata={**record.metadata, **(metadata or {})}, updated_at=_utc_now())
        return self._persist(final)

    def _retry_delay(self, retry_policy: ComponentDownloadRetryPolicy, attempt: int) -> float:
        delay = min(retry_policy.backoff_seconds * (2 ** max(attempt - 1, 0)), retry_policy.max_backoff_seconds)
        return max(0.0, delay)

    def _update_progress(
        self,
        record: ComponentDownloadRecord,
        *,
        downloaded_bytes: int,
        total_bytes: int | None,
        started_at: datetime,
        last_update_monotonic: float,
        smoothed_speed: float | None,
        status: ComponentDownloadStatus | None = None,
    ) -> ComponentDownloadRecord:
        elapsed = max(time.monotonic() - last_update_monotonic, 0.001)
        inst_speed = downloaded_bytes / max((datetime.now(timezone.utc) - started_at).total_seconds(), 0.001)
        speed = inst_speed
        if smoothed_speed is not None:
            speed = (0.25 * inst_speed) + (0.75 * smoothed_speed)
        percentage = None
        eta = None
        if total_bytes:
            percentage = min(100.0, (downloaded_bytes / total_bytes) * 100.0)
            remaining = max(total_bytes - downloaded_bytes, 0)
            if speed > 0:
                eta = remaining / speed
        progress = ComponentDownloadProgress(
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            percentage=percentage,
            speed_bytes_per_second=inst_speed,
            smoothed_speed_bytes_per_second=speed,
            eta_seconds=eta,
            started_at=started_at,
            updated_at=_utc_now(),
        )
        updated = replace(
            record,
            progress=progress,
            bytes_received=downloaded_bytes,
            status=status or record.status,
            updated_at=_utc_now(),
        )
        return updated

    def _should_persist(self, download_id: str, *, bytes_received: int, force: bool = False) -> bool:
        if force:
            self._last_persist_at[download_id] = time.monotonic()
            return True
        last = self._last_persist_at.get(download_id, 0.0)
        now = time.monotonic()
        if now - last >= 0.75 or bytes_received == 0:
            self._last_persist_at[download_id] = now
            return True
        return False

    def _open_follow_redirects(
        self,
        url: str,
        *,
        method: str,
        headers: dict[str, str],
        timeout_seconds: float,
        max_redirects: int,
        allowed_domains: tuple[str, ...],
        policy: DownloadSourcePolicy,
    ) -> HTTPTransportResponse:
        current_url = url
        current_headers = dict(headers)
        for _ in range(max_redirects + 1):
            policy.validate(current_url, allowed_domains=allowed_domains)
            response = self.transport.open(current_url, method=method, headers=current_headers, timeout_seconds=timeout_seconds)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                response.close()
                if not location:
                    raise ValueError("Redireccion sin Location.")
                next_url = join_redirect_url(current_url, location)
                policy.validate(next_url, allowed_domains=allowed_domains)
                current_url = next_url
                current_headers = dict(headers)
                continue
            return response
        raise ValueError("Demasiadas redirecciones.")

    def _perform_attempt(self, record: ComponentDownloadRecord, *, resume_offset: int) -> ComponentDownloadRecord:
        partial_path = Path(record.partial_path)
        verified_path = Path(record.verified_artifact_path)
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        verified_path.parent.mkdir(parents=True, exist_ok=True)
        policy = self._source_policy(record)
        headers: dict[str, str] = {}
        if resume_offset > 0:
            headers["Range"] = f"bytes={resume_offset}-"
            if record.source_etag:
                headers["If-Range"] = record.source_etag
            elif record.source_last_modified:
                headers["If-Range"] = record.source_last_modified
        response = self._open_follow_redirects(
            record.source_url,
            method="GET",
            headers=headers,
            timeout_seconds=max(record.connect_timeout_seconds, record.read_timeout_seconds),
            max_redirects=record.max_redirects,
            allowed_domains=record.allowed_domains,
            policy=policy,
        )
        try:
            if response.status_code not in {200, 206}:
                if response.status_code == 429:
                    raise RuntimeError("rate_limited")
                if 400 <= response.status_code < 500:
                    raise RuntimeError(f"http_{response.status_code}")
                if 500 <= response.status_code < 600:
                    raise RuntimeError(f"http_{response.status_code}")
                raise RuntimeError(f"http_{response.status_code}")
            response_etag = response.headers.get("etag")
            response_last_modified = _parse_http_date(response.headers.get("last-modified"))
            response_total_size = None
            content_range = _parse_content_range(response.headers.get("content-range"))
            if content_range is not None:
                response_total_size = content_range[2]
                if resume_offset > 0 and content_range[0] != resume_offset:
                    raise RuntimeError("range_invalid")
            elif response.headers.get("content-length") is not None:
                try:
                    response_total_size = int(response.headers.get("content-length") or "0")
                except ValueError:
                    response_total_size = None
                if resume_offset > 0 and response.status_code == 200:
                    response.close()
                    partial_path.unlink(missing_ok=True)
                    return self._perform_attempt(record, resume_offset=0)
            if resume_offset > 0 and record.source_etag and response_etag and response_etag != record.source_etag:
                response.close()
                partial_path.unlink(missing_ok=True)
                return self._perform_attempt(record, resume_offset=0)
            if resume_offset > 0 and record.source_last_modified and response_last_modified and response_last_modified != record.source_last_modified:
                response.close()
                partial_path.unlink(missing_ok=True)
                return self._perform_attempt(record, resume_offset=0)

            started_at = record.progress.started_at or _utc_now()
            bytes_received = resume_offset
            sha256 = hashlib.sha256()
            if resume_offset > 0 and partial_path.exists():
                with partial_path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        sha256.update(chunk)
            open_mode = "ab" if resume_offset > 0 else "wb"
            last_persist_bytes = bytes_received
            last_update_monotonic = time.monotonic()
            smoothed_speed: float | None = None
            with partial_path.open(open_mode) as handle:
                if resume_offset == 0:
                    sha256 = hashlib.sha256()
                self._emit_event(
                    ComponentEventType.COMPONENT_DOWNLOAD_STARTED,
                    "La descarga de componente comenzo.",
                    component_id=record.component_id,
                    payload={"download_id": record.download_id, "source": self._sanitized_host(record.source_url)},
                )
                current = self._set_status(
                    record,
                    ComponentDownloadStatus.DOWNLOADING,
                    source_etag=response_etag,
                    source_last_modified=response_last_modified,
                    metadata={"response_status": response.status_code},
                )
                record = current
                while True:
                    control = self._control_for(record.download_id)
                    if control["cancel"].is_set():
                        latest = self.get_download(record.download_id) or record
                        if latest.status != ComponentDownloadStatus.CANCEL_REQUESTED:
                            latest = self._set_status(latest, ComponentDownloadStatus.CANCEL_REQUESTED, cancel_requested_at=_utc_now())
                        latest = self._set_status(latest, ComponentDownloadStatus.CANCELLED, cancelled_at=_utc_now())
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_CANCELLED,
                            "La descarga fue cancelada.",
                            component_id=record.component_id,
                            payload={"download_id": record.download_id},
                        )
                        return latest
                    if control["pause"].is_set():
                        latest = self.get_download(record.download_id) or record
                        if latest.status != ComponentDownloadStatus.PAUSE_REQUESTED:
                            latest = self._set_status(latest, ComponentDownloadStatus.PAUSE_REQUESTED, pause_requested_at=_utc_now())
                        latest = self._set_status(latest, ComponentDownloadStatus.PAUSED)
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_PAUSED,
                            "La descarga quedo en pausa.",
                            component_id=record.component_id,
                            payload={"download_id": record.download_id},
                        )
                        return latest
                    chunk = response.read(record.chunk_size_bytes)
                    if not chunk:
                        break
                    try:
                        handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())
                    except OSError as exc:
                        if getattr(exc, "errno", None) == errno.ENOSPC:
                            raise
                        raise
                    sha256.update(chunk)
                    bytes_received += len(chunk)
                    now_monotonic = time.monotonic()
                    elapsed = max(now_monotonic - last_update_monotonic, 0.001)
                    inst_speed = len(chunk) / elapsed
                    smoothed_speed = inst_speed if smoothed_speed is None else (0.25 * inst_speed) + (0.75 * smoothed_speed)
                    record = self._update_progress(
                        record,
                        downloaded_bytes=bytes_received,
                        total_bytes=response_total_size or record.expected_download_bytes,
                        started_at=started_at,
                        last_update_monotonic=last_update_monotonic,
                        smoothed_speed=smoothed_speed,
                        status=ComponentDownloadStatus.DOWNLOADING,
                    )
                    last_update_monotonic = now_monotonic
                    if self._should_persist(record.download_id, bytes_received=bytes_received):
                        self._persist(record)
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_PROGRESS,
                            "La descarga de componente avanzo.",
                            component_id=record.component_id,
                            payload={"download_id": record.download_id, "bytes_received": bytes_received, "total_bytes": response_total_size or record.expected_download_bytes},
                        )
                    if response_total_size is not None and bytes_received > response_total_size:
                        raise RuntimeError("content_length_mismatch")
                if response_total_size is not None and bytes_received < response_total_size:
                    raise RuntimeError("truncated_response")
            digest = sha256.hexdigest()
            if record.expected_download_bytes is not None and bytes_received != record.expected_download_bytes:
                raise RuntimeError("content_length_mismatch")
            if record.expected_sha256 and digest.lower() != record.expected_sha256.lower():
                raise RuntimeError("sha256_mismatch")
            self._emit_event(
                ComponentEventType.COMPONENT_DOWNLOAD_VERIFICATION_STARTED,
                "La verificacion del artefacto de descarga comenzo.",
                component_id=record.component_id,
                payload={"download_id": record.download_id},
            )
            verified_path.unlink(missing_ok=True)
            os.replace(partial_path, verified_path)
            final_progress = self._update_progress(
                record,
                downloaded_bytes=bytes_received,
                total_bytes=response_total_size or record.expected_download_bytes,
                started_at=started_at,
                last_update_monotonic=last_update_monotonic,
                smoothed_speed=smoothed_speed,
                status=ComponentDownloadStatus.VERIFYING,
            )
            record = self._set_status(
                final_progress,
                ComponentDownloadStatus.COMPLETED,
                progress=final_progress.progress,
                verified_sha256=digest,
                verified_size_bytes=bytes_received,
                source_etag=response_etag,
                source_last_modified=response_last_modified,
                bytes_received=bytes_received,
                verified_at=_utc_now(),
                completed_at=_utc_now(),
                verification_status="verified",
                metadata={"verified_artifact": str(verified_path)},
            )
            self._emit_event(
                ComponentEventType.COMPONENT_DOWNLOAD_VERIFIED,
                "El artefacto de descarga fue verificado.",
                component_id=record.component_id,
                payload={"download_id": record.download_id, "sha256": digest, "size_bytes": bytes_received},
            )
            self._emit_event(
                ComponentEventType.COMPONENT_DOWNLOAD_COMPLETED,
                "La descarga de componente se completo y verifico.",
                component_id=record.component_id,
                payload={"download_id": record.download_id, "artifact_path": str(verified_path)},
            )
            return record
        finally:
            response.close()

    def _download_worker(self, download_id: str) -> None:
        acquired = False
        try:
            acquired = self._semaphore.acquire(timeout=0.1)
            while not acquired:
                record = self.get_download(download_id)
                if record is None:
                    return
                if record.status in DOWNLOAD_TERMINAL_STATES:
                    return
                time.sleep(0.05)
                acquired = self._semaphore.acquire(timeout=0.1)
            record = self.get_download(download_id)
            if record is None:
                return
            if record.status in DOWNLOAD_TERMINAL_STATES:
                return
            self._set_status(record, ComponentDownloadStatus.PREPARING)
            self._emit_event(
                ComponentEventType.COMPONENT_DOWNLOAD_STARTED,
                "La descarga de componente comenzo a prepararse.",
                component_id=record.component_id,
                payload={"download_id": record.download_id},
            )
            free_bytes = self.paths.free_space_bytes()
            partial_path = Path(record.partial_path)
            partial_bytes = self._partial_size(partial_path)
            if not DownloadDiskSpacePolicy(record.safety_margin_bytes).can_start(
                free_bytes=free_bytes,
                expected_download_bytes=record.expected_download_bytes,
                partial_bytes=partial_bytes,
            ):
                error = ComponentDownloadError(
                    category=ComponentDownloadErrorCategory.INSUFFICIENT_DISK_SPACE,
                    message_safe="No hay suficiente espacio para descargar este componente.",
                )
                self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
                return
            attempt = 0
            while attempt < max(1, record.retry_policy.max_attempts):
                attempt += 1
                record = self._set_status(record, ComponentDownloadStatus.PREPARING, attempts=attempt)
                try:
                    resume_offset = self._partial_size(partial_path)
                    record = self._perform_attempt(record, resume_offset=resume_offset)
                    return
                except OSError as exc:
                    error = _error_from_exception(exc)
                    if error.category == ComponentDownloadErrorCategory.DISK_FULL:
                        self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_FAILED,
                            "La descarga fallo por falta de espacio en disco.",
                            component_id=record.component_id,
                            severity="error",
                            payload={"download_id": download_id},
                        )
                        return
                    retryable = _retryable_error_category(error.category)
                    if not retryable or attempt >= record.retry_policy.max_attempts:
                        self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_FAILED,
                            "La descarga de componente fallo.",
                            component_id=record.component_id,
                            severity="error",
                            payload={"download_id": download_id, "error_category": error.category.value},
                        )
                        return
                    self._emit_event(
                        ComponentEventType.COMPONENT_DOWNLOAD_RETRY_SCHEDULED,
                        "Se programo un reintento de descarga.",
                        component_id=record.component_id,
                        payload={"download_id": download_id, "attempt": attempt + 1},
                    )
                    time.sleep(self._retry_delay(record.retry_policy, attempt))
                    record = self._set_status(
                        record,
                        ComponentDownloadStatus.INTERRUPTED,
                        interrupted_at=_utc_now(),
                        error=error,
                    )
                    continue
                except RuntimeError as exc:
                    error_text = str(exc)
                    if error_text == "range_invalid":
                        error = ComponentDownloadError(category=ComponentDownloadErrorCategory.RANGE_INVALID, message_safe="El servidor devolvio un rango invalido.", details=error_text)
                    elif error_text == "sha256_mismatch":
                        error = ComponentDownloadError(category=ComponentDownloadErrorCategory.SHA256_MISMATCH, message_safe="La verificacion SHA-256 no coincide.", details=error_text)
                    elif error_text == "truncated_response":
                        error = ComponentDownloadError(category=ComponentDownloadErrorCategory.TRUNCATED_RESPONSE, message_safe="La respuesta HTTP termino antes de tiempo.", details=error_text)
                    elif error_text == "content_length_mismatch":
                        error = ComponentDownloadError(category=ComponentDownloadErrorCategory.CONTENT_LENGTH_MISMATCH, message_safe="El tamano del archivo no coincide.", details=error_text)
                    elif error_text == "rate_limited":
                        error = ComponentDownloadError(category=ComponentDownloadErrorCategory.RATE_LIMITED, message_safe="El servidor limito la descarga.", details=error_text)
                    elif error_text.startswith("http_"):
                        code = int(error_text.split("_", 1)[1])
                        category = ComponentDownloadErrorCategory.HTTP_4XX if 400 <= code < 500 else ComponentDownloadErrorCategory.HTTP_5XX
                        if code == 429:
                            category = ComponentDownloadErrorCategory.RATE_LIMITED
                        error = ComponentDownloadError(category=category, message_safe=f"El servidor respondio con {code}.", details=error_text)
                    else:
                        error = ComponentDownloadError(category=ComponentDownloadErrorCategory.UNEXPECTED_ERROR, message_safe="La descarga fallo.", details=error_text)
                    if error.category == ComponentDownloadErrorCategory.SHA256_MISMATCH:
                        self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_HASH_MISMATCH,
                            "La descarga no coincidio con el SHA-256 esperado.",
                            component_id=record.component_id,
                            severity="error",
                            payload={"download_id": download_id},
                        )
                        return
                    retryable = _retryable_error_category(error.category)
                    if not retryable or attempt >= record.retry_policy.max_attempts:
                        self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
                        self._emit_event(
                            ComponentEventType.COMPONENT_DOWNLOAD_FAILED,
                            "La descarga de componente fallo.",
                            component_id=record.component_id,
                            severity="error",
                            payload={"download_id": download_id, "error_category": error.category.value},
                        )
                        return
                    self._emit_event(
                        ComponentEventType.COMPONENT_DOWNLOAD_RETRY_SCHEDULED,
                        "Se programo un reintento de descarga.",
                        component_id=record.component_id,
                        payload={"download_id": download_id, "attempt": attempt + 1},
                    )
                    time.sleep(self._retry_delay(record.retry_policy, attempt))
                    record = self._set_status(
                        record,
                        ComponentDownloadStatus.INTERRUPTED,
                        interrupted_at=_utc_now(),
                        error=error,
                    )
                    continue
                except Exception as exc:
                    error = _error_from_exception(exc)
                    self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
                    self._emit_event(
                        ComponentEventType.COMPONENT_DOWNLOAD_FAILED,
                        "La descarga de componente fallo.",
                        component_id=record.component_id,
                        severity="error",
                        payload={"download_id": download_id, "error_category": error.category.value},
                    )
                    return
            error = ComponentDownloadError(category=ComponentDownloadErrorCategory.UNEXPECTED_ERROR, message_safe="La descarga excedio el numero de reintentos.", details="max_attempts")
            self._finalize_terminal(record, status=ComponentDownloadStatus.FAILED, error=error, metadata={"error_category": error.category.value})
            self._emit_event(
                ComponentEventType.COMPONENT_DOWNLOAD_FAILED,
                "La descarga de componente fallo tras reintentos.",
                component_id=record.component_id,
                severity="error",
                payload={"download_id": download_id},
            )
        finally:
            if acquired:
                try:
                    self._semaphore.release()
                except ValueError:
                    pass
            self._release_worker(download_id)

    def recover_interrupted_downloads(self) -> tuple[ComponentDownloadRecord, ...]:
        recovered: list[ComponentDownloadRecord] = []
        for record in self.repository.list_records():
            if record.status in {ComponentDownloadStatus.DOWNLOADING, ComponentDownloadStatus.PREPARING, ComponentDownloadStatus.VERIFYING, ComponentDownloadStatus.PAUSE_REQUESTED, ComponentDownloadStatus.CANCEL_REQUESTED, ComponentDownloadStatus.RESUME_REQUESTED}:
                updated = replace(
                    record,
                    status=ComponentDownloadStatus.INTERRUPTED,
                    interrupted_at=_utc_now(),
                    recovered_at=_utc_now(),
                    updated_at=_utc_now(),
                )
                self.repository.save_record(updated)
                recovered.append(updated)
                self._emit_event(
                    ComponentEventType.COMPONENT_DOWNLOAD_RECOVERED_AFTER_RESTART,
                    "Se recupero una descarga interrumpida tras reiniciar la aplicacion.",
                    component_id=record.component_id,
                    payload={"download_id": record.download_id},
                )
        return tuple(recovered)

    def wait_for_terminal(self, download_id: str, timeout_seconds: float | None = None) -> ComponentDownloadRecord | None:
        deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
        while True:
            record = self.get_download(download_id)
            if record is None or record.status in DOWNLOAD_TERMINAL_STATES | {ComponentDownloadStatus.PAUSED, ComponentDownloadStatus.INTERRUPTED}:
                return record
            if deadline is not None and time.monotonic() > deadline:
                return record
            time.sleep(0.05)

    def verified_artifact(self, download_id: str) -> VerifiedComponentArtifact | None:
        record = self.get_download(download_id)
        if record is None or record.status != ComponentDownloadStatus.COMPLETED:
            return None
        if not record.verified_sha256 or record.verified_size_bytes is None:
            return None
        return VerifiedComponentArtifact(
            download_id=record.download_id,
            component_id=record.component_id,
            verified_artifact_path=record.verified_artifact_path,
            partial_path=record.partial_path,
            sha256=record.verified_sha256,
            size_bytes=record.verified_size_bytes,
            created_at=record.created_at or _utc_now(),
            verified_at=record.verified_at or _utc_now(),
            etag=record.source_etag,
            last_modified=record.source_last_modified,
            source_url=record.source_url,
        )
