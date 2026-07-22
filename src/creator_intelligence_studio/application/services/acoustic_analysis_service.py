"""Servicio de aplicacion para analisis acustico local."""

from __future__ import annotations

import csv
import io
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.acoustic_analysis.entities import (
    AcousticAnalysis,
    AcousticAnalysisStatus,
    AcousticEvent,
    AcousticTimelineWindow,
)
from creator_intelligence_studio.domain.acoustic_analysis.errors import AcousticAnalysisStateError, AcousticAnalysisValidationError
from creator_intelligence_studio.domain.acoustic_analysis.repositories import AcousticAnalysisRepository
from creator_intelligence_studio.domain.acoustic_analysis.services import (
    build_acoustic_configuration_fingerprint,
    build_acoustic_source_fingerprint,
    is_acoustic_analysis_stale,
    normalize_acoustic_analysis_config,
    validate_acoustic_analysis_options,
)
from creator_intelligence_studio.domain.acoustic_analysis.value_objects import (
    AcousticAnalysisOptions,
    AcousticEventData,
    AcousticTimelineWindowData,
)
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.errors import ConflictError, NotFoundError
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionStatus
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.acoustic_analysis.frame_analyzer import analyze_frames
from creator_intelligence_studio.infrastructure.acoustic_analysis.metrics import (
    PauseSummary,
    aggregate_windows,
    compute_global_metrics,
    detect_events,
    summarize_pauses,
)
from creator_intelligence_studio.infrastructure.acoustic_analysis.voice_activity_detector import detect_voice_activity
from creator_intelligence_studio.infrastructure.acoustic_analysis.wav_reader import read_wav_audio
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class AcousticAnalysisReport:
    """Estado y resultado de un analisis acustico."""

    video: VideoAsset
    prepared_audio: PreparedAudioAsset | None
    transcription: Transcription | None
    analysis: AcousticAnalysis | None
    windows: tuple[AcousticTimelineWindow, ...]
    events: tuple[AcousticEvent, ...]
    status: AcousticAnalysisStatus
    is_stale: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "prepared_audio": self.prepared_audio.to_dict() if self.prepared_audio else None,
            "transcription": self.transcription.to_dict() if self.transcription else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "windows": [window.to_dict() for window in self.windows],
            "events": [event.to_dict() for event in self.events],
            "status": self.status.value,
            "is_stale": self.is_stale,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class AcousticAnalysisExportResult:
    """Resultado de exportacion del analisis acustico."""

    video: VideoAsset
    analysis: AcousticAnalysis
    format: str
    content: str
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "analysis": self.analysis.to_dict(),
            "format": self.format,
            "content": self.content,
            "path": self.path,
        }


