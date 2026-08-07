"""Servicio de aplicacion para preparacion tecnica de audio."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4, UUID

from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.audio.errors import (
    AudioPreparationError,
    AudioStateError,
    AudioToolUnavailableError,
    AudioValidationError,
)
from creator_intelligence_studio.domain.audio.repositories import PreparedAudioRepository
from creator_intelligence_studio.domain.audio.services import (
    AudioPreparationConfig,
    build_audio_candidates,
    select_audio_stream,
    validate_audio_preparation_config,
)
from creator_intelligence_studio.domain.audio.value_objects import AudioStreamCandidate
from creator_intelligence_studio.domain.errors import NotFoundError
from creator_intelligence_studio.domain.media.entities import VideoInspectionStatus
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.audio.ffmpeg_audio_extractor import (
    FFmpegAudioExtractionError,
    FFmpegAudioExtractor,
)
from creator_intelligence_studio.infrastructure.audio.wav_inspector import (
    WavInspectionError,
    WavInspectionResult,
    inspect_wav_file,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.media.parsers import parse_ffprobe_streams
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths

from .media_inspection_service import MediaInspectionService, VideoInspectionReport


AUDIO_CACHE_SUBDIR = "audio"


@dataclass(frozen=True, slots=True)
class PreparedAudioReport:
    """Resultado de la preparacion tecnica de audio."""

    video: VideoAsset
    status: PreparedAudioStatus
    is_stale: bool
    prepared_audio: PreparedAudioAsset | None
    selected_stream: AudioStreamCandidate | None
    wav_validation: WavInspectionResult | None
    cache_path: str | None
    metadata_path: str | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "status": self.status.value,
            "is_stale": self.is_stale,
            "prepared_audio": self.prepared_audio.to_dict() if self.prepared_audio else None,
            "selected_stream": self.selected_stream.to_dict() if self.selected_stream else None,
            "wav_validation": self.wav_validation.to_dict() if self.wav_validation else None,
            "cache_path": self.cache_path,
            "metadata_path": self.metadata_path,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class AudioCacheDeletionResult:
    """Resultado de la limpieza de caché de audio."""

    video_id: str
    deleted_record: bool
    deleted_files: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "video_id": self.video_id,
            "deleted_record": self.deleted_record,
            "deleted_files": list(self.deleted_files),
        }


def _snapshot_file(video: VideoAsset) -> tuple[bool, int | None, datetime | None]:
    path = Path(video.source_path)
    if not path.exists() or not path.is_file():
        return False, None, None
    stat = path.stat()
    return True, stat.st_size, datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _utc_now() -> datetime:
    return utc_now()


def _build_audio_dir(cache_root: Path, video_id: str) -> Path:
    return cache_root / "videos" / str(UUID(video_id)) / AUDIO_CACHE_SUBDIR


def _build_audio_paths(cache_root: Path, video_id: str, cache_version: str) -> tuple[Path, Path]:
    audio_dir = _build_audio_dir(cache_root, video_id)
    return audio_dir / f"normalized_{cache_version}.wav", audio_dir / "metadata.json"


def _safe_delete(path: Path, *, root: Path) -> bool:
    try:
        resolved_root = root.resolve()
        resolved_path = path.resolve()
        if not resolved_path.is_relative_to(resolved_root):
            return False
    except FileNotFoundError:
        pass
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
        return True
    path.unlink()
    return True


def _read_inspection_report(media_service: MediaInspectionService, video_id: str) -> VideoInspectionReport | None:
    return media_service.get_video_inspection(video_id)


def _build_stream_from_asset(asset: PreparedAudioAsset) -> AudioStreamCandidate | None:
    if asset.selected_stream_index is None:
        return None
    return AudioStreamCandidate(
        index=asset.selected_stream_index,
        codec_name=asset.selected_stream_codec_name,
        codec_long_name=None,
        channels=asset.selected_stream_channels,
        channel_layout=asset.selected_stream_channel_layout,
        sample_rate_hz=asset.selected_stream_sample_rate_hz,
        language=asset.selected_stream_language,
        is_default=bool(asset.selected_stream_is_default) if asset.selected_stream_is_default is not None else False,
        tags={},
    )


def _build_metadata_payload(
    *,
    video: VideoAsset,
    inspection: VideoInspectionReport | None,
    config: AudioPreparationConfig,
    selected_stream: AudioStreamCandidate | None,
    wav_validation: WavInspectionResult | None,
) -> dict[str, object]:
    return {
        "video_id": video.id,
        "source_inspection_id": inspection.inspection.id if inspection and inspection.inspection else None,
        "source_inspection_status": inspection.status.value if inspection else None,
        "source_inspection_stale": inspection.is_stale if inspection else None,
        "configuration": config.to_dict(),
        "selected_stream": selected_stream.to_dict() if selected_stream else None,
        "wav_validation": wav_validation.to_dict() if wav_validation else None,
        "generated_at": _utc_now().isoformat(),
    }


def _wav_matches_expected(result: WavInspectionResult, config: AudioPreparationConfig) -> bool:
    return (
        result.valid
        and result.format_name == "wav"
        and result.codec_name == "pcm_s16le"
        and result.sample_rate_hz == config.sample_rate_hz
        and result.channels == config.channels
        and result.bit_depth == config.bit_depth
    )


class AudioPreparationService:
    """Coordina la preparacion tecnica de audio reutilizable."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        video_repository: VideoRepository,
        inspection_service: MediaInspectionService,
        audio_repository: PreparedAudioRepository,
        logger: logging.Logger | None = None,
        tool_locator: MediaToolLocator | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.video_repository = video_repository
        self.inspection_service = inspection_service
        self.audio_repository = audio_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.audio")
        self.tool_locator = tool_locator or MediaToolLocator(
            settings=settings,
            project_root=paths.project_root,
        )
        self.config = AudioPreparationConfig(
            sample_rate_hz=settings.audio_normalization_sample_rate_hz,
            channels=1,
            bit_depth=16,
            cache_version=settings.audio_cache_version,
            preferred_language=settings.preferred_audio_language,
        )
        validate_audio_preparation_config(self.config)

    @property
    def cache_root(self) -> Path:
        return self.paths.project_root / "cache"

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _load_audio(self, video_id: str) -> PreparedAudioAsset | None:
        return self.audio_repository.get_by_video_asset_id(video_id)

    def _inspection_report(self, video_id: str) -> VideoInspectionReport | None:
        return _read_inspection_report(self.inspection_service, video_id)

    def _source_snapshot(self, video: VideoAsset) -> tuple[bool, int | None, datetime | None]:
        return _snapshot_file(video)

    def _is_asset_stale(
        self,
        *,
        asset: PreparedAudioAsset,
        inspection_report: VideoInspectionReport | None,
        snapshot: tuple[bool, int | None, datetime | None],
    ) -> bool:
        exists, size_bytes, modified_at = snapshot
        if not exists:
            return True
        if asset.source_file_size_bytes != size_bytes or asset.source_file_modified_at != modified_at:
            return True
        if inspection_report is None or inspection_report.inspection is None or inspection_report.is_stale:
            return True
        if asset.source_inspection_id != inspection_report.inspection.id:
            return True
        if asset.cache_version != self.config.cache_version:
            return True
        if asset.normalization_sample_rate_hz != self.config.sample_rate_hz:
            return True
        if asset.normalization_channels != self.config.channels:
            return True
        return False

    def _report_from_state(
        self,
        *,
        video: VideoAsset,
        asset: PreparedAudioAsset | None,
        inspection_report: VideoInspectionReport | None,
        snapshot: tuple[bool, int | None, datetime | None],
        selected_stream: AudioStreamCandidate | None = None,
        wav_validation: WavInspectionResult | None = None,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> PreparedAudioReport:
        exists, size_bytes, modified_at = snapshot
        status = PreparedAudioStatus.NOT_PREPARED
        is_stale = False
        cache_path = None
        metadata_path = None

        if asset is not None:
            cache_path, metadata_path = _build_audio_paths(self.cache_root, video.id, asset.cache_version)
            cache_path_text = str(cache_path)
            metadata_path_text = str(metadata_path)
            cache_path = cache_path_text
            metadata_path = metadata_path_text
            cache_path_obj = Path(cache_path_text)
            metadata_path_obj = Path(metadata_path_text)
            cache_missing = not cache_path_obj.exists() or not metadata_path_obj.exists()
            if cache_missing:
                if asset.status in {
                    PreparedAudioStatus.FAILED,
                    PreparedAudioStatus.NO_AUDIO_STREAM,
                    PreparedAudioStatus.TOOL_UNAVAILABLE,
                }:
                    status = asset.status
                else:
                    status = PreparedAudioStatus.FILE_MISSING
            else:
                is_stale = self._is_asset_stale(asset=asset, inspection_report=inspection_report, snapshot=snapshot)
                if not exists:
                    status = PreparedAudioStatus.FILE_MISSING
                elif is_stale:
                    status = PreparedAudioStatus.STALE
                else:
                    status = asset.status
            if status == PreparedAudioStatus.NOT_PREPARED:
                status = asset.status
            if asset.status == PreparedAudioStatus.FILE_MISSING:
                status = PreparedAudioStatus.FILE_MISSING
            if asset.status == PreparedAudioStatus.NO_AUDIO_STREAM:
                status = PreparedAudioStatus.NO_AUDIO_STREAM
            if asset.status == PreparedAudioStatus.TOOL_UNAVAILABLE:
                status = PreparedAudioStatus.TOOL_UNAVAILABLE
            if asset.status == PreparedAudioStatus.FAILED and status == PreparedAudioStatus.NOT_PREPARED:
                status = PreparedAudioStatus.FAILED
            if selected_stream is None:
                selected_stream = _build_stream_from_asset(asset)
        elif not exists:
            status = PreparedAudioStatus.FILE_MISSING

        return PreparedAudioReport(
            video=video,
            status=status,
            is_stale=is_stale,
            prepared_audio=asset,
            selected_stream=selected_stream,
            wav_validation=wav_validation,
            cache_path=cache_path,
            metadata_path=metadata_path,
            warnings=warnings,
            errors=errors,
        )

    def _persist_asset(
        self,
        *,
        video: VideoAsset,
        inspection_report: VideoInspectionReport | None,
        snapshot: tuple[bool, int | None, datetime | None],
        status: PreparedAudioStatus,
        selected_stream: AudioStreamCandidate | None,
        wav_validation: WavInspectionResult | None = None,
        warning_code: str | None = None,
        warning_message: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        relative_cache_path: str | None = None,
        metadata_relative_path: str | None = None,
        extraction_started_at: datetime | None = None,
        extraction_completed_at: datetime | None = None,
        ffmpeg_version: str | None = None,
    ) -> PreparedAudioAsset:
        exists, size_bytes, modified_at = snapshot
        now = _utc_now()
        asset = PreparedAudioAsset(
            id=str(uuid4()),
            video_asset_id=video.id,
            source_inspection_id=inspection_report.inspection.id if inspection_report and inspection_report.inspection else None,
            status=status,
            relative_cache_path=relative_cache_path,
            metadata_relative_path=metadata_relative_path,
            format_name=wav_validation.format_name if wav_validation else "wav",
            codec_name=wav_validation.codec_name if wav_validation else "pcm_s16le",
            sample_rate_hz=wav_validation.sample_rate_hz if wav_validation else self.config.sample_rate_hz,
            channels=wav_validation.channels if wav_validation else self.config.channels,
            channel_layout="mono" if self.config.channels == 1 else None,
            bit_depth=wav_validation.bit_depth if wav_validation else self.config.bit_depth,
            duration_seconds=wav_validation.duration_seconds if wav_validation else None,
            file_size_bytes=wav_validation.file_size_bytes if wav_validation else None,
            source_file_size_bytes=size_bytes,
            source_file_modified_at=modified_at,
            selected_stream_index=selected_stream.index if selected_stream else None,
            selected_stream_codec_name=selected_stream.codec_name if selected_stream else None,
            selected_stream_channels=selected_stream.channels if selected_stream else None,
            selected_stream_channel_layout=selected_stream.channel_layout if selected_stream else None,
            selected_stream_sample_rate_hz=selected_stream.sample_rate_hz if selected_stream else None,
            selected_stream_language=selected_stream.language if selected_stream else None,
            selected_stream_is_default=selected_stream.is_default if selected_stream else None,
            extraction_started_at=extraction_started_at,
            extraction_completed_at=extraction_completed_at,
            ffmpeg_version=ffmpeg_version,
            cache_version=self.config.cache_version,
            normalization_sample_rate_hz=self.config.sample_rate_hz,
            normalization_channels=self.config.channels,
            warning_code=warning_code,
            warning_message=warning_message,
            error_code=error_code,
            error_message=error_message,
            created_at=now,
            updated_at=now,
        )
        return self.audio_repository.upsert(asset)

    def get_prepared_audio(self, video_id: str) -> PreparedAudioReport:
        video = self._require_video(video_id)
        snapshot = self._source_snapshot(video)
        inspection_report = self._inspection_report(video_id)
        asset = self._load_audio(video_id)
        selected_stream = _build_stream_from_asset(asset) if asset is not None else None
        if asset is None:
            return self._report_from_state(
                video=video,
                asset=None,
                inspection_report=inspection_report,
                snapshot=snapshot,
            )
        wav_validation = None
        cache_path, metadata_path = _build_audio_paths(self.cache_root, video.id, asset.cache_version)
        if cache_path.exists():
            try:
                wav_validation = inspect_wav_file(cache_path)
                if not _wav_matches_expected(wav_validation, self.config):
                    asset = replace(
                        asset,
                        status=PreparedAudioStatus.FAILED,
                        error_code="invalid_wav",
                        error_message="El WAV preparado no cumple con el formato esperado.",
                        updated_at=_utc_now(),
                    )
                    return self._report_from_state(
                        video=video,
                        asset=asset,
                        inspection_report=inspection_report,
                        snapshot=snapshot,
                        selected_stream=selected_stream,
                        wav_validation=wav_validation,
                        errors=("El WAV preparado no cumple con el formato esperado.",),
                    )
            except WavInspectionError as exc:
                return self._report_from_state(
                    video=video,
                    asset=asset,
                    inspection_report=inspection_report,
                    snapshot=snapshot,
                    selected_stream=selected_stream,
                    errors=(str(exc),),
                )
        return self._report_from_state(
            video=video,
            asset=asset,
            inspection_report=inspection_report,
            snapshot=snapshot,
            selected_stream=selected_stream,
            wav_validation=wav_validation,
        )

    def is_prepared_audio_stale(self, video_id: str) -> bool:
        report = self.get_prepared_audio(video_id)
        return bool(report and report.is_stale)

    def _load_audio_streams(self, inspection_report: VideoInspectionReport) -> list[AudioStreamCandidate]:
        if inspection_report.inspection is None:
            return []
        payload = json.loads(inspection_report.inspection.metadata_json or "{}")
        streams = parse_ffprobe_streams(payload)
        return build_audio_candidates(streams)

    def _current_report_after_prepare(
        self,
        *,
        video: VideoAsset,
        asset: PreparedAudioAsset | None,
        inspection_report: VideoInspectionReport | None,
        snapshot: tuple[bool, int | None, datetime | None],
        selected_stream: AudioStreamCandidate | None = None,
        wav_validation: WavInspectionResult | None = None,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> PreparedAudioReport:
        return self._report_from_state(
            video=video,
            asset=asset,
            inspection_report=inspection_report,
            snapshot=snapshot,
            selected_stream=selected_stream,
            wav_validation=wav_validation,
            warnings=warnings,
            errors=errors,
        )

    def _write_json_atomic(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(path.name + ".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temp_path.replace(path)

    def _finalize_extraction(
        self,
        *,
        working_audio_path: Path,
        working_metadata_path: Path,
        final_audio_path: Path,
        final_metadata_path: Path,
    ) -> None:
        try:
            working_audio_path.replace(final_audio_path)
            working_metadata_path.replace(final_metadata_path)
        except Exception:
            if final_audio_path.exists():
                final_audio_path.unlink(missing_ok=True)
            if final_metadata_path.exists():
                final_metadata_path.unlink(missing_ok=True)
            if working_audio_path.exists():
                working_audio_path.unlink(missing_ok=True)
            if working_metadata_path.exists():
                working_metadata_path.unlink(missing_ok=True)
            raise

    def prepare_audio(self, video_id: str, force: bool = False) -> PreparedAudioReport:
        video = self._require_video(video_id)
        snapshot = self._source_snapshot(video)
        inspection_report = self._inspection_report(video_id)
        existing = self._load_audio(video_id)
        if existing and not force:
            current_report = self._report_from_state(
                video=video,
                asset=existing,
                inspection_report=inspection_report,
                snapshot=snapshot,
            )
            if current_report.status == PreparedAudioStatus.COMPLETED and not current_report.is_stale:
                return current_report

        exists, size_bytes, modified_at = snapshot
        if not exists:
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.FILE_MISSING,
                selected_stream=None,
                error_code="file_missing",
                error_message="El archivo original no existe o no esta disponible.",
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=("El archivo original no existe o no esta disponible.",),
            )

        if inspection_report is None or inspection_report.inspection is None:
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.FAILED,
                selected_stream=None,
                error_code="inspection_missing",
                error_message="Primero debes realizar la inspeccion tecnica del video.",
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=("Primero debes realizar la inspeccion tecnica del video.",),
            )

        if inspection_report.status != VideoInspectionStatus.COMPLETED:
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.FAILED,
                selected_stream=None,
                error_code="inspection_not_completed",
                error_message="La inspeccion tecnica del video no esta completada.",
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=("La inspeccion tecnica del video no esta completada.",),
            )

        if inspection_report.is_stale:
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.STALE,
                selected_stream=None,
                error_code="inspection_stale",
                error_message="La inspeccion tecnica de origen esta desactualizada.",
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=("La inspeccion tecnica de origen esta desactualizada.",),
            )

        ffmpeg_tool = self.tool_locator.locate("ffmpeg")
        if not ffmpeg_tool.available or not ffmpeg_tool.path:
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.TOOL_UNAVAILABLE,
                selected_stream=None,
                ffmpeg_version=ffmpeg_tool.version,
                error_code="tool_unavailable",
                error_message=ffmpeg_tool.error_message or "ffmpeg no esta disponible.",
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=(ffmpeg_tool.error_message or "ffmpeg no esta disponible.",),
            )
        self.logger.info(
            "Audio preparation using FFmpeg source=%s version=%s health=%s",
            getattr(ffmpeg_tool, "source", None) or getattr(ffmpeg_tool, "installation_type", None) or "unknown",
            ffmpeg_tool.version or "unknown",
            getattr(ffmpeg_tool, "health_status", None) or "unknown",
        )

        candidates = self._load_audio_streams(inspection_report)
        if not candidates:
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.NO_AUDIO_STREAM,
                selected_stream=None,
                ffmpeg_version=ffmpeg_tool.version,
                error_code="no_audio_stream",
                error_message="El video no contiene streams de audio utilizables.",
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=("El video no contiene streams de audio utilizables.",),
            )

        selected_stream = select_audio_stream(
            candidates,
            preferred_language=self.config.preferred_language,
        )
        final_audio_path, final_metadata_path = _build_audio_paths(
            self.cache_root,
            video.id,
            self.config.cache_version,
        )
        working_audio_path = final_audio_path.with_name(final_audio_path.name + ".partial.wav")
        working_metadata_path = final_metadata_path.with_name(final_metadata_path.name + ".partial")
        if working_audio_path.exists():
            working_audio_path.unlink(missing_ok=True)
        if working_metadata_path.exists():
            working_metadata_path.unlink(missing_ok=True)

        started_at = _utc_now()
        try:
            extractor = FFmpegAudioExtractor(Path(ffmpeg_tool.path), timeout_seconds=self.settings.audio_extraction_timeout_seconds)
            acquire_lease = getattr(self.tool_locator, "acquire_lease", None)
            if callable(acquire_lease):
                lease_context = acquire_lease("ffmpeg")
            else:
                from contextlib import nullcontext

                lease_context = nullcontext()
            with lease_context:
                extractor.extract(
                    source_path=Path(video.source_path),
                    selected_stream_index=selected_stream.index,
                    destination_path=working_audio_path,
                    sample_rate_hz=self.config.sample_rate_hz,
                    channels=self.config.channels,
                )
            wav_validation = inspect_wav_file(working_audio_path)
            if not _wav_matches_expected(wav_validation, self.config):
                raise AudioValidationError(
                    "El WAV generado no cumple con el formato esperado de 16-bit mono a 16 kHz."
                )
            metadata_payload = _build_metadata_payload(
                video=video,
                inspection=inspection_report,
                config=self.config,
                selected_stream=selected_stream,
                wav_validation=wav_validation,
            )
            self._write_json_atomic(working_metadata_path, metadata_payload)
            self._finalize_extraction(
                working_audio_path=working_audio_path,
                working_metadata_path=working_metadata_path,
                final_audio_path=final_audio_path,
                final_metadata_path=final_metadata_path,
            )
            completed_at = _utc_now()
            asset = self._persist_asset(
                video=video,
                inspection_report=inspection_report,
                snapshot=snapshot,
                status=PreparedAudioStatus.COMPLETED,
                selected_stream=selected_stream,
                wav_validation=wav_validation,
                relative_cache_path=str(final_audio_path.relative_to(self.cache_root)),
                metadata_relative_path=str(final_metadata_path.relative_to(self.cache_root)),
                extraction_started_at=started_at,
                extraction_completed_at=completed_at,
                ffmpeg_version=ffmpeg_tool.version,
            )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                selected_stream=selected_stream,
                wav_validation=wav_validation,
            )
        except (FFmpegAudioExtractionError, WavInspectionError, AudioValidationError) as exc:
            self.logger.warning("No se pudo preparar el audio de %s: %s", video.id, exc)
            if working_audio_path.exists():
                working_audio_path.unlink(missing_ok=True)
            if working_metadata_path.exists():
                working_metadata_path.unlink(missing_ok=True)
            persist_failure = existing is None or existing.status != PreparedAudioStatus.COMPLETED
            if persist_failure:
                asset = self._persist_asset(
                    video=video,
                    inspection_report=inspection_report,
                    snapshot=snapshot,
                    status=PreparedAudioStatus.FAILED,
                    selected_stream=selected_stream,
                    ffmpeg_version=ffmpeg_tool.version,
                    error_code="extraction_failed",
                    error_message=str(exc),
                )
            else:
                asset = replace(
                    existing,
                    status=PreparedAudioStatus.FAILED,
                    warning_code=None,
                    warning_message=None,
                    error_code="extraction_failed",
                    error_message=str(exc),
                    updated_at=_utc_now(),
                )
            return self._current_report_after_prepare(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                selected_stream=selected_stream,
                errors=(str(exc),),
            )

    def verify_prepared_audio(self, video_id: str) -> PreparedAudioReport:
        video = self._require_video(video_id)
        snapshot = self._source_snapshot(video)
        inspection_report = self._inspection_report(video_id)
        asset = self._load_audio(video_id)
        if asset is None:
            return self._report_from_state(
                video=video,
                asset=None,
                inspection_report=inspection_report,
                snapshot=snapshot,
            )
        cache_path, metadata_path = _build_audio_paths(self.cache_root, video.id, asset.cache_version)
        if not cache_path.exists() or not metadata_path.exists():
            return self._report_from_state(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=("El archivo WAV preparado o su metadata ya no existe.",),
            )
        try:
            wav_validation = inspect_wav_file(cache_path)
            if not _wav_matches_expected(wav_validation, self.config):
                temp_asset = replace(
                    asset,
                    status=PreparedAudioStatus.FAILED,
                    error_code="invalid_wav",
                    error_message="El WAV preparado no cumple con el formato esperado.",
                    updated_at=_utc_now(),
                )
                return self._report_from_state(
                    video=video,
                    asset=temp_asset,
                    inspection_report=inspection_report,
                    snapshot=snapshot,
                    errors=("El WAV preparado no cumple con el formato esperado.",),
                    wav_validation=wav_validation,
                )
        except WavInspectionError as exc:
            return self._report_from_state(
                video=video,
                asset=asset,
                inspection_report=inspection_report,
                snapshot=snapshot,
                errors=(str(exc),),
            )
        selected_stream = _build_stream_from_asset(asset)
        return self._report_from_state(
            video=video,
            asset=asset,
            inspection_report=inspection_report,
            snapshot=snapshot,
            selected_stream=selected_stream,
            wav_validation=wav_validation,
        )

    def delete_prepared_audio_cache(self, video_id: str) -> AudioCacheDeletionResult:
        video = self._require_video(video_id)
        asset = self._load_audio(video_id)
        deleted_files: list[str] = []
        if asset is not None:
            cache_path, metadata_path = _build_audio_paths(self.cache_root, video.id, asset.cache_version)
            for path in (cache_path, metadata_path):
                if _safe_delete(path, root=self.cache_root):
                    deleted_files.append(str(path))
        else:
            final_audio_path, final_metadata_path = _build_audio_paths(
                self.cache_root,
                video.id,
                self.config.cache_version,
            )
            for path in (final_audio_path, final_metadata_path):
                if _safe_delete(path, root=self.cache_root):
                    deleted_files.append(str(path))
        deleted_record = self.audio_repository.delete_by_video_asset_id(video.id)
        if deleted_files:
            parent = _build_audio_dir(self.cache_root, video.id)
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        return AudioCacheDeletionResult(
            video_id=video.id,
            deleted_record=deleted_record,
            deleted_files=tuple(deleted_files),
        )


def build_audio_preparation_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    video_repository: VideoRepository,
    inspection_service: MediaInspectionService,
    audio_repository: PreparedAudioRepository,
    logger: logging.Logger | None = None,
    tool_locator: MediaToolLocator | None = None,
) -> AudioPreparationService:
    """Construye el servicio de preparacion de audio."""

    return AudioPreparationService(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        inspection_service=inspection_service,
        audio_repository=audio_repository,
        logger=logger,
        tool_locator=tool_locator,
    )
