"""Contratos de descargas de componentes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from creator_intelligence_studio.shared.dates import from_iso_z, to_iso_z


class ComponentDownloadStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED = "paused"
    RESUME_REQUESTED = "resume_requested"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class ComponentDownloadErrorCategory(str, Enum):
    INVALID_REQUEST = "invalid_request"
    SOURCE_NOT_APPROVED = "source_not_approved"
    INVALID_URL = "invalid_url"
    INSECURE_SCHEME = "insecure_scheme"
    BLOCKED_DESTINATION = "blocked_destination"
    CONNECTION_FAILED = "connection_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    READ_TIMEOUT = "read_timeout"
    STALLED_TRANSFER = "stalled_transfer"
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    RATE_LIMITED = "rate_limited"
    RANGE_NOT_SUPPORTED = "range_not_supported"
    RANGE_INVALID = "range_invalid"
    REMOTE_ARTIFACT_CHANGED = "remote_artifact_changed"
    CONTENT_LENGTH_MISMATCH = "content_length_mismatch"
    TRUNCATED_RESPONSE = "truncated_response"
    INSUFFICIENT_DISK_SPACE = "insufficient_disk_space"
    DISK_FULL = "disk_full"
    WRITE_FAILED = "write_failed"
    SHA256_MISMATCH = "sha256_mismatch"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    PERSISTENCE_FAILED = "persistence_failed"
    UNSUPPORTED_ARTIFACT = "unsupported_artifact"
    UNEXPECTED_ERROR = "unexpected_error"


class ComponentDownloadOverwritePolicy(str, Enum):
    REJECT = "reject"
    REUSE = "reuse"
    REPLACE = "replace"


class ComponentDownloadPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ComponentDownloadRetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    jitter_seconds: float = 0.25

    def to_dict(self) -> dict[str, object]:
        return {
            "max_attempts": self.max_attempts,
            "backoff_seconds": self.backoff_seconds,
            "max_backoff_seconds": self.max_backoff_seconds,
            "jitter_seconds": self.jitter_seconds,
        }


@dataclass(frozen=True, slots=True)
class ComponentDownloadRequest:
    component_id: str
    catalog_version: int
    source_url: str
    expected_sha256: str | None
    expected_download_bytes: int | None
    destination_logical_location: str
    priority: ComponentDownloadPriority = ComponentDownloadPriority.NORMAL
    user_initiated: bool = True
    retry_policy: ComponentDownloadRetryPolicy = field(default_factory=ComponentDownloadRetryPolicy)
    overwrite_policy: ComponentDownloadOverwritePolicy = ComponentDownloadOverwritePolicy.REJECT
    allowed_domains: tuple[str, ...] = ()
    allow_localhost: bool = False
    test_mode: bool = False
    max_redirects: int = 3
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 10.0
    stalled_timeout_seconds: float = 30.0
    chunk_size_bytes: int = 1024 * 256
    safety_margin_bytes: int = 8 * 1024 * 1024

    def canonical_url(self) -> str:
        parts = urlsplit(self.source_url)
        sanitized = parts._replace(query="", fragment="")
        return urlunsplit(sanitized)

    def identity_key(self) -> str:
        payload = {
            "component_id": self.component_id.strip().lower(),
            "catalog_version": self.catalog_version,
            "source_url": self.canonical_url(),
            "expected_sha256": self.expected_sha256,
            "expected_download_bytes": self.expected_download_bytes,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ComponentDownloadProgress:
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    percentage: float | None = None
    speed_bytes_per_second: float | None = None
    smoothed_speed_bytes_per_second: float | None = None
    eta_seconds: float | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "percentage": self.percentage,
            "speed_bytes_per_second": self.speed_bytes_per_second,
            "smoothed_speed_bytes_per_second": self.smoothed_speed_bytes_per_second,
            "eta_seconds": self.eta_seconds,
            "started_at": to_iso_z(self.started_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ComponentDownloadArtifact:
    download_id: str
    component_id: str
    verified_artifact_path: str
    partial_path: str | None
    sha256: str
    size_bytes: int
    created_at: datetime
    verified_at: datetime
    etag: str | None = None
    last_modified: str | None = None
    source_url: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "download_id": self.download_id,
            "component_id": self.component_id,
            "verified_artifact_path": self.verified_artifact_path,
            "partial_path": self.partial_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "created_at": to_iso_z(self.created_at),
            "verified_at": to_iso_z(self.verified_at),
            "etag": self.etag,
            "last_modified": self.last_modified,
            "source_url": self.source_url,
        }


VerifiedComponentArtifact = ComponentDownloadArtifact


@dataclass(frozen=True, slots=True)
class ComponentDownloadError:
    category: ComponentDownloadErrorCategory
    message_safe: str
    details: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category.value,
            "message_safe": self.message_safe,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class ComponentDownloadRecord:
    download_id: str
    identity_key: str
    component_id: str
    catalog_version: int
    source_url: str
    expected_sha256: str | None
    expected_download_bytes: int | None
    destination_logical_location: str
    priority: ComponentDownloadPriority
    user_initiated: bool
    retry_policy: ComponentDownloadRetryPolicy
    overwrite_policy: ComponentDownloadOverwritePolicy
    allowed_domains: tuple[str, ...]
    allow_localhost: bool
    test_mode: bool
    max_redirects: int
    connect_timeout_seconds: float
    read_timeout_seconds: float
    stalled_timeout_seconds: float
    chunk_size_bytes: int
    safety_margin_bytes: int
    status: ComponentDownloadStatus
    progress: ComponentDownloadProgress
    partial_path: str
    verified_artifact_path: str
    source_etag: str | None = None
    source_last_modified: str | None = None
    bytes_received: int = 0
    attempts: int = 0
    max_attempts: int = 3
    verification_status: str = "pending_verification"
    verified_sha256: str | None = None
    verified_size_bytes: int | None = None
    error: ComponentDownloadError | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    interrupted_at: datetime | None = None
    resume_requested_at: datetime | None = None
    pause_requested_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    verified_at: datetime | None = None
    recovered_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "download_id": self.download_id,
            "identity_key": self.identity_key,
            "component_id": self.component_id,
            "catalog_version": self.catalog_version,
            "source_url": self.source_url,
            "expected_sha256": self.expected_sha256,
            "expected_download_bytes": self.expected_download_bytes,
            "destination_logical_location": self.destination_logical_location,
            "priority": self.priority.value,
            "user_initiated": self.user_initiated,
            "retry_policy": self.retry_policy.to_dict(),
            "overwrite_policy": self.overwrite_policy.value,
            "allowed_domains": list(self.allowed_domains),
            "allow_localhost": self.allow_localhost,
            "test_mode": self.test_mode,
            "max_redirects": self.max_redirects,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
            "stalled_timeout_seconds": self.stalled_timeout_seconds,
            "chunk_size_bytes": self.chunk_size_bytes,
            "safety_margin_bytes": self.safety_margin_bytes,
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "partial_path": self.partial_path,
            "verified_artifact_path": self.verified_artifact_path,
            "source_etag": self.source_etag,
            "source_last_modified": self.source_last_modified,
            "bytes_received": self.bytes_received,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "verification_status": self.verification_status,
            "verified_sha256": self.verified_sha256,
            "verified_size_bytes": self.verified_size_bytes,
            "error": self.error.to_dict() if self.error else None,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
            "completed_at": to_iso_z(self.completed_at),
            "cancelled_at": to_iso_z(self.cancelled_at),
            "interrupted_at": to_iso_z(self.interrupted_at),
            "resume_requested_at": to_iso_z(self.resume_requested_at),
            "pause_requested_at": to_iso_z(self.pause_requested_at),
            "cancel_requested_at": to_iso_z(self.cancel_requested_at),
            "verified_at": to_iso_z(self.verified_at),
            "recovered_at": to_iso_z(self.recovered_at),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ComponentDownloadRecord":
        def _enum_from_payload(enum_cls, value, default):
            try:
                return enum_cls(str(value or default))
            except ValueError:
                return enum_cls(default)

        def _datetime_from_payload(value):
            if value in {None, ""}:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                return from_iso_z(value)
            return None

        retry_payload = payload.get("retry_policy") or {}
        progress_payload = payload.get("progress") or {}
        error_payload = payload.get("error")
        return cls(
            download_id=str(payload.get("download_id") or ""),
            identity_key=str(payload.get("identity_key") or ""),
            component_id=str(payload.get("component_id") or ""),
            catalog_version=int(payload.get("catalog_version") or 0),
            source_url=str(payload.get("source_url") or ""),
            expected_sha256=payload.get("expected_sha256"),
            expected_download_bytes=payload.get("expected_download_bytes"),
            destination_logical_location=str(payload.get("destination_logical_location") or ""),
            priority=_enum_from_payload(ComponentDownloadPriority, payload.get("priority"), "normal"),
            user_initiated=bool(payload.get("user_initiated", True)),
            retry_policy=ComponentDownloadRetryPolicy(
                max_attempts=int(retry_payload.get("max_attempts", 3)),
                backoff_seconds=float(retry_payload.get("backoff_seconds", 1.0)),
                max_backoff_seconds=float(retry_payload.get("max_backoff_seconds", 30.0)),
                jitter_seconds=float(retry_payload.get("jitter_seconds", 0.25)),
            ),
            overwrite_policy=_enum_from_payload(ComponentDownloadOverwritePolicy, payload.get("overwrite_policy"), "reject"),
            allowed_domains=tuple(payload.get("allowed_domains") or ()),
            allow_localhost=bool(payload.get("allow_localhost", False)),
            test_mode=bool(payload.get("test_mode", False)),
            max_redirects=int(payload.get("max_redirects", 3)),
            connect_timeout_seconds=float(payload.get("connect_timeout_seconds", 10.0)),
            read_timeout_seconds=float(payload.get("read_timeout_seconds", 10.0)),
            stalled_timeout_seconds=float(payload.get("stalled_timeout_seconds", 30.0)),
            chunk_size_bytes=int(payload.get("chunk_size_bytes", 1024 * 256)),
            safety_margin_bytes=int(payload.get("safety_margin_bytes", 8 * 1024 * 1024)),
            status=_enum_from_payload(ComponentDownloadStatus, payload.get("status"), "queued"),
            progress=ComponentDownloadProgress(
                downloaded_bytes=int(progress_payload.get("downloaded_bytes") or 0),
                total_bytes=progress_payload.get("total_bytes"),
                percentage=progress_payload.get("percentage"),
                speed_bytes_per_second=progress_payload.get("speed_bytes_per_second"),
                smoothed_speed_bytes_per_second=progress_payload.get("smoothed_speed_bytes_per_second"),
                eta_seconds=progress_payload.get("eta_seconds"),
                started_at=_datetime_from_payload(progress_payload.get("started_at")),
                updated_at=_datetime_from_payload(progress_payload.get("updated_at")),
            ),
            partial_path=str(payload.get("partial_path") or ""),
            verified_artifact_path=str(payload.get("verified_artifact_path") or ""),
            source_etag=payload.get("source_etag"),
            source_last_modified=payload.get("source_last_modified"),
            bytes_received=int(payload.get("bytes_received") or 0),
            attempts=int(payload.get("attempts") or 0),
            max_attempts=int(payload.get("max_attempts") or 3),
            verification_status=str(payload.get("verification_status") or "pending_verification"),
            verified_sha256=payload.get("verified_sha256"),
            verified_size_bytes=payload.get("verified_size_bytes"),
            error=(
                ComponentDownloadError(
                    category=_enum_from_payload(
                        ComponentDownloadErrorCategory,
                        error_payload.get("category"),
                        "unexpected_error",
                    ),
                    message_safe=str(error_payload.get("message_safe") or ""),
                    details=error_payload.get("details"),
                )
                if isinstance(error_payload, dict)
                else None
            ),
            created_at=_datetime_from_payload(payload.get("created_at")),
            updated_at=_datetime_from_payload(payload.get("updated_at")),
            completed_at=_datetime_from_payload(payload.get("completed_at")),
            cancelled_at=_datetime_from_payload(payload.get("cancelled_at")),
            interrupted_at=_datetime_from_payload(payload.get("interrupted_at")),
            resume_requested_at=_datetime_from_payload(payload.get("resume_requested_at")),
            pause_requested_at=_datetime_from_payload(payload.get("pause_requested_at")),
            cancel_requested_at=_datetime_from_payload(payload.get("cancel_requested_at")),
            verified_at=_datetime_from_payload(payload.get("verified_at")),
            recovered_at=_datetime_from_payload(payload.get("recovered_at")),
            metadata=dict(payload.get("metadata") or {}),
        )


def sanitize_download_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(query="", fragment=""))


ALLOWED_DOWNLOAD_STATUS_TRANSITIONS: dict[ComponentDownloadStatus, set[ComponentDownloadStatus]] = {
    ComponentDownloadStatus.QUEUED: {ComponentDownloadStatus.PREPARING, ComponentDownloadStatus.CANCEL_REQUESTED, ComponentDownloadStatus.FAILED},
    ComponentDownloadStatus.PREPARING: {ComponentDownloadStatus.DOWNLOADING, ComponentDownloadStatus.CANCEL_REQUESTED, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED},
    ComponentDownloadStatus.DOWNLOADING: {ComponentDownloadStatus.PAUSE_REQUESTED, ComponentDownloadStatus.CANCEL_REQUESTED, ComponentDownloadStatus.VERIFYING, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED, ComponentDownloadStatus.COMPLETED},
    ComponentDownloadStatus.PAUSE_REQUESTED: {ComponentDownloadStatus.PAUSED, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED},
    ComponentDownloadStatus.PAUSED: {ComponentDownloadStatus.RESUME_REQUESTED, ComponentDownloadStatus.CANCEL_REQUESTED, ComponentDownloadStatus.INTERRUPTED},
    ComponentDownloadStatus.RESUME_REQUESTED: {ComponentDownloadStatus.DOWNLOADING, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED},
    ComponentDownloadStatus.VERIFYING: {ComponentDownloadStatus.COMPLETED, ComponentDownloadStatus.CANCEL_REQUESTED, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED},
    ComponentDownloadStatus.COMPLETED: set(),
    ComponentDownloadStatus.CANCEL_REQUESTED: {ComponentDownloadStatus.CANCELLED, ComponentDownloadStatus.INTERRUPTED, ComponentDownloadStatus.FAILED},
    ComponentDownloadStatus.CANCELLED: set(),
    ComponentDownloadStatus.INTERRUPTED: {ComponentDownloadStatus.RESUME_REQUESTED, ComponentDownloadStatus.PREPARING, ComponentDownloadStatus.FAILED, ComponentDownloadStatus.CANCEL_REQUESTED},
    ComponentDownloadStatus.FAILED: set(),
}


def validate_download_transition(current: ComponentDownloadStatus, next_state: ComponentDownloadStatus) -> None:
    if current == next_state:
        return
    allowed = ALLOWED_DOWNLOAD_STATUS_TRANSITIONS.get(current, set())
    if next_state not in allowed:
        raise ValueError(f"Transicion de descarga invalida: {current.value} -> {next_state.value}")
