"""Adaptador de infraestructura para faster-whisper y CTranslate2."""

from __future__ import annotations

import gc
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.transcription.errors import TranscriptionBackendError
from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionBackendInfo,
    TranscriptionCancellationToken,
    TranscriptionOptions,
    TranscriptionProgress,
    TranscriptionResult,
    TranscriptionSegmentData,
    TranscriptionVerificationResult,
    TranscriptionWordData,
)
from creator_intelligence_studio.domain.transcription.services import (
    build_configuration_fingerprint,
    build_source_audio_fingerprint,
    normalize_device,
    normalize_language,
    normalize_model_name,
    normalize_profile,
    normalize_requested_compute_type,
)
from creator_intelligence_studio.infrastructure.transcription.cuda_runtime_loader import (
    CudaRuntimeLocations,
    discover_cuda_runtime_locations,
    register_cuda_runtime_paths,
)
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.dates import utc_now


@dataclass(frozen=True, slots=True)
class BackendPlan:
    device: str
    compute_type: str
    fallback_reason: str | None = None


class FasterWhisperEngine:
    """Encapsula carga de modelos y transcripcion real."""

    def __init__(self, model_manager: TranscriptionModelManager, logger: logging.Logger | None = None) -> None:
        self.model_manager = model_manager
        self.logger = logger or logging.getLogger("creator_intelligence_studio.transcription")
        self._handles = []
        self._model = None
        self._loaded_key: tuple[str, str, str, str] | None = None
        self._backend_version: str | None = None
        self._ctranslate2_version: str | None = None
        self._faster_whisper_version: str | None = None
        self._runtime_locations: CudaRuntimeLocations | None = None

    @property
    def engine_name(self) -> str:
        return "faster-whisper"

    @property
    def engine_version(self) -> str | None:
        return self._faster_whisper_version

    @property
    def model_version(self) -> str | None:
        return self._loaded_key[0] if self._loaded_key else None

    def _ensure_versions(self) -> None:
        if self._ctranslate2_version is None:
            import ctranslate2

            self._ctranslate2_version = getattr(ctranslate2, "__version__", None)
        if self._faster_whisper_version is None:
            try:
                from importlib.metadata import version

                self._faster_whisper_version = version("faster-whisper")
            except Exception:
                self._faster_whisper_version = None

    def release_model(self) -> None:
        self._model = None
        self._loaded_key = None
        self._runtime_locations = None
        while self._handles:
            handle = self._handles.pop()
            try:
                close = getattr(handle, "close", None)
                if callable(close):
                    close()
            except Exception:
                continue

    def _import_backend(self, *, device: str):
        self._ensure_versions()
        if device == "cuda":
            self._runtime_locations = discover_cuda_runtime_locations()
            if not self._runtime_locations.available:
                raise TranscriptionBackendError(
                    "Faltan runtimes NVIDIA requeridos: " + ", ".join(self._runtime_locations.missing)
                )
            self._handles = register_cuda_runtime_paths(self._runtime_locations)
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover - depende de entorno
            raise TranscriptionBackendError(f"No se pudo importar faster-whisper: {exc}") from exc
        return WhisperModel

    def load_model(self, *, model_name: str, device: str, compute_type: str) -> Any:
        """Carga y reutiliza un modelo sin ejecutar inferencia."""

        return self._load_model(model_name=model_name, device=device, compute_type=compute_type)

    def verify_backend(self) -> TranscriptionBackendInfo:
        errors: list[str] = []
        runtime_locations = discover_cuda_runtime_locations()
        handles = []
        cuda_runtime_available = runtime_locations.cuda_runtime_bin is not None and runtime_locations.cublas_bin is not None
        cudnn_available = runtime_locations.cudnn_bin is not None
        device_count = 0
        supported_compute_types: tuple[str, ...] = ()
        backend = "cpu"
        fallback_reason = None
        try:
            handles = register_cuda_runtime_paths(runtime_locations)
        except Exception as exc:
            errors.append(str(exc))
        try:
            import ctranslate2

            self._ctranslate2_version = getattr(ctranslate2, "__version__", None)
            device_count = int(ctranslate2.get_cuda_device_count())
            supported_compute_types = tuple(ctranslate2.get_supported_compute_types("cuda"))
            if device_count > 0 and "int8_float16" in supported_compute_types and runtime_locations.available:
                backend = "cuda"
            else:
                backend = "cpu"
                fallback_reason = "CUDA no disponible o compute type no soportado."
        except Exception as exc:
            errors.append(str(exc))
            fallback_reason = fallback_reason or str(exc)
        try:
            from importlib.metadata import version

            faster_whisper_version = version("faster-whisper")
        except Exception:
            faster_whisper_version = None
        finally:
            while handles:
                handle = handles.pop()
                try:
                    close = getattr(handle, "close", None)
                    if callable(close):
                        close()
                except Exception:
                    continue
        return TranscriptionBackendInfo(
            available=backend == "cuda" and not errors,
            device_count=device_count,
            supported_compute_types=supported_compute_types,
            cuda_runtime_available=cuda_runtime_available,
            cudnn_available=cudnn_available,
            dll_directories=tuple(str(path) for path in runtime_locations.paths),
            backend=backend,
            fallback_reason=fallback_reason,
            errors=tuple(errors),
            version=self._ctranslate2_version,
            ctranslate2_version=self._ctranslate2_version,
            faster_whisper_version=faster_whisper_version,
        )

    def plan_runtime(self, options: TranscriptionOptions) -> BackendPlan:
        device = normalize_device(options.device)
        requested_compute_type = normalize_requested_compute_type(options.compute_type)
        normalize_profile(options.profile)
        normalize_model_name(options.model_name)
        if device == "cpu":
            return BackendPlan(device="cpu", compute_type=requested_compute_type or "int8")
        backend = self.verify_backend()
        if device == "cuda":
            if backend.available and "int8_float16" in backend.supported_compute_types:
                return BackendPlan(device="cuda", compute_type=requested_compute_type or "int8_float16")
            raise TranscriptionBackendError(
                backend.fallback_reason or "CUDA no disponible para el modelo solicitado."
            )
        if backend.available and "int8_float16" in backend.supported_compute_types:
            return BackendPlan(device="cuda", compute_type=requested_compute_type or "int8_float16")
        return BackendPlan(
            device="cpu",
            compute_type=requested_compute_type or "int8",
            fallback_reason=backend.fallback_reason or "Fallback a CPU por disponibilidad o compatibilidad.",
        )

    def _load_model(self, *, model_name: str, device: str, compute_type: str, model_path: Path | None = None) -> Any:
        WhisperModel = self._import_backend(device=device)
        model_status = self.model_manager.inspect_model_availability(model_name)
        if not model_status.installed:
            raise TranscriptionBackendError("El modelo local solicitado no esta instalado o no puede verificarse.")
        resolved_path = Path(model_path) if model_path is not None else Path(self.model_manager.download_root(model_name))
        key = (model_name, device, compute_type, str(resolved_path))
        if self._model is not None and self._loaded_key == key:
            return self._model
        self.release_model()
        self._model = WhisperModel(str(resolved_path), device=device, compute_type=compute_type)
        self._loaded_key = key
        return self._model

    def transcribe(
        self,
        *,
        video_asset_id: str,
        prepared_audio_asset_id: str,
        audio_path: Path,
        audio_size_bytes: int | None,
        audio_modified_at: str | None,
        options: TranscriptionOptions,
        cancellation_token: TranscriptionCancellationToken | None = None,
        progress_callback=None,
    ) -> TranscriptionResult:
        plan = self.plan_runtime(options)
        model = self._load_model(
            model_name=normalize_model_name(options.model_name),
            device=plan.device,
            compute_type=plan.compute_type,
            model_path=Path(options.model_cache_root) if options.model_cache_root else None,
        )
        if progress_callback is not None:
            progress_callback(TranscriptionProgress(phase="Cargando modelo", approximate=True))
        started = utc_now()
        try:
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=normalize_language(options.language),
                beam_size=options.beam_size,
                word_timestamps=options.word_timestamps,
                vad_filter=options.vad_filter,
            )
            collected_segments: list[TranscriptionSegmentData] = []
            full_text_parts: list[str] = []
            for segment in segments_iter:
                if cancellation_token is not None and cancellation_token.cancelled():
                    raise TranscriptionBackendError("La transcripcion fue cancelada por el usuario.")
                words = []
                if getattr(segment, "words", None):
                    for word in segment.words:
                        words.append(
                            TranscriptionWordData(
                                start_seconds=float(getattr(word, "start", 0.0) or 0.0),
                                end_seconds=float(getattr(word, "end", 0.0) or 0.0),
                                word=str(getattr(word, "word", "")),
                                probability=getattr(word, "probability", None),
                            )
                        )
                collected_segments.append(
                    TranscriptionSegmentData(
                        segment_index=int(getattr(segment, "id", len(collected_segments) + 1)),
                        start_seconds=float(getattr(segment, "start", 0.0) or 0.0),
                        end_seconds=float(getattr(segment, "end", 0.0) or 0.0),
                        text=str(getattr(segment, "text", "")).strip(),
                        confidence=getattr(segment, "avg_logprob", None),
                        no_speech_probability=getattr(segment, "no_speech_prob", None),
                        temperature=getattr(segment, "temperature", None),
                        words=tuple(words),
                    )
                )
                full_text_parts.append(str(getattr(segment, "text", "")).strip())
                if progress_callback is not None:
                    total_duration = float(getattr(info, "duration", 0.0) or 0.0)
                    current_end = float(getattr(segment, "end", 0.0) or 0.0)
                    ratio = (current_end / total_duration) if total_duration else None
                    progress_callback(
                        TranscriptionProgress(
                            phase="Transcribiendo",
                            progress_ratio=ratio,
                            current_segment_end_seconds=current_end,
                            total_duration_seconds=total_duration or None,
                            approximate=True,
                        )
                    )
            completed = utc_now()
            model_version = self._loaded_key[0] if self._loaded_key else None
            result = TranscriptionResult(
                transcription_id=None,
                video_asset_id=video_asset_id,
                prepared_audio_asset_id=prepared_audio_asset_id,
                status=TranscriptionStatus.COMPLETED.value,
                engine=self.engine_name,
                model_name=normalize_model_name(options.model_name),
                device=plan.device,
                compute_type=plan.compute_type,
                requested_language=normalize_language(options.language),
                detected_language=getattr(info, "language", None),
                language_probability=getattr(info, "language_probability", None),
                full_text=" ".join(part for part in full_text_parts if part).strip(),
                duration_seconds=float(getattr(info, "duration", 0.0) or 0.0),
                processing_time_seconds=(completed - started).total_seconds(),
                real_time_factor=(completed - started).total_seconds() / float(getattr(info, "duration", 1.0) or 1.0),
                segment_count=len(collected_segments),
                word_timestamps_enabled=options.word_timestamps,
                vad_enabled=options.vad_filter,
                source_audio_size_bytes=audio_size_bytes,
                source_audio_modified_at=audio_modified_at,
                source_audio_fingerprint="",
                configuration_fingerprint="",
                engine_version=self.engine_version,
                model_version=model_version,
                segments=tuple(collected_segments),
                warnings=(plan.fallback_reason,) if plan.fallback_reason else (),
            )
            return result
        except Exception as exc:
            raise TranscriptionBackendError(str(exc)) from exc
        finally:
            gc.collect()
