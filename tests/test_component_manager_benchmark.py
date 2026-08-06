from __future__ import annotations

import tempfile
import time
import unittest
import wave
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.services.transcription_capability_resolver import TranscriptionCapabilityResolver
from creator_intelligence_studio.application.services.transcription_runtime_benchmark_service import TranscriptionRuntimeBenchmarkService
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog, build_default_transcription_profiles
from creator_intelligence_studio.domain.components.entities import (
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.hardware.entities import DiskVolumeSummary, GpuSummary, HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.transcription.benchmark import (
    TranscriptionRuntimeBenchmarkReadiness,
    TranscriptionRuntimeBenchmarkStatus,
)
from creator_intelligence_studio.domain.transcription.profiles import TranscriptionProfileDefinition
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionBackendInfo, TranscriptionModelInfo, TranscriptionModelStatus, TranscriptionCancellationToken
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_component_manager_repository import SQLiteComponentManagerRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


def _make_settings() -> AppSettings:
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        models_directory="models",
        artifacts_directory="artifacts",
        preferred_compute_backend="cuda",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="runtime.db",
        database_timeout_seconds=5.0,
        audio_cache_version="v1",
    )


def _write_wav(destination: Path, *, duration_seconds: float = 2.0, sample_rate: int = 16000) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * int(duration_seconds * sample_rate))


def _demo_audio_side_effect(destination: Path, *, text: str, duration_seconds: float = 2.0):
    _write_wav(destination, duration_seconds=1.5)
    return destination, ()


class FakeModelManager:
    def __init__(self, models_root: Path, *, installed_models: set[str] | None = None) -> None:
        self.models_root = models_root
        self.installed_models = installed_models or set()
        self.download_calls: list[str] = []

    def inspect_model_availability(self, model_name: str):
        installed = model_name in self.installed_models
        status = TranscriptionModelStatus.INSTALLED if installed else TranscriptionModelStatus.NOT_INSTALLED
        return TranscriptionModelInfo(
            model_name=model_name,
            profile={"base": "fast", "small": "balanced", "medium": "maximum_quality"}.get(model_name, "balanced"),
            path=str(self.models_root / model_name),
            installed=installed,
            size_bytes=1024 if installed else None,
            notes="Modelo disponible en caché local." if installed else "Modelo no instalado.",
            status=status,
        )

    def download_root(self, model_name: str) -> str:
        return str(self.models_root / model_name)

    def list_models(self):
        return tuple(self.inspect_model_availability(model_name) for model_name in ("base", "small", "medium"))

    def get_model_status(self, model_name: str):
        return self.inspect_model_availability(model_name)


class FakeHardwareService:
    def __init__(self, *, hardware_profile: HardwareProfile, runtime_check: RuntimeCheckRecord) -> None:
        self.hardware_profile = hardware_profile
        self.runtime_check = runtime_check

    def collect_inventory(self, *, persist: bool = False) -> HardwareProfile:
        return self.hardware_profile

    def collect_runtime_check(self, *, persist: bool = False) -> RuntimeCheckRecord:
        return self.runtime_check


class FakeBenchmarkModel:
    def __init__(self, *, text: str, delay_seconds: float = 0.0) -> None:
        self.text = text
        self.delay_seconds = delay_seconds

    def transcribe(self, audio_path: str, language=None, beam_size=None, word_timestamps=None, vad_filter=None):
        def _iter():
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            yield SimpleNamespace(
                id=0,
                start=0.0,
                end=1.0,
                text=self.text,
                words=(),
            )

        return _iter(), SimpleNamespace(language="es", language_probability=0.99, duration=2.0)


class FakeBenchmarkEngine:
    def __init__(
        self,
        *,
        backend_available: bool = True,
        text: str = "hola",
        delay_seconds: float = 0.0,
        supported_compute_types: tuple[str, ...] = ("int8", "int8_float16"),
    ) -> None:
        self.backend_available = backend_available
        self.text = text
        self.delay_seconds = delay_seconds
        self.supported_compute_types = supported_compute_types
        self.release_calls = 0
        self.last_load: tuple[str, str, str] | None = None

    def verify_backend(self):
        return TranscriptionBackendInfo(
            available=self.backend_available,
            device_count=1 if self.backend_available else 0,
            supported_compute_types=self.supported_compute_types,
            cuda_runtime_available=True,
            cudnn_available=True,
            dll_directories=(),
            backend="cuda" if self.backend_available else "cpu",
            fallback_reason=None if self.backend_available else "CUDA no disponible.",
            errors=(),
            version="4.8.1",
            ctranslate2_version="4.8.1",
            faster_whisper_version="1.2.1",
        )

    def load_model(self, *, model_name: str, device: str, compute_type: str):
        self.last_load = (model_name, device, compute_type)
        return FakeBenchmarkModel(text=self.text, delay_seconds=self.delay_seconds)

    def release_model(self) -> None:
        self.release_calls += 1


