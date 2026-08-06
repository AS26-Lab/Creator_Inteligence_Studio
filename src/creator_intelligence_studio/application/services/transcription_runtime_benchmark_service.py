"""Benchmark funcional local para motor y hardware de transcripcion."""

from __future__ import annotations

import gc
import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalogEntry,
    ComponentEvent,
    ComponentEventType,
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.hardware.entities import HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.transcription.benchmark import (
    TranscriptionRuntimeBenchmarkErrorCode,
    TranscriptionRuntimeBenchmarkPresentation,
    TranscriptionRuntimeBenchmarkReadiness,
    TranscriptionRuntimeBenchmarkRequest,
    TranscriptionRuntimeBenchmarkResult,
    TranscriptionRuntimeBenchmarkStatus,
)
from creator_intelligence_studio.domain.components.catalog import build_default_transcription_profiles
from creator_intelligence_studio.domain.transcription.profiles import TranscriptionProfileDefinition
from creator_intelligence_studio.domain.transcription.services import normalize_device, normalize_model_name, normalize_profile, normalize_requested_compute_type
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionBackendInfo, TranscriptionCancellationToken, TranscriptionModelStatus
from creator_intelligence_studio.infrastructure.operational_evaluation.demo_asset_factory import create_demo_audio
from creator_intelligence_studio.infrastructure.transcription.faster_whisper_engine import FasterWhisperEngine
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


BENCHMARK_VERSION = 1
BENCHMARK_CHECK_KIND = "transcription_runtime_benchmark"
DEFAULT_BENCHMARK_TEXT = "Diagnostico local de transcripcion."


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _system_ram_available_bytes() -> int | None:
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullAvailPhys)
        except Exception:
            return None
    elif hasattr(os, "sysconf"):
        try:
            pagesize = os.sysconf("SC_PAGE_SIZE")
            avphys_pages = os.sysconf("SC_AVPHYS_PAGES")
            if isinstance(pagesize, int) and isinstance(avphys_pages, int):
                return pagesize * avphys_pages
        except (ValueError, OSError, AttributeError):
            return None
    return None