class AcousticAnalysisService:
    """Coordina analisis determinista, persistencia y exportacion."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        video_repository: VideoRepository,
        prepared_audio_repository: SQLitePreparedAudioRepository,
        transcription_repository: SQLiteTranscriptionRepository,
        acoustic_repository: AcousticAnalysisRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.video_repository = video_repository
        self.prepared_audio_repository = prepared_audio_repository
        self.transcription_repository = transcription_repository
        self.acoustic_repository = acoustic_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.acoustic")
        self.options = normalize_acoustic_analysis_config(AcousticAnalysisOptions())
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

    def _load_analysis(self, video_id: str) -> AcousticAnalysis | None:
        return self.acoustic_repository.get_by_video_asset_id(video_id)

    def _prepared_audio_exists(self, prepared_audio: PreparedAudioAsset) -> bool:
        if prepared_audio.relative_cache_path is None:
            return False
        return (self.paths.project_root / "cache" / prepared_audio.relative_cache_path).exists()

    def _prepared_audio_snapshot(self, prepared_audio: PreparedAudioAsset) -> tuple[int | None, str | None]:
        if prepared_audio.relative_cache_path is None:
            return None, None
        path = self.paths.project_root / "cache" / prepared_audio.relative_cache_path
        if not path.exists():
            return None, None
        stat = path.stat()
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        return stat.st_size, modified_at

    def _audio_path(self, prepared_audio: PreparedAudioAsset) -> Path:
        if prepared_audio.relative_cache_path is None:
            raise AcousticAnalysisStateError("El audio preparado no tiene una ruta de caché.")
        return self.paths.project_root / "cache" / prepared_audio.relative_cache_path

    def _report(
        self,
        *,
        video: VideoAsset,
        prepared_audio: PreparedAudioAsset | None,
        transcription: Transcription | None,
        analysis: AcousticAnalysis | None,
        windows: list[AcousticTimelineWindow] | None = None,
        events: list[AcousticEvent] | None = None,
        status: AcousticAnalysisStatus | None = None,
        is_stale: bool = False,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
        progress_message: str | None = None,
    ) -> AcousticAnalysisReport:
        if analysis is not None:
            if windows is None:
                windows = self.acoustic_repository.list_windows(analysis.id)
            if events is None:
                events = self.acoustic_repository.list_events(analysis.id)
        resolved_status = status or (analysis.status if analysis else AcousticAnalysisStatus.NOT_ANALYZED)
        return AcousticAnalysisReport(
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            analysis=analysis,
            windows=tuple(windows or ()),
            events=tuple(events or ()),
            status=resolved_status,
            is_stale=is_stale,
            warnings=warnings,
            errors=errors,
            progress_message=progress_message,
        )

    def _build_analysis_entity(
        self,
        *,
        analysis_id: str,
        video: VideoAsset,
        prepared_audio: PreparedAudioAsset,
        transcription: Transcription | None,
        audio_file_snapshot: tuple[int | None, str | None],
        windows: list[AcousticTimelineWindowData],
        events: list[AcousticEventData],
        total_duration_seconds: float,
        pause_summary: PauseSummary,
        metrics: dict[str, float | None],
        started_at: datetime,
        completed_at: datetime,
    ) -> tuple[AcousticAnalysis, list[AcousticTimelineWindow], list[AcousticEvent]]:
        source_fingerprint = build_acoustic_source_fingerprint(
            prepared_audio=prepared_audio,
            transcription=transcription,
            audio_file_size_bytes=audio_file_snapshot[0],
            audio_file_modified_at=audio_file_snapshot[1],
        )
        configuration_fingerprint = build_acoustic_configuration_fingerprint(self.options, transcription=transcription)
        analysis = AcousticAnalysis(
            id=analysis_id,
            video_asset_id=video.id,
            prepared_audio_asset_id=prepared_audio.id,
            transcription_id=transcription.id if transcription else None,
            status=AcousticAnalysisStatus.COMPLETED,
            analyzer_version=self.options.analyzer_version,
            configuration_fingerprint=configuration_fingerprint,
            source_audio_fingerprint=source_fingerprint,
            duration_seconds=total_duration_seconds,
            speech_duration_seconds=float(metrics["speech_duration_seconds"] or 0.0),
            silence_duration_seconds=float(metrics["silence_duration_seconds"] or 0.0),
            speech_ratio=float(metrics["speech_ratio"] or 0.0),
            silence_ratio=float(metrics["silence_ratio"] or 0.0),
            words_per_minute=metrics["words_per_minute"],
            voiced_words_per_minute=metrics["voiced_words_per_minute"],
            average_energy=float(metrics["average_energy"] or 0.0),
            peak_energy=float(metrics["peak_energy"] or 0.0),
            dynamic_range=float(metrics["dynamic_range"] or 0.0),
            pause_count=pause_summary.pause_count,
            average_pause_seconds=pause_summary.average_pause_seconds,
            longest_pause_seconds=pause_summary.longest_pause_seconds,
            short_pause_count=pause_summary.short_pause_count,
            medium_pause_count=pause_summary.medium_pause_count,
            long_pause_count=pause_summary.long_pause_count,
            low_activity_segment_count=sum(1 for window in windows if window.activity_label.value == "low_activity"),
            abrupt_change_count=sum(1 for event in events if event.event_type.value == "abrupt_energy_change"),
            event_candidate_count=len(events),
            started_at=started_at,
            completed_at=completed_at,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=started_at,
            updated_at=completed_at,
        )
        persisted_windows: list[AcousticTimelineWindow] = []
        window_created_at = completed_at
        for window in windows:
            persisted_windows.append(
                AcousticTimelineWindow(
                    id=str(uuid4()),
                    acoustic_analysis_id=analysis_id,
                    window_index=window.window_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    speech_probability=window.speech_probability,
                    is_speech=window.is_speech,
                    rms_energy=window.rms_energy,
                    peak_amplitude=window.peak_amplitude,
                    normalized_energy=window.normalized_energy,
                    zero_crossing_rate=window.zero_crossing_rate,
                    speech_rate_estimate=window.speech_rate_estimate,
                    word_count=window.word_count,
                    pause_duration_seconds=window.pause_duration_seconds,
                    activity_label=window.activity_label,
                    created_at=window_created_at,
                )
            )
        persisted_events: list[AcousticEvent] = []
        for event in events:
            persisted_events.append(
                AcousticEvent(
                    id=str(uuid4()),
                    acoustic_analysis_id=analysis_id,
                    event_index=event.event_index,
                    start_seconds=event.start_seconds,
                    end_seconds=event.end_seconds,
                    event_type=event.event_type,
                    confidence=event.confidence,
                    evidence_json=json.dumps(event.evidence, ensure_ascii=False, separators=(",", ":")),
                    created_at=completed_at,
                )
            )
        return analysis, persisted_windows, persisted_events

    def _analysis_is_stale(
        self,
        analysis: AcousticAnalysis | None,
        *,
        prepared_audio: PreparedAudioAsset | None,
        transcription: Transcription | None,
        audio_file_snapshot: tuple[int | None, str | None] | None,
    ) -> bool:
        if analysis is None:
            return False
        if prepared_audio is None or prepared_audio.status != PreparedAudioStatus.COMPLETED:
            return True
        if not self._prepared_audio_exists(prepared_audio):
            return True
        if transcription is not None and transcription.status != TranscriptionStatus.COMPLETED:
            return True
        return is_acoustic_analysis_stale(
            analysis,
            prepared_audio=prepared_audio,
            transcription=transcription,
            options=self.options,
            audio_file_size_bytes=audio_file_snapshot[0] if audio_file_snapshot else None,
            audio_file_modified_at=audio_file_snapshot[1] if audio_file_snapshot else None,
        )

    def analyze_acoustics(
        self,
        video_id: str,
        force: bool = False,
        *,
        progress_callback=None,
    ) -> AcousticAnalysisReport:
        video = self._require_video(video_id)
        prepared_audio = self._load_prepared_audio(video.id)
        transcription = self._load_transcription(video.id)
        existing = self._load_analysis(video.id)
        audio_file_snapshot = self._prepared_audio_snapshot(prepared_audio) if prepared_audio else None
        if existing and not force and not self._analysis_is_stale(
            existing,
            prepared_audio=prepared_audio,
            transcription=transcription,
            audio_file_snapshot=audio_file_snapshot,
        ):
            return self.get_acoustic_analysis(video.id)

        if prepared_audio is None:
            return self._persist_failure(
                video=video,
                prepared_audio=None,
                transcription=transcription,
                status=AcousticAnalysisStatus.AUDIO_NOT_PREPARED,
                error_code="audio_not_prepared",
                error_message="No existe audio preparado para este video.",
            )
        if prepared_audio.status == PreparedAudioStatus.FILE_MISSING:
            return self._persist_failure(
                video=video,
                prepared_audio=prepared_audio,
                transcription=transcription,
                status=AcousticAnalysisStatus.FILE_MISSING,
                error_code="file_missing",
                error_message="El audio preparado no esta disponible.",
            )
        if prepared_audio.status != PreparedAudioStatus.COMPLETED:
            if prepared_audio.status == PreparedAudioStatus.STALE:
                return self._persist_failure(
                    video=video,
                    prepared_audio=prepared_audio,
                    transcription=transcription,
                    status=AcousticAnalysisStatus.AUDIO_STALE,
                    error_code="audio_stale",
                    error_message="El audio preparado esta desactualizado.",
                )
            return self._persist_failure(
                video=video,
                prepared_audio=prepared_audio,
                transcription=transcription,
                status=AcousticAnalysisStatus.AUDIO_NOT_PREPARED,
                error_code="audio_not_prepared",
                error_message="El audio preparado no esta listo para analisis.",
            )
        if not self._prepared_audio_exists(prepared_audio):
            return self._persist_failure(
                video=video,
                prepared_audio=prepared_audio,
                transcription=transcription,
                status=AcousticAnalysisStatus.FILE_MISSING,
                error_code="file_missing",
                error_message="El WAV preparado no existe o no esta disponible.",
            )
        if existing and not force and self._analysis_is_stale(
            existing,
            prepared_audio=prepared_audio,
            transcription=transcription,
            audio_file_snapshot=audio_file_snapshot,
        ):
            return self.get_acoustic_analysis(video.id)

        if progress_callback is not None:
            progress_callback("Leyendo audio", 0.05)
        audio_path = self._audio_path(prepared_audio)
        try:
            wav_audio = read_wav_audio(audio_path)
        except Exception as exc:
            return self._persist_failure(
                video=video,
                prepared_audio=prepared_audio,
                transcription=transcription,
                status=AcousticAnalysisStatus.FILE_MISSING,
                error_code="file_missing",
                error_message=str(exc),
                warnings=(str(exc),),
            )

        started_at = utc_now()
        if progress_callback is not None:
            progress_callback("Analizando frames", 0.2)
        frames = analyze_frames(
            wav_audio.samples,
            sample_rate_hz=wav_audio.sample_rate_hz,
            frame_duration_ms=self.options.frame_duration_ms,
            hop_duration_ms=self.options.frame_hop_ms,
        )
        transcript_segments = list(self.transcription_repository.list_segments(transcription.id)) if transcription else []
        transcript_windows = [(segment.start_seconds, segment.end_seconds) for segment in transcript_segments]
        activity = detect_voice_activity(
            frames,
            transcript_windows=transcript_windows,
            minimum_speech_seconds=self.options.minimum_speech_seconds,
            speech_energy_multiplier=self.options.speech_energy_multiplier,
            silence_energy_multiplier=self.options.silence_energy_multiplier,
        )
        if progress_callback is not None:
            progress_callback("Combinando transcripcion", 0.5)
        windows = aggregate_windows(
            frames,
            activity,
            sample_rate_hz=wav_audio.sample_rate_hz,
            total_duration_seconds=wav_audio.duration_seconds,
            window_duration_seconds=self.options.window_duration_seconds,
            rhythm_window_seconds=self.options.rhythm_window_seconds,
            transcript_segments=transcript_segments,
        )
        pause_summary = summarize_pauses(
            windows,
            pause_micro_max_seconds=self.options.pause_micro_max_seconds,
            pause_short_max_seconds=self.options.pause_short_max_seconds,
            pause_medium_max_seconds=self.options.pause_medium_max_seconds,
        )
        if progress_callback is not None:
            progress_callback("Detectando pausas y eventos", 0.75)
        events = detect_events(windows, pause_summary=pause_summary, transcript_segments=transcript_segments)
        metrics = compute_global_metrics(
            windows,
            total_duration_seconds=wav_audio.duration_seconds,
            pause_summary=pause_summary,
            transcript_segments=transcript_segments,
        )
        if progress_callback is not None:
            progress_callback("Guardando resultados", 0.9)
        completed_at = utc_now()
        analysis_id = existing.id if existing else str(uuid4())
        analysis, persisted_windows, persisted_events = self._build_analysis_entity(
            analysis_id=analysis_id,
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            audio_file_snapshot=audio_file_snapshot or self._prepared_audio_snapshot(prepared_audio),
            windows=windows,
            events=events,
            total_duration_seconds=wav_audio.duration_seconds,
            pause_summary=pause_summary,
            metrics=metrics,
            started_at=started_at,
            completed_at=completed_at,
        )
        persisted = self.acoustic_repository.upsert(analysis, persisted_windows, persisted_events)
        if progress_callback is not None:
            progress_callback("Completado", 1.0)
        return self._report(
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            analysis=persisted,
            windows=self.acoustic_repository.list_windows(persisted.id),
            events=self.acoustic_repository.list_events(persisted.id),
            status=AcousticAnalysisStatus.COMPLETED,
            is_stale=False,
            progress_message="Completado",
        )

    def _persist_failure(
        self,
        *,
        video: VideoAsset,
        prepared_audio: PreparedAudioAsset | None,
        transcription: Transcription | None,
        status: AcousticAnalysisStatus,
        error_code: str,
        error_message: str,
        warnings: tuple[str, ...] = (),
    ) -> AcousticAnalysisReport:
        now = utc_now()
        existing = self._load_analysis(video.id)
        audio_file_snapshot = self._prepared_audio_snapshot(prepared_audio) if prepared_audio else None
        analysis = AcousticAnalysis(
            id=existing.id if existing else str(uuid4()),
            video_asset_id=video.id,
            prepared_audio_asset_id=prepared_audio.id if prepared_audio else None,
            transcription_id=transcription.id if transcription else None,
            status=status,
            analyzer_version=self.options.analyzer_version,
            configuration_fingerprint=build_acoustic_configuration_fingerprint(self.options, transcription=transcription),
            source_audio_fingerprint=build_acoustic_source_fingerprint(
                prepared_audio=prepared_audio,
                transcription=transcription,
                audio_file_size_bytes=audio_file_snapshot[0] if audio_file_snapshot else None,
                audio_file_modified_at=audio_file_snapshot[1] if audio_file_snapshot else None,
            )
            if prepared_audio
            else "",
            duration_seconds=0.0,
            speech_duration_seconds=0.0,
            silence_duration_seconds=0.0,
            speech_ratio=0.0,
            silence_ratio=0.0,
            words_per_minute=None,
            voiced_words_per_minute=None,
            average_energy=0.0,
            peak_energy=0.0,
            dynamic_range=0.0,
            pause_count=0,
            average_pause_seconds=None,
            longest_pause_seconds=None,
            short_pause_count=0,
            medium_pause_count=0,
            long_pause_count=0,
            low_activity_segment_count=0,
            abrupt_change_count=0,
            event_candidate_count=0,
            started_at=now,
            completed_at=now,
            warning_code=None,
            warning_message=None,
            error_code=error_code,
            error_message=error_message,
            created_at=now,
            updated_at=now,
        )
        persisted = self.acoustic_repository.upsert(analysis, [], [])
        return self._report(
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            analysis=persisted,
            status=status,
            is_stale=False,
            warnings=warnings,
            errors=(error_message,),
        )

    def _placeholder_audio(self, video_id: str) -> PreparedAudioAsset:
        return PreparedAudioAsset(
            id="",
            video_asset_id=video_id,
            source_inspection_id=None,
            status=PreparedAudioStatus.NOT_PREPARED,
            relative_cache_path=None,
            metadata_relative_path=None,
            format_name=None,
            codec_name=None,
            sample_rate_hz=None,
            channels=None,
            channel_layout=None,
            bit_depth=None,
            duration_seconds=None,
            file_size_bytes=None,
            source_file_size_bytes=None,
            source_file_modified_at=None,
            selected_stream_index=None,
            selected_stream_codec_name=None,
            selected_stream_channels=None,
            selected_stream_channel_layout=None,
            selected_stream_sample_rate_hz=None,
            selected_stream_language=None,
            selected_stream_is_default=None,
            extraction_started_at=None,
            extraction_completed_at=None,
            ffmpeg_version=None,
            cache_version=self.settings.audio_cache_version,
            normalization_sample_rate_hz=self.settings.audio_normalization_sample_rate_hz,
            normalization_channels=1,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

    def get_acoustic_analysis(self, video_id: str) -> AcousticAnalysisReport:
        video = self._require_video(video_id)
        prepared_audio = self._load_prepared_audio(video.id)
        transcription = self._load_transcription(video.id)
        analysis = self._load_analysis(video.id)
        audio_file_snapshot = self._prepared_audio_snapshot(prepared_audio) if prepared_audio else None
        is_stale = self._analysis_is_stale(
            analysis,
            prepared_audio=prepared_audio,
            transcription=transcription,
            audio_file_snapshot=audio_file_snapshot,
        )
        if analysis is None:
            return self._report(
                video=video,
                prepared_audio=prepared_audio,
                transcription=transcription,
                analysis=None,
                status=AcousticAnalysisStatus.NOT_ANALYZED,
                is_stale=False,
            )
        status = analysis.status
        if prepared_audio is None:
            status = AcousticAnalysisStatus.AUDIO_NOT_PREPARED
        elif not self._prepared_audio_exists(prepared_audio):
            status = AcousticAnalysisStatus.FILE_MISSING
        elif prepared_audio.status == PreparedAudioStatus.FILE_MISSING:
            status = AcousticAnalysisStatus.FILE_MISSING
        elif prepared_audio.status == PreparedAudioStatus.STALE:
            status = AcousticAnalysisStatus.AUDIO_STALE
        elif prepared_audio.status != PreparedAudioStatus.COMPLETED:
            status = AcousticAnalysisStatus.AUDIO_NOT_PREPARED
        elif is_stale:
            status = AcousticAnalysisStatus.STALE
        windows = self.acoustic_repository.list_windows(analysis.id)
        events = self.acoustic_repository.list_events(analysis.id)
        return self._report(
            video=video,
            prepared_audio=prepared_audio,
            transcription=transcription,
            analysis=analysis,
            windows=windows,
            events=events,
            status=status,
            is_stale=is_stale,
        )

    def get_acoustic_timeline(self, video_id: str) -> list[AcousticTimelineWindow]:
        report = self.get_acoustic_analysis(video_id)
        return list(report.windows)

    def list_acoustic_events(self, video_id: str) -> list[AcousticEvent]:
        report = self.get_acoustic_analysis(video_id)
        return list(report.events)

    def is_acoustic_analysis_stale(self, video_id: str) -> bool:
        report = self.get_acoustic_analysis(video_id)
        return report.is_stale

    def delete_acoustic_analysis(self, video_id: str) -> bool:
        return self.acoustic_repository.delete_by_video_asset_id(video_id)

    def export_acoustic_analysis(
        self,
        video_id: str,
        format: str,
        *,
        destination: Path | None = None,
    ) -> AcousticAnalysisExportResult:
        report = self.get_acoustic_analysis(video_id)
        if report.analysis is None:
            raise NotFoundError("No existe un analisis acustico para exportar.")
        analysis = report.analysis
        windows = list(report.windows)
        events = list(report.events)
        format_name = format.lower().strip()
        if format_name == "json":
            content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
            suffix = ".json"
        elif format_name == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "window_index",
                "start_seconds",
                "end_seconds",
                "speech_probability",
                "is_speech",
                "rms_energy",
                "peak_amplitude",
                "normalized_energy",
                "zero_crossing_rate",
                "speech_rate_estimate",
                "word_count",
                "pause_duration_seconds",
                "activity_label",
            ])
            for window in windows:
                writer.writerow([
                    window.window_index,
                    window.start_seconds,
                    window.end_seconds,
                    window.speech_probability,
                    int(window.is_speech),
                    window.rms_energy,
                    window.peak_amplitude,
                    window.normalized_energy,
                    window.zero_crossing_rate,
                    window.speech_rate_estimate,
                    window.word_count,
                    window.pause_duration_seconds,
                    window.activity_label.value,
                ])
            content = output.getvalue()
            suffix = ".csv"
        elif format_name == "txt":
            lines = [
                f"Video: {video_id}",
                f"Estado: {analysis.status.value}",
                f"Duracion: {analysis.duration_seconds:.3f} s",
                f"Voz: {analysis.speech_duration_seconds:.3f} s",
                f"Silencio: {analysis.silence_duration_seconds:.3f} s",
                f"Speech ratio: {analysis.speech_ratio:.3f}",
                f"Palabras por minuto: {analysis.words_per_minute if analysis.words_per_minute is not None else 'No verificado'}",
                f"Pausas: {analysis.pause_count}",
                f"Pausa mas larga: {analysis.longest_pause_seconds if analysis.longest_pause_seconds is not None else 'No verificada'}",
                f"Energia media: {analysis.average_energy:.6f}",
                f"Rango dinamico: {analysis.dynamic_range:.6f}",
                f"Cambios bruscos: {analysis.abrupt_change_count}",
                f"Eventos candidatos: {analysis.event_candidate_count}",
                "",
                "Eventos:",
            ]
            for event in events:
                lines.append(
                    f"[{event.event_index}] {event.event_type.value} {event.start_seconds:.3f}-{event.end_seconds:.3f} conf={event.confidence:.3f}"
                )
            content = "\n".join(lines) + "\n"
            suffix = ".txt"
        else:
            raise AcousticAnalysisValidationError(f"Formato de exportacion no soportado: {format}")
        target = destination or (self.paths.project_root / "cache" / "acoustics" / video_id / f"acoustic_analysis{suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return AcousticAnalysisExportResult(
            video=report.video,
            analysis=analysis,
            format=format_name,
            content=content,
            path=str(target),
        )


def build_acoustic_analysis_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    video_repository: VideoRepository,
    prepared_audio_repository: SQLitePreparedAudioRepository,
    transcription_repository: SQLiteTranscriptionRepository,
    acoustic_repository: AcousticAnalysisRepository,
    logger: logging.Logger | None = None,
) -> AcousticAnalysisService:
    return AcousticAnalysisService(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        prepared_audio_repository=prepared_audio_repository,
        transcription_repository=transcription_repository,
        acoustic_repository=acoustic_repository,
        logger=logger,
    )