class BenchmarkContractTests(unittest.TestCase):
    def _paths(self, temp_dir: str) -> ProjectPaths:
        settings = _make_settings()
        paths = ProjectPaths.from_settings(Path(temp_dir), settings)
        paths.ensure_runtime_directories()
        return paths

    def _repository(self, temp_dir: str) -> SQLiteComponentManagerRepository:
        settings = _make_settings()
        paths = self._paths(temp_dir)
        database = build_database(settings, paths)
        with database.connect() as connection:
            run_migrations(connection)
        return SQLiteComponentManagerRepository(database)

    def _hardware_profile(self, *, gpu_status: HardwareCapabilityState = HardwareCapabilityState.NOT_DETECTED) -> HardwareProfile:
        return HardwareProfile(
            generated_at=datetime.now(tz=timezone.utc),
            platform="Windows",
            architecture="AMD64",
            cpu_logical_count=8,
            cpu_summary="Windows AMD64; logical=8",
            ram_total_bytes=16 * 1024 * 1024 * 1024,
            ram_available_bytes=8 * 1024 * 1024 * 1024,
            gpu=GpuSummary(
                vendor="nvidia" if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
                name="GeForce RTX" if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
                driver_version="552.12" if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
                vram_total_bytes=8 * 1024 * 1024 * 1024 if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
                cuda_visible=gpu_status != HardwareCapabilityState.NOT_DETECTED,
                cuda_runtime_reported="12.4" if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
                ctranslate2_cuda_available=gpu_status != HardwareCapabilityState.NOT_DETECTED,
                status=gpu_status,
                notes="GPU NVIDIA detectada; falta prueba funcional de transcripcion." if gpu_status == HardwareCapabilityState.REPORTED_NOT_TESTED else None,
            ),
            driver_summary="552.12" if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
            cuda_reported="12.4" if gpu_status != HardwareCapabilityState.NOT_DETECTED else None,
            ctranslate2_cuda_status=HardwareCapabilityState.REPORTED_NOT_TESTED if gpu_status != HardwareCapabilityState.NOT_DETECTED else HardwareCapabilityState.NOT_DETECTED,
            disk_volumes=(DiskVolumeSummary(path="C:\\models", free_bytes=64 * 1024 * 1024 * 1024, total_bytes=128 * 1024 * 1024 * 1024, status=HardwareCapabilityState.DETECTED),),
            detection_source="local",
            status=gpu_status if gpu_status != HardwareCapabilityState.NOT_DETECTED else HardwareCapabilityState.NOT_DETECTED,
            warnings=(),
            errors=(),
        )

    def _runtime_check(self, *, status: RuntimeCheckStatus = RuntimeCheckStatus.READY) -> RuntimeCheckRecord:
        return RuntimeCheckRecord(
            component_id="transcription-runtime.ctranslate2",
            status=status,
            runtime_importable=True,
            runtime_version="4.8.1",
            device_count=1,
            supported_compute_types=("int8", "int8_float16"),
            notes="Runtime listo.",
            warning_message=None,
            error_code=None,
            error_message=None,
            metadata={},
            checked_at=datetime.now(tz=timezone.utc),
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )

    def _install_component(self, repo: SQLiteComponentManagerRepository, component_id: str) -> None:
        repo.upsert_installation(
            ComponentInstallation(
                component_id=component_id,
                installation_status=ComponentInstallationStatus.READY,
                installed_version="1",
                revision="1",
                install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
                location_path=None,
                location_reference=None,
                detected_at=datetime.now(tz=timezone.utc),
                verified_at=datetime.now(tz=timezone.utc),
                health_status=RuntimeCheckStatus.READY,
                source="test",
                managed=False,
                metadata={},
            )
        )

    def test_cpu_benchmark_succeeds_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repository(temp_dir)
            paths = self._paths(temp_dir)
            self._install_component(repo, "ffmpeg")
            self._install_component(repo, "ffprobe")
            self._install_component(repo, "transcription-runtime.ctranslate2")
            self._install_component(repo, "transcription-model.small")
            model_manager = FakeModelManager(paths.models_directory, installed_models={"small"})
            hardware_service = FakeHardwareService(hardware_profile=self._hardware_profile(), runtime_check=self._runtime_check())
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=model_manager)
            benchmark = TranscriptionRuntimeBenchmarkService(
                paths=paths,
                repository=repo,
                model_manager=model_manager,
                resolver=resolver,
                hardware_service=hardware_service,
                engine_factory=lambda manager, logger: FakeBenchmarkEngine(backend_available=True, text="hola mundo"),
            )
            with (
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service.create_demo_audio", side_effect=_demo_audio_side_effect),
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service._system_ram_available_bytes", return_value=8 * 1024 * 1024 * 1024),
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service._query_nvidia_vram_free_bytes", return_value=None),
            ):
                report = benchmark.run_benchmark(requested_profile="balanced", requested_device="cpu", persist_result=True, fixture_id="cpu_benchmark")
            self.assertEqual(report.status, TranscriptionRuntimeBenchmarkStatus.COMPLETED)
            self.assertTrue(report.transcript_present)
            self.assertEqual(report.selected_compute_type, "int8")
            self.assertGreaterEqual(report.segment_count, 1)
            self.assertIsNotNone(benchmark.latest_benchmark())
            self.assertEqual(len(repo.list_runtime_checks()), 1)
            self.assertEqual(benchmark.present(report).title, "Listo")

    def test_gpu_benchmark_success_enables_resolver_gpu_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repository(temp_dir)
            paths = self._paths(temp_dir)
            self._install_component(repo, "ffmpeg")
            self._install_component(repo, "ffprobe")
            self._install_component(repo, "transcription-runtime.ctranslate2")
            self._install_component(repo, "transcription-model.small")
            model_manager = FakeModelManager(paths.models_directory, installed_models={"small"})
            hardware_profile = self._hardware_profile(gpu_status=HardwareCapabilityState.REPORTED_NOT_TESTED)
            hardware_service = FakeHardwareService(hardware_profile=hardware_profile, runtime_check=self._runtime_check())
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=model_manager)
            benchmark = TranscriptionRuntimeBenchmarkService(
                paths=paths,
                repository=repo,
                model_manager=model_manager,
                resolver=resolver,
                hardware_service=hardware_service,
                engine_factory=lambda manager, logger: FakeBenchmarkEngine(backend_available=True, text="hola gpu"),
            )
            with (
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service.create_demo_audio", side_effect=_demo_audio_side_effect),
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service._system_ram_available_bytes", return_value=8 * 1024 * 1024 * 1024),
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service._query_nvidia_vram_free_bytes", return_value=4 * 1024 * 1024 * 1024),
            ):
                report = benchmark.run_benchmark(requested_profile="balanced", requested_device="gpu", persist_result=True, fixture_id="gpu_benchmark")
            resolved = resolver.resolve(requested_profile="balanced", preferred_device="gpu", hardware_profile=hardware_profile)
            self.assertEqual(report.status, TranscriptionRuntimeBenchmarkStatus.COMPLETED)
            self.assertEqual(report.actual_device, "cuda")
            self.assertEqual(resolved.selected_device, "gpu")
            self.assertEqual(resolved.readiness, "ready")

    def test_missing_model_does_not_download_and_returns_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repository(temp_dir)
            paths = self._paths(temp_dir)
            self._install_component(repo, "ffmpeg")
            self._install_component(repo, "ffprobe")
            self._install_component(repo, "transcription-runtime.ctranslate2")
            model_manager = FakeModelManager(paths.models_directory, installed_models=set())
            hardware_service = FakeHardwareService(hardware_profile=self._hardware_profile(), runtime_check=self._runtime_check())
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=model_manager)
            benchmark = TranscriptionRuntimeBenchmarkService(
                paths=paths,
                repository=repo,
                model_manager=model_manager,
                resolver=resolver,
                hardware_service=hardware_service,
                engine_factory=lambda manager, logger: FakeBenchmarkEngine(backend_available=True, text="hola"),
            )
            with patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service.create_demo_audio", side_effect=_demo_audio_side_effect):
                report = benchmark.run_benchmark(requested_profile="balanced", requested_device="cpu", model_component_id="transcription-model.small", persist_result=True)
            self.assertEqual(report.safe_error_category, "model_missing")
            self.assertEqual(report.inference_status, "benchmark_unavailable_missing_model")
            self.assertEqual(model_manager.download_calls, [])
            self.assertIsNotNone(benchmark.latest_benchmark())

    def test_gpu_runtime_missing_fails_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repository(temp_dir)
            paths = self._paths(temp_dir)
            self._install_component(repo, "ffmpeg")
            self._install_component(repo, "ffprobe")
            self._install_component(repo, "transcription-runtime.ctranslate2")
            self._install_component(repo, "transcription-model.small")
            model_manager = FakeModelManager(paths.models_directory, installed_models={"small"})
            hardware_service = FakeHardwareService(hardware_profile=self._hardware_profile(gpu_status=HardwareCapabilityState.REPORTED_NOT_TESTED), runtime_check=self._runtime_check())
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=model_manager)
            benchmark = TranscriptionRuntimeBenchmarkService(
                paths=paths,
                repository=repo,
                model_manager=model_manager,
                resolver=resolver,
                hardware_service=hardware_service,
                engine_factory=lambda manager, logger: FakeBenchmarkEngine(backend_available=False, text="hola"),
            )
            with patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service.create_demo_audio", side_effect=_demo_audio_side_effect):
                report = benchmark.run_benchmark(requested_profile="balanced", requested_device="gpu", persist_result=False, fixture_id="gpu_runtime_missing")
            self.assertEqual(report.safe_error_category, "gpu_runtime_missing")
            self.assertEqual(report.status, TranscriptionRuntimeBenchmarkStatus.FAILED)
            self.assertFalse(report.transcript_present)

    def test_unsupported_compute_type_reports_incompatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repository(temp_dir)
            paths = self._paths(temp_dir)
            self._install_component(repo, "ffmpeg")
            self._install_component(repo, "ffprobe")
            self._install_component(repo, "transcription-runtime.ctranslate2")
            self._install_component(repo, "transcription-model.small")
            model_manager = FakeModelManager(paths.models_directory, installed_models={"small"})
            hardware_service = FakeHardwareService(hardware_profile=self._hardware_profile(), runtime_check=self._runtime_check())
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=model_manager)
            benchmark = TranscriptionRuntimeBenchmarkService(
                paths=paths,
                repository=repo,
                model_manager=model_manager,
                resolver=resolver,
                hardware_service=hardware_service,
                engine_factory=lambda manager, logger: FakeBenchmarkEngine(backend_available=True, text="hola", supported_compute_types=()),
            )
            with patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service.create_demo_audio", side_effect=_demo_audio_side_effect):
                report = benchmark.run_benchmark(requested_profile="balanced", requested_device="gpu", persist_result=False, fixture_id="unsupported_compute")
            self.assertEqual(report.safe_error_category, "unsupported_compute_type")
            self.assertEqual(report.status, TranscriptionRuntimeBenchmarkStatus.FAILED)
            self.assertFalse(report.transcript_present)

    def test_timeout_and_cancellation_terminal_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repository(temp_dir)
            paths = self._paths(temp_dir)
            self._install_component(repo, "ffmpeg")
            self._install_component(repo, "ffprobe")
            self._install_component(repo, "transcription-runtime.ctranslate2")
            self._install_component(repo, "transcription-model.small")
            model_manager = FakeModelManager(paths.models_directory, installed_models={"small"})
            hardware_service = FakeHardwareService(hardware_profile=self._hardware_profile(), runtime_check=self._runtime_check())
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=model_manager)
            delayed_engine = FakeBenchmarkEngine(backend_available=True, text="hola", )
            delayed_engine.delay_seconds = 0.2
            benchmark = TranscriptionRuntimeBenchmarkService(
                paths=paths,
                repository=repo,
                model_manager=model_manager,
                resolver=resolver,
                hardware_service=hardware_service,
                engine_factory=lambda manager, logger: delayed_engine,
            )
            with (
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service.create_demo_audio", side_effect=_demo_audio_side_effect),
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service._system_ram_available_bytes", return_value=8 * 1024 * 1024 * 1024),
                patch("creator_intelligence_studio.application.services.transcription_runtime_benchmark_service._query_nvidia_vram_free_bytes", return_value=None),
            ):
                timed_out = benchmark.run_benchmark(requested_profile="balanced", requested_device="cpu", timeout_seconds=0.01, fixture_id="timeout_case")
                cancelled = benchmark.run_benchmark(
                    requested_profile="balanced",
                    requested_device="cpu",
                    fixture_id="cancel_case",
                    cancellation_token=TranscriptionCancellationToken(is_cancelled=lambda: True),
                )
            self.assertEqual(timed_out.status, TranscriptionRuntimeBenchmarkStatus.TIMED_OUT)
            self.assertEqual(cancelled.status, TranscriptionRuntimeBenchmarkStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