def _query_nvidia_vram_free_bytes(timeout_seconds: float = 3.0) -> int | None:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [
                executable,
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    line = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    if not line:
        return None
    try:
        return int(float(line) * 1024 * 1024)
    except ValueError:
        return None


def _duration_ms(start: float, end: float) -> int:
    return max(0, int(round((end - start) * 1000.0)))


def _audio_duration_ms(audio_path: Path) -> int | None:
    try:
        with wave.open(str(audio_path), "rb") as handle:
            frames = handle.getnframes()
            sample_rate = handle.getframerate()
            if sample_rate <= 0:
                return None
            return int(round(frames / sample_rate * 1000.0))
    except Exception:
        return None


def _normalize_error_category(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _requested_device_to_runtime_device(value: str | None) -> str:
    normalized = (value or "auto").strip().lower()
    if normalized == "gpu":
        return "cuda"
    return normalized


@dataclass(frozen=True, slots=True)
class _BenchmarkSelection:
    profile: TranscriptionProfileDefinition | None
    model_entry: ComponentCatalogEntry | None
    model_name: str | None
    model_status: ComponentInstallationStatus
    notes: tuple[str, ...] = ()
    warning: str | None = None


class TranscriptionRuntimeBenchmarkService:
    """Ejecuta y persiste un benchmark funcional pequeno y explicito."""

    def __init__(
        self,
        *,
        paths: ProjectPaths,
        repository: ComponentManagerRepository,
        model_manager: TranscriptionModelManager,
        resolver,
        hardware_service,
        engine_factory=None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.paths = paths
        self.repository = repository
        self.model_manager = model_manager
        self.resolver = resolver
        self.hardware_service = hardware_service
        self.engine_factory = engine_factory or (lambda manager, log: FasterWhisperEngine(model_manager=manager, logger=log))
        self.logger = logger or logging.getLogger("creator_intelligence_studio.components.benchmark")
        self._lock = False

    def _profiles(self) -> dict[str, TranscriptionProfileDefinition]:
        profiles = self.repository.list_transcription_profiles()
        if not profiles:
            profiles = build_default_transcription_profiles()
        return {profile.profile_id: profile for profile in profiles}

    def _catalog_entry_from_model(self, model_name: str) -> ComponentCatalogEntry | None:
        catalog = self.repository.get_catalog()
        return catalog.get_entry(f"transcription-model.{model_name}")

    def _installed_model_candidates(self) -> list[_BenchmarkSelection]:
        candidates: list[_BenchmarkSelection] = []
        for model_name in ("base", "small", "medium"):
            info = self.model_manager.inspect_model_availability(model_name)
            entry = self._catalog_entry_from_model(model_name)
            status = ComponentInstallationStatus.READY if info.installed else (
                ComponentInstallationStatus.INVALID if info.status in {TranscriptionModelStatus.CORRUPT, TranscriptionModelStatus.INCOMPLETE, TranscriptionModelStatus.ERROR} else (
                    ComponentInstallationStatus.INCOMPATIBLE if info.status == TranscriptionModelStatus.INCOMPATIBLE else ComponentInstallationStatus.MISSING
                )
            )
            if info.installed and entry is not None:
                profile = self._profiles().get(info.profile)
                candidates.append(
                    _BenchmarkSelection(
                        profile=profile,
                        model_entry=entry,
                        model_name=info.model_name,
                        model_status=status,
                    )
                )
        return candidates

    def _select_profile_and_model(self, request: TranscriptionRuntimeBenchmarkRequest) -> _BenchmarkSelection:
        profile_key = normalize_profile(request.requested_profile)
        profiles = self._profiles()
        requested_profile = profiles.get(profile_key) or profiles.get("balanced") or next(iter(profiles.values()), None)
        explicit_model_entry = self._catalog_entry_from_model(request.model_component_id.split(".", 1)[-1]) if request.model_component_id else None
        explicit_model_name = explicit_model_entry.version if explicit_model_entry else None
        if explicit_model_name:
            explicit_info = self.model_manager.inspect_model_availability(explicit_model_name)
            status = ComponentInstallationStatus.READY if explicit_info.installed else (
                ComponentInstallationStatus.INVALID if explicit_info.status in {TranscriptionModelStatus.CORRUPT, TranscriptionModelStatus.INCOMPLETE, TranscriptionModelStatus.ERROR} else (
                    ComponentInstallationStatus.INCOMPATIBLE if explicit_info.status == TranscriptionModelStatus.INCOMPATIBLE else ComponentInstallationStatus.MISSING
                )
            )
            return _BenchmarkSelection(
                profile=requested_profile,
                model_entry=explicit_model_entry,
                model_name=explicit_model_name,
                model_status=status,
                warning=None if explicit_info.installed else "benchmark_unavailable_missing_model",
            )
        preferred_model_name = requested_profile.model_component_id.split(".", 1)[-1] if requested_profile and requested_profile.model_component_id else "small"
        preferred_info = self.model_manager.inspect_model_availability(preferred_model_name)
        preferred_entry = self._catalog_entry_from_model(preferred_model_name)
        if preferred_info.installed and preferred_entry is not None:
            return _BenchmarkSelection(
                profile=requested_profile,
                model_entry=preferred_entry,
                model_name=preferred_model_name,
                model_status=ComponentInstallationStatus.READY,
            )
        fallback = self._installed_model_candidates()
        if fallback:
            chosen = fallback[0]
            return _BenchmarkSelection(
                profile=requested_profile,
                model_entry=chosen.model_entry,
                model_name=chosen.model_name,
                model_status=chosen.model_status,
                notes=(f"Se uso el modelo local {chosen.model_name} porque el perfil solicitado no estaba disponible.",),
            )
        return _BenchmarkSelection(
            profile=requested_profile,
            model_entry=preferred_entry,
            model_name=preferred_model_name,
            model_status=ComponentInstallationStatus.MISSING,
            warning="benchmark_unavailable_missing_model",
        )

    def _resolve_compute_type(self, *, profile: TranscriptionProfileDefinition | None, device: str, backend: TranscriptionBackendInfo) -> str | None:
        normalized_device = normalize_device(device)
        if normalized_device == "cpu":
            requested = normalize_requested_compute_type(profile.cpu_compute_type if profile else None)
            if requested is not None:
                return requested
            if "int8" in backend.supported_compute_types:
                return "int8"
            if backend.supported_compute_types:
                return backend.supported_compute_types[0]
            return None
        requested = normalize_requested_compute_type(profile.gpu_compute_type if profile else None)
        supported = tuple(str(item) for item in backend.supported_compute_types)
        if requested and requested in supported:
            return requested
        for candidate in ("int8_float16", "float16", "int8"):
            if candidate in supported:
                return candidate
        return None

    def _prepare_fixture(self, fixture_id: str) -> tuple[Path, int | None, tuple[str, ...]]:
        fixture_root = self.paths.project_root / "cache" / "transcription_benchmarks" / fixture_id
        fixture_path = fixture_root / "benchmark_fixture.wav"
        if fixture_path.exists():
            return fixture_path, _audio_duration_ms(fixture_path), ("Fixture reutilizada de caché local.",)
        try:
            _, notes = create_demo_audio(fixture_path, text=DEFAULT_BENCHMARK_TEXT, duration_seconds=2.0)
            return fixture_path, _audio_duration_ms(fixture_path), notes
        except Exception as exc:
            raise RuntimeError(f"No se pudo crear la fixture segura: {exc}") from exc

    def _persist_runtime_check(
        self,
        *,
        selection: _BenchmarkSelection,
        result: TranscriptionRuntimeBenchmarkResult,
        runtime_backend: TranscriptionBackendInfo,
        persist_result: bool,
    ) -> None:
        if not persist_result:
            return
        component_id = selection.model_entry.component_id if selection.model_entry is not None else result.model_component_id
        if component_id and self.repository.get_installation(component_id) is None:
            self.repository.upsert_installation(
                ComponentInstallation(
                    component_id=component_id,
                    installation_status=ComponentInstallationStatus.MISSING,
                    installed_version=None,
                    revision=None,
                    install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
                    location_path=None,
                    location_reference=None,
                    detected_at=None,
                    verified_at=None,
                    health_status=RuntimeCheckStatus.NOT_CHECKED,
                    source="benchmark_persistence",
                    managed=False,
                    metadata={"created_by": "benchmark_persistence"},
                )
            )
        record = RuntimeCheckRecord(
            component_id=component_id or "transcription-runtime.ctranslate2",
            status=result.runtime_status,
            runtime_importable=result.runtime_status != RuntimeCheckStatus.FAILED,
            runtime_version=getattr(runtime_backend, "ctranslate2_version", None)
            or getattr(runtime_backend, "runtime_version", None)
            or getattr(runtime_backend, "version", None),
            device_count=int(getattr(runtime_backend, "device_count", 0) or 0),
            supported_compute_types=getattr(runtime_backend, "supported_compute_types", ()),
            notes="Benchmark funcional local.",
            warning_message="; ".join(result.warnings) if result.warnings else None,
            error_code=result.safe_error_category,
            error_message=result.safe_error_message,
            metadata={
                "check_kind": BENCHMARK_CHECK_KIND,
                "benchmark_id": result.benchmark_id,
                "benchmark_version": result.benchmark_version,
                "requested_profile": result.requested_profile,
                "requested_device": result.requested_device,
                "actual_device": result.actual_device,
                "model_component_id": result.model_component_id,
                "selected_compute_type": result.selected_compute_type,
                "model_status": result.model_status.value,
                "runtime_status": result.runtime_status.value,
                "status": result.status.value,
                "readiness": result.readiness.value,
                "inference_status": result.inference_status,
                "transcript_present": result.transcript_present,
                "segment_count": result.segment_count,
                "detected_language": result.detected_language,
                "load_duration_ms": result.load_duration_ms,
                "inference_duration_ms": result.inference_duration_ms,
                "total_duration_ms": result.total_duration_ms,
                "audio_duration_ms": result.audio_duration_ms,
                "real_time_factor": result.real_time_factor,
                "fixture_id": result.fixture_id,
                "evidence": list(result.evidence),
                "compute_policy": result.compute_policy,
            },
            checked_at=result.completed_at or result.started_at,
            created_at=result.completed_at or result.started_at,
            updated_at=result.completed_at or result.started_at,
        )
        self.repository.upsert_runtime_check(record)

    def _append_event(
        self,
        *,
        event_type: ComponentEventType,
        message_safe: str,
        selection: _BenchmarkSelection | None,
        benchmark_id: str,
        payload: dict[str, object],
    ) -> None:
        self.repository.append_event(
            ComponentEvent(
                event_type=event_type,
                message_safe=message_safe,
                component_id=selection.model_entry.component_id if selection and selection.model_entry else None,
                hardware_profile_id=None,
                profile_id=selection.profile.profile_id if selection and selection.profile else None,
                severity="info",
                technical_reference=benchmark_id,
                payload=payload,
                created_at=utc_now(),
            )
        )

    def _deadline_exceeded(self, started_monotonic: float, timeout_seconds: float) -> bool:
        return timeout_seconds > 0 and (time.monotonic() - started_monotonic) >= timeout_seconds

    def run_benchmark(
        self,
        *,
        requested_profile: str = "balanced",
        requested_device: str = "auto",
        model_component_id: str | None = None,
        timeout_seconds: float = 30.0,
        cancellation_token: TranscriptionCancellationToken | None = None,
        fixture_id: str = "synthetic_voice_v1",
        persist_result: bool = True,
        force_refresh: bool = False,
    ) -> TranscriptionRuntimeBenchmarkResult:
        request = TranscriptionRuntimeBenchmarkRequest(
            requested_profile=requested_profile,
            requested_device=requested_device,
            model_component_id=model_component_id,
            timeout_seconds=timeout_seconds,
            fixture_id=fixture_id,
            persist_result=persist_result,
            force_refresh=force_refresh,
        )
        benchmark_id = str(uuid4())
        started_at = _utc_now()
        started_monotonic = time.monotonic()
        status = TranscriptionRuntimeBenchmarkStatus.PENDING
        readiness = TranscriptionRuntimeBenchmarkReadiness.UNKNOWN
        warnings: list[str] = []
        evidence: list[str] = [f"benchmark_id={benchmark_id}", f"request_profile={request.requested_profile}"]
        requested_device = (request.requested_device or "auto").strip().lower() or "auto"
        selected_device = _requested_device_to_runtime_device(requested_device)
        if selected_device not in {"auto", "cpu", "cuda"}:
            selected_device = "cuda" if selected_device == "cuda" else "auto"
        runtime_backend = self.hardware_service.collect_runtime_check(persist=persist_result)
        hardware_profile = self.hardware_service.collect_inventory(persist=persist_result)
        selection = self._select_profile_and_model(request)
        if selection.warning:
            warnings.append(selection.warning)
        warnings.extend(selection.notes)
        compute_type: str | None = self._resolve_compute_type(
            profile=selection.profile,
            device=selected_device,
            backend=runtime_backend,
        )
        if selection.model_entry is None or selection.model_status != ComponentInstallationStatus.READY:
            result = TranscriptionRuntimeBenchmarkResult(
                benchmark_id=benchmark_id,
                status=TranscriptionRuntimeBenchmarkStatus.FAILED,
                requested_device=requested_device,
                actual_device=None,
                runtime_status=RuntimeCheckStatus.FAILED if selection.warning == "benchmark_unavailable_missing_model" else RuntimeCheckStatus.DEGRADED,
                model_status=selection.model_status,
                inference_status=selection.warning or "model_missing",
                selected_model=selection.model_entry,
                selected_compute_type=None,
                started_at=started_at,
                completed_at=utc_now(),
                load_duration_ms=None,
                inference_duration_ms=None,
                total_duration_ms=_duration_ms(started_monotonic, time.monotonic()),
                audio_duration_ms=None,
                real_time_factor=None,
                approximate_ram_before=hardware_profile.ram_available_bytes,
                approximate_ram_peak=hardware_profile.ram_available_bytes,
                approximate_ram_after=hardware_profile.ram_available_bytes,
                approximate_vram_before=None,
                approximate_vram_peak=None,
                approximate_vram_after=None,
                transcript_present=False,
                segment_count=0,
                detected_language=None,
                warnings=tuple(warnings),
                safe_error_category=TranscriptionRuntimeBenchmarkErrorCode.MODEL_MISSING.value,
                safe_error_message="Se necesita instalar un modelo local para comprobar el rendimiento.",
                readiness=TranscriptionRuntimeBenchmarkReadiness.UNAVAILABLE,
                evidence=tuple(evidence + [f"runtime_status={runtime_backend.status.value}", "benchmark_unavailable_missing_model"]),
                benchmark_version=BENCHMARK_VERSION,
                fixture_id=request.fixture_id,
                requested_profile=selection.profile.profile_id if selection.profile else request.requested_profile,
                model_component_id=selection.model_entry.component_id if selection.model_entry else request.model_component_id,
                compute_policy=None,
            )
            self._persist_runtime_check(selection=selection, result=result, runtime_backend=runtime_backend, persist_result=persist_result)
            self._append_event(
                event_type=ComponentEventType.COMPONENT_MISSING,
                message_safe="No se pudo ejecutar el benchmark porque falta un modelo local.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={"benchmark_id": benchmark_id, "fixture_id": request.fixture_id, "reason": result.safe_error_category},
            )
            return result

        engine = self.engine_factory(self.model_manager, self.logger)
        backend = engine.verify_backend()
        evidence.append(f"backend={backend.backend}")
        if selected_device == "cuda" and backend.available is False:
            result = TranscriptionRuntimeBenchmarkResult(
                benchmark_id=benchmark_id,
                status=TranscriptionRuntimeBenchmarkStatus.FAILED,
                requested_device=requested_device,
                actual_device="cuda",
                runtime_status=RuntimeCheckStatus.FAILED,
                model_status=selection.model_status,
                inference_status="gpu_runtime_missing",
                selected_model=selection.model_entry,
                selected_compute_type=None,
                started_at=started_at,
                completed_at=utc_now(),
                load_duration_ms=None,
                inference_duration_ms=None,
                total_duration_ms=_duration_ms(started_monotonic, time.monotonic()),
                audio_duration_ms=None,
                real_time_factor=None,
                approximate_ram_before=hardware_profile.ram_available_bytes,
                approximate_ram_peak=hardware_profile.ram_available_bytes,
                approximate_ram_after=hardware_profile.ram_available_bytes,
                approximate_vram_before=_query_nvidia_vram_free_bytes(),
                approximate_vram_peak=None,
                approximate_vram_after=_query_nvidia_vram_free_bytes(),
                transcript_present=False,
                segment_count=0,
                detected_language=None,
                warnings=tuple(warnings + [backend.fallback_reason or "CUDA no disponible."]),
                safe_error_category=TranscriptionRuntimeBenchmarkErrorCode.GPU_RUNTIME_MISSING.value,
                safe_error_message=backend.fallback_reason or "CUDA no disponible.",
                readiness=TranscriptionRuntimeBenchmarkReadiness.INCOMPATIBLE,
                evidence=tuple(evidence),
                benchmark_version=BENCHMARK_VERSION,
                fixture_id=request.fixture_id,
                requested_profile=selection.profile.profile_id if selection.profile else request.requested_profile,
                model_component_id=selection.model_entry.component_id,
                compute_policy=None,
            )
            self._persist_runtime_check(selection=selection, result=result, runtime_backend=backend, persist_result=persist_result)
            self._append_event(
                event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_COMPLETED,
                message_safe="El benchmark de GPU no pudo completarse por falta de runtime CUDA.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={"benchmark_id": benchmark_id, "fixture_id": request.fixture_id, "reason": result.safe_error_category},
            )
            return result

        compute_type = self._resolve_compute_type(profile=selection.profile, device=selected_device, backend=backend)
        if compute_type is None:
            result = TranscriptionRuntimeBenchmarkResult(
                benchmark_id=benchmark_id,
                status=TranscriptionRuntimeBenchmarkStatus.FAILED,
                requested_device=requested_device,
                actual_device=selected_device,
                runtime_status=RuntimeCheckStatus.INCOMPATIBLE,
                model_status=selection.model_status,
                inference_status="unsupported_compute_type",
                selected_model=selection.model_entry,
                selected_compute_type=None,
                started_at=started_at,
                completed_at=utc_now(),
                load_duration_ms=None,
                inference_duration_ms=None,
                total_duration_ms=_duration_ms(started_monotonic, time.monotonic()),
                audio_duration_ms=None,
                real_time_factor=None,
                approximate_ram_before=hardware_profile.ram_available_bytes,
                approximate_ram_peak=hardware_profile.ram_available_bytes,
                approximate_ram_after=hardware_profile.ram_available_bytes,
                approximate_vram_before=_query_nvidia_vram_free_bytes() if selected_device == "cuda" else None,
                approximate_vram_peak=None,
                approximate_vram_after=_query_nvidia_vram_free_bytes() if selected_device == "cuda" else None,
                transcript_present=False,
                segment_count=0,
                detected_language=None,
                warnings=tuple(warnings),
                safe_error_category=TranscriptionRuntimeBenchmarkErrorCode.UNSUPPORTED_COMPUTE_TYPE.value,
                safe_error_message="El compute type solicitado no es compatible con este entorno.",
                readiness=TranscriptionRuntimeBenchmarkReadiness.INCOMPATIBLE,
                evidence=tuple(evidence),
                benchmark_version=BENCHMARK_VERSION,
                fixture_id=request.fixture_id,
                requested_profile=selection.profile.profile_id if selection.profile else request.requested_profile,
                model_component_id=selection.model_entry.component_id,
                compute_policy=None,
            )
            self._persist_runtime_check(selection=selection, result=result, runtime_backend=backend, persist_result=persist_result)
            self._append_event(
                event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_COMPLETED,
                message_safe="El benchmark no pudo completarse por incompatibilidad de compute type.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={"benchmark_id": benchmark_id, "fixture_id": request.fixture_id, "reason": result.safe_error_category},
            )
            return result

        if self._deadline_exceeded(started_monotonic, timeout_seconds):
            result = TranscriptionRuntimeBenchmarkResult(
                benchmark_id=benchmark_id,
                status=TranscriptionRuntimeBenchmarkStatus.TIMED_OUT,
                requested_device=requested_device,
                actual_device=selected_device,
                runtime_status=RuntimeCheckStatus.FAILED,
                model_status=selection.model_status,
                inference_status="inference_timeout",
                selected_model=selection.model_entry,
                selected_compute_type=compute_type,
                started_at=started_at,
                completed_at=utc_now(),
                load_duration_ms=None,
                inference_duration_ms=None,
                total_duration_ms=_duration_ms(started_monotonic, time.monotonic()),
                audio_duration_ms=None,
                real_time_factor=None,
                approximate_ram_before=hardware_profile.ram_available_bytes,
                approximate_ram_peak=hardware_profile.ram_available_bytes,
                approximate_ram_after=hardware_profile.ram_available_bytes,
                approximate_vram_before=_query_nvidia_vram_free_bytes() if selected_device == "cuda" else None,
                approximate_vram_peak=None,
                approximate_vram_after=_query_nvidia_vram_free_bytes() if selected_device == "cuda" else None,
                transcript_present=False,
                segment_count=0,
                detected_language=None,
                warnings=tuple(warnings),
                safe_error_category=TranscriptionRuntimeBenchmarkErrorCode.INFERENCE_TIMEOUT.value,
                safe_error_message="El benchmark excedio el tiempo permitido.",
                readiness=TranscriptionRuntimeBenchmarkReadiness.UNKNOWN,
                evidence=tuple(evidence),
                benchmark_version=BENCHMARK_VERSION,
                fixture_id=request.fixture_id,
                requested_profile=selection.profile.profile_id if selection.profile else request.requested_profile,
                model_component_id=selection.model_entry.component_id,
                compute_policy=compute_type,
            )
            self._persist_runtime_check(selection=selection, result=result, runtime_backend=backend, persist_result=persist_result)
            self._append_event(
                event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_COMPLETED,
                message_safe="El benchmark excedio el tiempo permitido.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={"benchmark_id": benchmark_id, "fixture_id": request.fixture_id, "reason": result.safe_error_category},
            )
            return result

        self._append_event(
            event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_STARTED,
            message_safe="Inicio de benchmark funcional de transcripcion.",
            selection=selection,
            benchmark_id=benchmark_id,
            payload={
                "benchmark_id": benchmark_id,
                "fixture_id": request.fixture_id,
                "requested_profile": selection.profile.profile_id if selection.profile else request.requested_profile,
                "requested_device": selected_device,
                "model_component_id": selection.model_entry.component_id,
            },
        )

        fixture_path: Path | None = None
        runtime_status = RuntimeCheckStatus.READY if backend.available else RuntimeCheckStatus.DEGRADED
        error_category: TranscriptionRuntimeBenchmarkErrorCode | None = None
        error_message: str | None = None
        transcript_present = False
        segment_count = 0
        detected_language: str | None = None
        inference_status = "completed"
        load_duration_ms: int | None = None
        inference_duration_ms: int | None = None
        total_duration_ms: int | None = None
        audio_duration_ms: int | None = None
        approx_ram_before = hardware_profile.ram_available_bytes
        approx_ram_peak = approx_ram_before
        approx_ram_after = approx_ram_before
        approx_vram_before = None
        approx_vram_peak = None
        approx_vram_after = None
        actual_device = selected_device
        selected_model_name = selection.model_name or "small"
        model = None
        try:
            self._append_event(
                event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_STARTED,
                message_safe="Preparando fixture de benchmark.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={"benchmark_id": benchmark_id, "fixture_id": request.fixture_id},
            )
            fixture_path, audio_duration_ms, fixture_notes = self._prepare_fixture(request.fixture_id)
            warnings.extend(fixture_notes)
            if self._deadline_exceeded(started_monotonic, timeout_seconds):
                raise TimeoutError("benchmark timeout before model load")
            self._append_event(
                event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_STARTED,
                message_safe="Cargando modelo local para benchmark.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={"benchmark_id": benchmark_id, "fixture_id": request.fixture_id, "model_component_id": selection.model_entry.component_id},
            )
            actual_device = selected_device if selected_device != "auto" else ("cuda" if backend.available and "int8_float16" in backend.supported_compute_types else "cpu")
            compute_type = self._resolve_compute_type(profile=selection.profile, device=actual_device, backend=backend) or compute_type
            approx_vram_before = _query_nvidia_vram_free_bytes() if actual_device == "gpu" else None
            approx_vram_peak = approx_vram_before
            approx_vram_after = approx_vram_before
            load_started = time.monotonic()
            model = engine.load_model(model_name=selected_model_name, device=actual_device, compute_type=compute_type)
            load_duration_ms = _duration_ms(load_started, time.monotonic())
            ram_after_load = _system_ram_available_bytes()
            approx_ram_peak = min(
                value for value in (approx_ram_peak, ram_after_load) if value is not None
            ) if approx_ram_peak is not None and ram_after_load is not None else (approx_ram_peak if ram_after_load is None else ram_after_load)
            if actual_device == "gpu":
                approx_vram_peak = min(filter(lambda value: value is not None, [approx_vram_peak, _query_nvidia_vram_free_bytes()])) if approx_vram_peak is not None else _query_nvidia_vram_free_bytes()
            if self._deadline_exceeded(started_monotonic, timeout_seconds):
                raise TimeoutError("benchmark timeout after model load")
            inference_started = time.monotonic()
            segments_iter, info = model.transcribe(
                str(fixture_path),
                language=None,
                beam_size=selection.profile.beam_size if selection.profile and selection.profile.beam_size is not None else 1,
                word_timestamps=bool(selection.profile.word_timestamps) if selection.profile else False,
                vad_filter=(selection.profile.vad_policy != "disabled") if selection.profile else False,
            )
            transcript_parts: list[str] = []
            for segment in segments_iter:
                if cancellation_token is not None and cancellation_token.cancelled():
                    error_category = TranscriptionRuntimeBenchmarkErrorCode.CANCELLATION_REQUESTED
                    raise RuntimeError("La cancelacion fue solicitada.")
                if self._deadline_exceeded(started_monotonic, timeout_seconds):
                    raise TimeoutError("benchmark timeout during inference")
                segment_count += 1
                text = str(getattr(segment, "text", "")).strip()
                if text:
                    transcript_parts.append(text)
            inference_duration_ms = _duration_ms(inference_started, time.monotonic())
            transcript_present = bool(" ".join(transcript_parts).strip())
            detected_language = getattr(info, "language", None)
            total_duration_ms = _duration_ms(started_monotonic, time.monotonic())
            if approx_vram_peak is None and actual_device == "gpu":
                approx_vram_peak = _query_nvidia_vram_free_bytes()
            approx_ram_after = _system_ram_available_bytes()
            approx_vram_after = _query_nvidia_vram_free_bytes() if actual_device == "gpu" else None
            if transcript_present:
                status = TranscriptionRuntimeBenchmarkStatus.COMPLETED
                readiness = TranscriptionRuntimeBenchmarkReadiness.READY
            else:
                status = TranscriptionRuntimeBenchmarkStatus.COMPLETED_WITH_WARNINGS
                readiness = TranscriptionRuntimeBenchmarkReadiness.DEGRADED
                error_category = error_category or TranscriptionRuntimeBenchmarkErrorCode.INFERENCE_EMPTY
                error_message = error_message or "La inferencia termino sin texto visible."
                inference_status = "inference_empty"
                warnings.append("La inferencia termino sin texto visible.")
            if warnings:
                status = TranscriptionRuntimeBenchmarkStatus.COMPLETED_WITH_WARNINGS if status == TranscriptionRuntimeBenchmarkStatus.COMPLETED else status
                readiness = TranscriptionRuntimeBenchmarkReadiness.READY_WITH_WARNINGS if readiness == TranscriptionRuntimeBenchmarkReadiness.READY else readiness
        except TimeoutError as exc:
            status = TranscriptionRuntimeBenchmarkStatus.TIMED_OUT
            inference_status = "inference_timeout"
            error_category = TranscriptionRuntimeBenchmarkErrorCode.INFERENCE_TIMEOUT
            error_message = str(exc)
            readiness = TranscriptionRuntimeBenchmarkReadiness.UNKNOWN
        except RuntimeError as exc:
            if error_category == TranscriptionRuntimeBenchmarkErrorCode.CANCELLATION_REQUESTED:
                status = TranscriptionRuntimeBenchmarkStatus.CANCELLED
                inference_status = "cancelled"
                readiness = TranscriptionRuntimeBenchmarkReadiness.UNKNOWN
                error_message = str(exc)
            else:
                status = TranscriptionRuntimeBenchmarkStatus.FAILED
                inference_status = "inference_failed"
                readiness = TranscriptionRuntimeBenchmarkReadiness.DEGRADED
                error_category = error_category or TranscriptionRuntimeBenchmarkErrorCode.INFERENCE_FAILED
                error_message = str(exc)
        except Exception as exc:
            status = TranscriptionRuntimeBenchmarkStatus.FAILED
            inference_status = "unexpected_error"
            readiness = TranscriptionRuntimeBenchmarkReadiness.UNKNOWN
            error_category = error_category or TranscriptionRuntimeBenchmarkErrorCode.UNEXPECTED_ERROR
            error_message = str(exc)
        finally:
            self._append_event(
                event_type=ComponentEventType.COMPONENT_HEALTH_CHECK_COMPLETED,
                message_safe="Benchmark funcional de transcripcion completado.",
                selection=selection,
                benchmark_id=benchmark_id,
                payload={
                    "benchmark_id": benchmark_id,
                    "fixture_id": request.fixture_id,
                    "status": status.value if isinstance(status, TranscriptionRuntimeBenchmarkStatus) else str(status),
                    "readiness": readiness.value if isinstance(readiness, TranscriptionRuntimeBenchmarkReadiness) else str(readiness),
                    "model_component_id": selection.model_entry.component_id,
                },
            )
            try:
                engine.release_model()
            except Exception as release_exc:
                warnings.append(f"resource_release_failed: {release_exc}")
                if status == TranscriptionRuntimeBenchmarkStatus.COMPLETED:
                    status = TranscriptionRuntimeBenchmarkStatus.COMPLETED_WITH_WARNINGS
                    readiness = TranscriptionRuntimeBenchmarkReadiness.READY_WITH_WARNINGS
                    error_category = error_category or TranscriptionRuntimeBenchmarkErrorCode.RESOURCE_RELEASE_FAILED
                    error_message = str(release_exc)
            gc.collect()

        benchmark = TranscriptionRuntimeBenchmarkResult(
            benchmark_id=benchmark_id,
            status=status,
            requested_device=requested_device,
            actual_device=actual_device,
            runtime_status=runtime_status,
            model_status=selection.model_status,
            inference_status=inference_status,
            selected_model=selection.model_entry,
            selected_compute_type=compute_type,
            started_at=started_at,
            completed_at=utc_now(),
            load_duration_ms=load_duration_ms,
            inference_duration_ms=inference_duration_ms,
            total_duration_ms=total_duration_ms or _duration_ms(started_monotonic, time.monotonic()),
            audio_duration_ms=audio_duration_ms,
            real_time_factor=(None if inference_duration_ms is None or not audio_duration_ms else (inference_duration_ms / 1000.0) / (audio_duration_ms / 1000.0)),
            approximate_ram_before=approx_ram_before,
            approximate_ram_peak=approx_ram_peak,
            approximate_ram_after=approx_ram_after,
            approximate_vram_before=approx_vram_before,
            approximate_vram_peak=approx_vram_peak,
            approximate_vram_after=approx_vram_after,
            transcript_present=transcript_present,
            segment_count=segment_count,
            detected_language=detected_language,
            warnings=tuple(dict.fromkeys(warnings)),
            safe_error_category=_normalize_error_category(error_category.value if isinstance(error_category, TranscriptionRuntimeBenchmarkErrorCode) else error_category),
            safe_error_message=error_message,
            readiness=readiness,
            evidence=tuple(
                dict.fromkeys(
                    evidence
                    + [
                        f"runtime_status={runtime_backend.status.value}",
                        f"backend_status={backend.backend}",
                        f"selected_compute_type={compute_type}",
                        f"audio_duration_ms={audio_duration_ms}",
                    ]
                )
            ),
            benchmark_version=BENCHMARK_VERSION,
            fixture_id=request.fixture_id,
            requested_profile=selection.profile.profile_id if selection.profile else request.requested_profile,
            model_component_id=selection.model_entry.component_id if selection.model_entry else request.model_component_id,
            compute_policy=compute_type,
        )
        self._persist_runtime_check(selection=selection, result=benchmark, runtime_backend=backend, persist_result=persist_result)
        return benchmark

    def latest_benchmark(self) -> TranscriptionRuntimeBenchmarkResult | None:
        checks = [record for record in self.repository.list_runtime_checks() if (record.metadata or {}).get("check_kind") == BENCHMARK_CHECK_KIND]
        if not checks:
            return None
        latest = max(checks, key=lambda record: record.checked_at or record.updated_at or record.created_at or _utc_now())
        return self._runtime_check_to_result(latest)

    def _runtime_check_to_result(self, record: RuntimeCheckRecord) -> TranscriptionRuntimeBenchmarkResult:
        metadata = dict(record.metadata or {})
        selected_model = self._catalog_entry_from_model(str(metadata.get("model_component_id") or "").split(".", 1)[-1]) if metadata.get("model_component_id") else None
        status = TranscriptionRuntimeBenchmarkStatus(metadata.get("status") or record.status.value)
        readiness = TranscriptionRuntimeBenchmarkReadiness(metadata.get("readiness") or TranscriptionRuntimeBenchmarkReadiness.UNKNOWN.value)
        return TranscriptionRuntimeBenchmarkResult(
            benchmark_id=str(metadata.get("benchmark_id") or record.component_id),
            status=status,
            requested_device=str(metadata.get("requested_device") or "auto"),
            actual_device=metadata.get("actual_device"),
            runtime_status=RuntimeCheckStatus(metadata.get("runtime_status")) if metadata.get("runtime_status") else record.status,
            model_status=ComponentInstallationStatus(metadata.get("model_status")) if metadata.get("model_status") else (ComponentInstallationStatus.READY if record.runtime_importable else ComponentInstallationStatus.MISSING),
            inference_status=str(metadata.get("inference_status") or status.value),
            selected_model=selected_model,
            selected_compute_type=metadata.get("selected_compute_type"),
            started_at=record.checked_at or record.created_at or _utc_now(),
            completed_at=record.checked_at or record.updated_at or record.created_at,
            load_duration_ms=metadata.get("load_duration_ms"),
            inference_duration_ms=metadata.get("inference_duration_ms"),
            total_duration_ms=metadata.get("total_duration_ms"),
            audio_duration_ms=metadata.get("audio_duration_ms"),
            real_time_factor=metadata.get("real_time_factor"),
            approximate_ram_before=metadata.get("approximate_ram_before"),
            approximate_ram_peak=metadata.get("approximate_ram_peak"),
            approximate_ram_after=metadata.get("approximate_ram_after"),
            approximate_vram_before=metadata.get("approximate_vram_before"),
            approximate_vram_peak=metadata.get("approximate_vram_peak"),
            approximate_vram_after=metadata.get("approximate_vram_after"),
            transcript_present=bool(metadata.get("transcript_present")),
            segment_count=int(metadata.get("segment_count") or 0),
            detected_language=metadata.get("detected_language"),
            warnings=tuple((record.warning_message or "").split("; ")) if record.warning_message else (),
            safe_error_category=record.error_code,
            safe_error_message=record.error_message,
            readiness=readiness,
            evidence=tuple(metadata.get("evidence") or ()),
            benchmark_version=int(metadata.get("benchmark_version") or BENCHMARK_VERSION),
            fixture_id=metadata.get("fixture_id"),
            requested_profile=str(metadata.get("requested_profile") or "balanced"),
            model_component_id=str(metadata.get("model_component_id") or record.component_id),
            compute_policy=metadata.get("compute_policy"),
        )

    def present(self, report: TranscriptionRuntimeBenchmarkResult | None) -> TranscriptionRuntimeBenchmarkPresentation:
        if report is None:
            return TranscriptionRuntimeBenchmarkPresentation(
                title="Sin benchmark",
                message="Todavia no se ha ejecutado una prueba funcional.",
            )
        if report.status in {TranscriptionRuntimeBenchmarkStatus.COMPLETED, TranscriptionRuntimeBenchmarkStatus.COMPLETED_WITH_WARNINGS}:
            if report.readiness == TranscriptionRuntimeBenchmarkReadiness.READY:
                return TranscriptionRuntimeBenchmarkPresentation(
                    title="Listo",
                    message="Tu computadora está lista para transcribir.",
                    details=report.to_dict(),
                )
            if report.readiness == TranscriptionRuntimeBenchmarkReadiness.READY_WITH_WARNINGS:
                return TranscriptionRuntimeBenchmarkPresentation(
                    title="Listo con advertencias",
                    message="La transcripcion funcional termino correctamente, pero hubo advertencias.",
                    details=report.to_dict(),
                )
            if report.transcript_present:
                return TranscriptionRuntimeBenchmarkPresentation(
                    title="Funcionando",
                    message="La prueba termino y el motor pudo procesar audio local, pero conviene revisar las advertencias.",
                    details=report.to_dict(),
                )
        if report.safe_error_category == TranscriptionRuntimeBenchmarkErrorCode.MODEL_MISSING.value:
            return TranscriptionRuntimeBenchmarkPresentation(
                title="Modelo faltante",
                message="Se necesita instalar un modelo local para comprobar el rendimiento.",
                details=report.to_dict(),
            )
        if report.safe_error_category == TranscriptionRuntimeBenchmarkErrorCode.GPU_RUNTIME_MISSING.value:
            return TranscriptionRuntimeBenchmarkPresentation(
                title="GPU no disponible",
                message="Se detectó una GPU, pero todavía falta el runtime necesario para probarla.",
                details=report.to_dict(),
            )
        if report.status == TranscriptionRuntimeBenchmarkStatus.TIMED_OUT:
            return TranscriptionRuntimeBenchmarkPresentation(
                title="Tiempo agotado",
                message="La prueba excedio el tiempo permitido.",
                details=report.to_dict(),
            )
        if report.status == TranscriptionRuntimeBenchmarkStatus.CANCELLED:
            return TranscriptionRuntimeBenchmarkPresentation(
                title="Cancelado",
                message="La prueba fue cancelada antes de completarse.",
                details=report.to_dict(),
            )
        return TranscriptionRuntimeBenchmarkPresentation(
            title="Modo limitado",
            message="La transcripcion puede continuar en modo limitado.",
            details=report.to_dict(),
        )
