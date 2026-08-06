"""Servicio de aplicacion para transcripcion local."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.errors import ConflictError, NotFoundError
from creator_intelligence_studio.domain.transcription.entities import (
    Transcription,
    TranscriptionSegment,
    TranscriptionStatus,
)
from creator_intelligence_studio.domain.transcription.errors import (
    TranscriptionBackendError,
    TranscriptionStateError,
    TranscriptionValidationError,
)
from creator_intelligence_studio.domain.transcription.repositories import TranscriptionRepository
from creator_intelligence_studio.domain.transcription.services import (
    build_configuration_fingerprint,
    build_source_audio_fingerprint,
    normalize_device,
    normalize_language,
    normalize_model_name,
    normalize_profile,
    normalize_requested_compute_type,
    validate_transcription_options,
)
from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionBackendInfo,
    TranscriptionCancellationToken,
    TranscriptionExportFormat,
    TranscriptionModelInfo,
    TranscriptionModelStatus,
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionSegmentData,
    TranscriptionVerificationResult,
)
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import (
    SQLitePreparedAudioRepository,
)
from creator_intelligence_studio.infrastructure.transcription.faster_whisper_engine import (
    BackendPlan,
    FasterWhisperEngine,
)
from creator_intelligence_studio.infrastructure.transcription.model_manager import (
    TranscriptionModelManager,
)
from creator_intelligence_studio.infrastructure.transcription.transcription_exporter import (
    export_json,
    export_srt,
    export_txt,
)
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class TranscriptionReport:
    """Estado y resultado de una transcripcion."""

    video: VideoAsset
    prepared_audio: PreparedAudioAsset | None
    transcription: Transcription | None
    segments: tuple[TranscriptionSegment, ...]
    status: TranscriptionStatus
    is_stale: bool
    backend: TranscriptionBackendInfo | None
    model_status: TranscriptionModelInfo | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "prepared_audio": self.prepared_audio.to_dict() if self.prepared_audio else None,
            "transcription": self.transcription.to_dict() if self.transcription else None,
            "segments": [segment.to_dict() for segment in self.segments],
            "status": self.status.value,
            "is_stale": self.is_stale,
            "backend": self.backend.to_dict() if self.backend else None,
            "model_status": self.model_status.to_dict() if self.model_status else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionExportResult:
    """Resultado de exportacion de transcripcion."""

    video: VideoAsset
    transcription: Transcription
    format: TranscriptionExportFormat
    content: str
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "transcription": self.transcription.to_dict(),
            "format": self.format.value,
            "content": self.content,
            "path": self.path,
        }


class TranscriptionService:
    """Coordina backend, persistencia, exportacion y estado de transcripcion."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        video_repository: VideoRepository,
        prepared_audio_repository: SQLitePreparedAudioRepository,
        transcription_repository: TranscriptionRepository,
        model_manager: TranscriptionModelManager,
        engine: FasterWhisperEngine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.video_repository = video_repository
        self.prepared_audio_repository = prepared_audio_repository
        self.transcription_repository = transcription_repository
        self.model_manager = model_manager
        self.engine = engine or FasterWhisperEngine(model_manager=model_manager, logger=logger)
        self.logger = logger or logging.getLogger("creator_intelligence_studio.transcription")
        self._active_jobs: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _load_prepared_audio(self, video_id: str) -> PreparedAudioAsset | None:
        return self.prepared_audio_repository.get_by_video_asset_id(video_id)

    def _load_transcription(self, video_id: str) -> Transcription | None:
        return self.transcription_repository.get_by_video_asset_id(video_id)

    def _inspect_model_availability(self, model_name: str) -> TranscriptionModelInfo:
        inspector = getattr(self.model_manager, "inspect_model_availability", None)
        if callable(inspector):
            return inspector(model_name)
        return self.model_manager.get_model_status(model_name)

    def _controlled_export_root(self, video_id: str) -> Path:
        return self.paths.project_root / "cache" / "transcriptions" / video_id

    def _transcription_is_stale(
        self,
        transcription: Transcription | None,
        *,
        prepared_audio: PreparedAudioAsset | None,
        options: TranscriptionOptions | None = None,
    ) -> bool:
        if transcription is None:
            return False
        if prepared_audio is None or prepared_audio.status != PreparedAudioStatus.COMPLETED:
            return True
        if transcription.prepared_audio_asset_id != prepared_audio.id:
            return True
        if transcription.status != TranscriptionStatus.COMPLETED:
            return True
        if transcription.source_audio_fingerprint != build_source_audio_fingerprint(prepared_audio=prepared_audio):
            return True
        if options is not None:
            config_fingerprint = build_configuration_fingerprint(
                options,
                engine_version=transcription.engine_version,
                model_version=transcription.model_version,
            )
            if transcription.configuration_fingerprint != config_fingerprint:
                return True
        return False

    def _report(
        self,
        *,
        video: VideoAsset,
        prepared_audio: PreparedAudioAsset | None,
        transcription: Transcription | None,
        segments: list[TranscriptionSegment] | None = None,
        status: TranscriptionStatus | None = None,
        is_stale: bool = False,
        backend: TranscriptionBackendInfo | None = None,
        model_status: TranscriptionModelInfo | None = None,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
        progress_message: str | None = None,
    ) -> TranscriptionReport:
        if segments is not None:
            segment_values = tuple(segments)
        elif transcription is not None:
            segment_values = tuple(self.transcription_repository.list_segments(transcription.id))
        else:
            segment_values = ()
        resolved_status = status or (transcription.status if transcription else TranscriptionStatus.NOT_TRANSCRIBED)
        return TranscriptionReport(
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            segments=segment_values,
            status=resolved_status,
            is_stale=is_stale,
            backend=backend,
            model_status=model_status,
            warnings=warnings,
            errors=errors,
            progress_message=progress_message,
        )

    def verify_transcription_backend(self) -> TranscriptionVerificationResult:
        backend = self.engine.verify_backend()
        return TranscriptionVerificationResult(
            backend=backend,
            model_statuses=self.list_models(),
            notes=(backend.fallback_reason,) if backend.fallback_reason else (),
        )

    def list_models(self) -> tuple[TranscriptionModelInfo, ...]:
        return self.model_manager.list_models()

    def get_model_status(self, model_name: str) -> TranscriptionModelInfo:
        return self.model_manager.get_model_status(normalize_model_name(model_name))

    def verify_model(self, model_name: str) -> TranscriptionModelInfo:
        return self.model_manager.verify_model(normalize_model_name(model_name))

    def download_model(
        self,
        model_name: str,
        *,
        force: bool = False,
        progress_callback=None,
        cancellation_token: TranscriptionCancellationToken | None = None,
    ) -> TranscriptionModelInfo:
        return self.model_manager.download_model(
            normalize_model_name(model_name),
            force=force,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    def remove_model(self, model_name: str) -> bool:
        return self.model_manager.remove_model(normalize_model_name(model_name))

    def list_transcription_segments(self, transcription_id: str) -> list[TranscriptionSegment]:
        return self.transcription_repository.list_segments(transcription_id)

    def is_transcription_stale(self, video_id: str) -> bool:
        video = self._require_video(video_id)
        prepared_audio = self._load_prepared_audio(video.id)
        transcription = self._load_transcription(video.id)
        return self._transcription_is_stale(transcription, prepared_audio=prepared_audio)

    def cancel_transcription(self, video_id: str) -> bool:
        with self._lock:
            event = self._active_jobs.get(video_id)
            if event is None:
                return False
            event.set()
            return True

    def delete_transcription(self, video_id: str) -> bool:
        return self.transcription_repository.delete_by_video_asset_id(video_id)

    def _build_transcription_entity(
        self,
        *,
        transcription_id: str,
        video: VideoAsset,
        prepared_audio: PreparedAudioAsset,
        result: TranscriptionResult,
        options: TranscriptionOptions,
    ) -> tuple[Transcription, list[TranscriptionSegment]]:
        started_at = utc_now()
        source_fingerprint = build_source_audio_fingerprint(prepared_audio=prepared_audio)
        configuration_fingerprint = build_configuration_fingerprint(
            options,
            engine_version=result.engine_version,
            model_version=result.model_version,
        )
        transcription = Transcription(
            id=transcription_id,
            video_asset_id=video.id,
            prepared_audio_asset_id=prepared_audio.id,
            status=TranscriptionStatus.COMPLETED,
            engine=result.engine,
            model_name=result.model_name,
            device=result.device,
            compute_type=result.compute_type,
            requested_language=result.requested_language,
            detected_language=result.detected_language,
            language_probability=result.language_probability,
            full_text=result.full_text,
            duration_seconds=result.duration_seconds,
            processing_time_seconds=result.processing_time_seconds,
            real_time_factor=result.real_time_factor,
            segment_count=result.segment_count,
            word_timestamps_enabled=result.word_timestamps_enabled,
            vad_enabled=result.vad_enabled,
            source_audio_size_bytes=result.source_audio_size_bytes,
            source_audio_modified_at=from_iso_z(result.source_audio_modified_at),
            source_audio_fingerprint=source_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            engine_version=result.engine_version,
            model_version=result.model_version,
            warning_code=result.warning_code,
            warning_message=result.warning_message,
            error_code=result.error_code,
            error_message=result.error_message,
            started_at=from_iso_z(result.started_at),
            completed_at=from_iso_z(result.completed_at),
            created_at=from_iso_z(result.created_at) or started_at,
            updated_at=from_iso_z(result.updated_at) or started_at,
        )
        segments: list[TranscriptionSegment] = []
        now = utc_now()
        for segment in result.segments:
            segments.append(
                TranscriptionSegment(
                    id=str(uuid4()),
                    transcription_id=transcription_id,
                    segment_index=segment.segment_index,
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    text=segment.text,
                    confidence=segment.confidence,
                    no_speech_probability=segment.no_speech_probability,
                    temperature=segment.temperature,
                    created_at=now,
                )
            )
        return transcription, segments

    def _persist_status(
        self,
        *,
        transcription_id: str,
        video: VideoAsset,
        prepared_audio: PreparedAudioAsset | None,
        status: TranscriptionStatus,
        options: TranscriptionOptions,
        error_code: str | None = None,
        error_message: str | None = None,
        warning_code: str | None = None,
        warning_message: str | None = None,
        backend_version: str | None = None,
        model_version: str | None = None,
    ) -> Transcription:
        now = utc_now()
        transcription = Transcription(
            id=transcription_id,
            video_asset_id=video.id,
            prepared_audio_asset_id=prepared_audio.id if prepared_audio else "",
            status=status,
            engine="faster-whisper",
            model_name=options.model_name,
            device=normalize_device(options.device),
            compute_type=normalize_requested_compute_type(options.compute_type) or (
                "int8_float16" if normalize_device(options.device) != "cpu" else "int8"
            ),
            requested_language=normalize_language(options.language),
            detected_language=None,
            language_probability=None,
            full_text="",
            duration_seconds=0.0,
            processing_time_seconds=0.0,
            real_time_factor=0.0,
            segment_count=0,
            word_timestamps_enabled=options.word_timestamps,
            vad_enabled=options.vad_filter,
            source_audio_size_bytes=prepared_audio.file_size_bytes if prepared_audio else None,
            source_audio_modified_at=prepared_audio.source_file_modified_at if prepared_audio else None,
            source_audio_fingerprint=build_source_audio_fingerprint(prepared_audio=prepared_audio) if prepared_audio else "",
            configuration_fingerprint=build_configuration_fingerprint(
                options,
                engine_version=backend_version,
                model_version=model_version,
            ),
            engine_version=backend_version,
            model_version=model_version,
            warning_code=warning_code,
            warning_message=warning_message,
            error_code=error_code,
            error_message=error_message,
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        return self.transcription_repository.upsert(transcription, [])

    def get_transcription(self, video_id: str) -> TranscriptionReport:
        video = self._require_video(video_id)
        prepared_audio = self._load_prepared_audio(video.id)
        transcription = self._load_transcription(video.id)
        is_stale = self._transcription_is_stale(transcription, prepared_audio=prepared_audio)
        backend = self.engine.verify_backend()
        model_status = self.model_manager.get_model_status(transcription.model_name if transcription else "small") if transcription else None
        if transcription is None:
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=None,
                status=TranscriptionStatus.NOT_TRANSCRIBED,
                is_stale=False,
                backend=backend,
                model_status=model_status,
            )
        status = transcription.status
        if prepared_audio is None:
            status = TranscriptionStatus.AUDIO_NOT_PREPARED
        elif prepared_audio.status != PreparedAudioStatus.COMPLETED:
            if prepared_audio.status == PreparedAudioStatus.STALE:
                status = TranscriptionStatus.AUDIO_STALE
            else:
                status = TranscriptionStatus.AUDIO_NOT_PREPARED
        elif is_stale:
            status = TranscriptionStatus.STALE
        segments = self.transcription_repository.list_segments(transcription.id)
        return self._report(
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            segments=segments,
            status=status,
            is_stale=is_stale,
            backend=backend,
            model_status=model_status,
        )

    def transcribe_video(
        self,
        video_id: str,
        options: TranscriptionOptions,
        *,
        progress_callback=None,
    ) -> TranscriptionReport:
        validate_transcription_options(options)
        video = self._require_video(video_id)
        prepared_audio = self._load_prepared_audio(video.id)
        if prepared_audio is None:
            raise TranscriptionStateError("El audio preparado no existe para este video.")
        if prepared_audio.status == PreparedAudioStatus.FILE_MISSING:
            raise TranscriptionStateError("El audio preparado no esta disponible.")
        if prepared_audio.status != PreparedAudioStatus.COMPLETED:
            raise TranscriptionStateError("El audio preparado no esta listo para transcripcion.")
        existing = self._load_transcription(video.id)
        if existing and existing.status == TranscriptionStatus.COMPLETED and not self._transcription_is_stale(
            existing,
            prepared_audio=prepared_audio,
            options=options,
        ):
            return self.get_transcription(video.id)
        transcription_id = existing.id if existing else str(uuid4())
        with self._lock:
            if video.id in self._active_jobs:
                raise ConflictError("Ya existe una transcripcion en curso para este video.")
            cancellation_event = threading.Event()
            self._active_jobs[video.id] = cancellation_event
        backend = self.engine.verify_backend()
        model_name = normalize_model_name(options.model_name)
        model_status = self._inspect_model_availability(model_name)
        if model_status.status != TranscriptionModelStatus.INSTALLED:
            friendly_message = "El modelo no esta instalado. Usa Componentes locales para instalarlo."
            failed = self._persist_status(
                transcription_id=transcription_id,
                video=video,
                prepared_audio=prepared_audio,
                status=TranscriptionStatus.MODEL_UNAVAILABLE,
                options=options,
                error_code=model_status.error_code or "model_unavailable",
                error_message=friendly_message,
                backend_version=backend.faster_whisper_version,
                model_version=model_status.model_name,
            )
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=failed,
                status=TranscriptionStatus.MODEL_UNAVAILABLE,
                is_stale=False,
                backend=backend,
                model_status=model_status,
                warnings=(model_status.notes,) if model_status.notes else (),
                errors=(friendly_message,),
                progress_message=friendly_message,
            )
        if not backend.available and normalize_device(options.device) == "cuda":
            raise TranscriptionBackendError(backend.fallback_reason or "CUDA no disponible.")
        if progress_callback is not None:
            progress_callback("Preparando backend", 0.0)
        try:
            engine_version = backend.faster_whisper_version
            queued = self._persist_status(
                transcription_id=transcription_id,
                video=video,
                prepared_audio=prepared_audio,
                status=TranscriptionStatus.QUEUED,
                options=options,
                backend_version=engine_version,
                model_version=model_status.model_name,
            )
            if progress_callback is not None:
                progress_callback("Cargando modelo", 0.1)
            loading = replace(queued, status=TranscriptionStatus.LOADING_MODEL, updated_at=utc_now())
            self.transcription_repository.upsert(loading, [])
            if progress_callback is not None:
                progress_callback("Transcribiendo", 0.2)
            if prepared_audio.relative_cache_path is None:
                raise TranscriptionStateError("El audio preparado no tiene ruta de caché.")
            audio_path = self.paths.project_root / "cache" / prepared_audio.relative_cache_path
            result = self.engine.transcribe(
                video_asset_id=video.id,
                prepared_audio_asset_id=prepared_audio.id,
                audio_path=audio_path,
                audio_size_bytes=prepared_audio.file_size_bytes,
                audio_modified_at=prepared_audio.source_file_modified_at.isoformat() if prepared_audio.source_file_modified_at else None,
                options=options,
                cancellation_token=TranscriptionCancellationToken(is_cancelled=cancellation_event.is_set),
                progress_callback=progress_callback,
            )
            transcription, segments = self._build_transcription_entity(
                transcription_id=queued.id,
                video=video,
                prepared_audio=prepared_audio,
                result=result,
                options=options,
            )
            persisted = self.transcription_repository.upsert(transcription, segments)
            if progress_callback is not None:
                progress_callback("Guardando resultado", 0.95)
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=persisted,
                segments=segments,
                status=TranscriptionStatus.COMPLETED,
                is_stale=False,
                backend=backend,
                model_status=model_status,
                warnings=result.warnings,
                errors=result.errors,
                progress_message="Completado",
            )
        except TranscriptionBackendError as exc:
            status = TranscriptionStatus.CANCELLED if cancellation_event.is_set() else TranscriptionStatus.BACKEND_UNAVAILABLE
            error_code = "cancelled" if status == TranscriptionStatus.CANCELLED else "backend_unavailable"
            failed = self._persist_status(
                transcription_id=transcription_id,
                video=video,
                prepared_audio=prepared_audio,
                status=status,
                options=options,
                error_code=error_code,
                error_message=str(exc),
                backend_version=backend.faster_whisper_version,
                model_version=model_status.model_name,
            )
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=failed,
                status=status,
                is_stale=False,
                backend=backend,
                model_status=model_status,
                errors=(str(exc),),
            )
        except FileNotFoundError as exc:
            failed = self._persist_status(
                transcription_id=transcription_id,
                video=video,
                prepared_audio=prepared_audio,
                status=TranscriptionStatus.FILE_MISSING,
                options=options,
                error_code="file_missing",
                error_message=str(exc),
                backend_version=backend.faster_whisper_version,
                model_version=model_status.model_name,
            )
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=failed,
                status=TranscriptionStatus.FILE_MISSING,
                is_stale=False,
                backend=backend,
                model_status=model_status,
                errors=(str(exc),),
            )
        except Exception as exc:
            status = TranscriptionStatus.CANCELLED if cancellation_event.is_set() else TranscriptionStatus.FAILED
            failed = self._persist_status(
                transcription_id=transcription_id,
                video=video,
                prepared_audio=prepared_audio,
                status=status,
                options=options,
                error_code="cancelled" if status == TranscriptionStatus.CANCELLED else "transcription_failed",
                error_message=str(exc),
                backend_version=backend.faster_whisper_version,
                model_version=model_status.model_name,
            )
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=failed,
                status=status,
                is_stale=False,
                backend=backend,
                model_status=model_status,
                errors=(str(exc),),
            )
        finally:
            with self._lock:
                self._active_jobs.pop(video.id, None)
            self.engine.release_model()

    def export_transcription(
        self,
        video_id: str,
        format: TranscriptionExportFormat,
        *,
        destination: Path | None = None,
    ) -> TranscriptionExportResult:
        report = self.get_transcription(video_id)
        if report.transcription is None:
            raise NotFoundError("No existe una transcripcion para exportar.")
        transcription = report.transcription
        segments = list(report.segments)
        if format == TranscriptionExportFormat.TXT:
            content = export_txt(transcription, segments)
            suffix = ".txt"
        elif format == TranscriptionExportFormat.SRT:
            content = export_srt(transcription, segments)
            suffix = ".srt"
        elif format == TranscriptionExportFormat.JSON:
            content = export_json(transcription, segments)
            suffix = ".json"
        else:
            raise TranscriptionValidationError(f"Formato de exportacion no soportado: {format}")
        target = destination or (self._controlled_export_root(video_id) / f"transcription{suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return TranscriptionExportResult(
            video=report.video,
            transcription=transcription,
            format=format,
            content=content,
            path=str(target),
        )


def build_transcription_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    video_repository: VideoRepository,
    prepared_audio_repository: SQLitePreparedAudioRepository,
    transcription_repository: TranscriptionRepository,
    logger: logging.Logger | None = None,
) -> TranscriptionService:
    """Construye el servicio formal de transcripcion."""

    model_manager = TranscriptionModelManager(paths.models_directory)
    engine = FasterWhisperEngine(model_manager=model_manager, logger=logger)
    return TranscriptionService(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        prepared_audio_repository=prepared_audio_repository,
        transcription_repository=transcription_repository,
        model_manager=model_manager,
        engine=engine,
        logger=logger,
    )
