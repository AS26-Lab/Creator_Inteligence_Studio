"""Servicio de aplicacion para analisis multimodal local."""

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

from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.errors import ConflictError, NotFoundError
from creator_intelligence_studio.domain.multimodal_analysis.entities import (
    MultimodalAnalysis,
    MultimodalMomentCandidate,
    MultimodalTimelineWindow,
)
from creator_intelligence_studio.domain.multimodal_analysis.errors import MultimodalAnalysisStateError
from creator_intelligence_studio.domain.multimodal_analysis.repositories import MultimodalAnalysisRepository
from creator_intelligence_studio.domain.multimodal_analysis.services import (
    build_multimodal_configuration_fingerprint,
    build_multimodal_source_fingerprint,
    is_multimodal_analysis_stale,
    normalize_multimodal_analysis_config,
)
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import (
    MultimodalAnalysisOptions,
    MultimodalAnalysisStatus,
    MultimodalCandidateType,
    MultimodalMomentCandidateData,
    MultimodalTimelineWindowData,
)
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.visual_analysis.entities import VisualAnalysis, VisualEvent, VisualScene, VisualTimelineWindow
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.multimodal_analysis.evidence_builder import build_window_evidence
from creator_intelligence_studio.infrastructure.multimodal_analysis.feature_normalizer import clamp01, normalize_series
from creator_intelligence_studio.infrastructure.multimodal_analysis.moment_candidate_detector import detect_candidate_seeds, merge_candidate_seeds
from creator_intelligence_studio.infrastructure.multimodal_analysis.scoring import compute_scores
from creator_intelligence_studio.infrastructure.multimodal_analysis.timeline_aligner import build_window_spans, overlap_ratio
from creator_intelligence_studio.infrastructure.persistence.sqlite_acoustic_analysis_repository import SQLiteAcousticAnalysisRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_visual_analysis_repository import SQLiteVisualAnalysisRepository
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class MultimodalAnalysisReport:
    """Estado y resultado del analisis multimodal."""

    video: VideoAsset
    transcription: Transcription | None
    acoustic_analysis: AcousticAnalysis | None
    visual_analysis: VisualAnalysis | None
    analysis: MultimodalAnalysis | None
    windows: tuple[MultimodalTimelineWindow, ...]
    candidates: tuple[MultimodalMomentCandidate, ...]
    status: MultimodalAnalysisStatus
    is_stale: bool
    available_sources: tuple[str, ...] = ()
    missing_sources: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "transcription": self.transcription.to_dict() if self.transcription else None,
            "acoustic_analysis": self.acoustic_analysis.to_dict() if self.acoustic_analysis else None,
            "visual_analysis": self.visual_analysis.to_dict() if self.visual_analysis else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "windows": [window.to_dict() for window in self.windows],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "status": self.status.value,
            "is_stale": self.is_stale,
            "available_sources": list(self.available_sources),
            "missing_sources": list(self.missing_sources),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class MultimodalAnalysisExportResult:
    """Resultado de exportacion del analisis multimodal."""

    video: VideoAsset
    analysis: MultimodalAnalysis
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


def _snapshot_file(video: VideoAsset) -> tuple[bool, int | None, datetime | None]:
    path = Path(video.source_path)
    if not path.exists() or not path.is_file():
        return False, None, None
    stat = path.stat()
    return True, stat.st_size, datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _safe_delete(path: Path, *, root: Path) -> bool:
    try:
        if not path.resolve().is_relative_to(root.resolve()):
            return False
    except FileNotFoundError:
        pass
    if not path.exists():
        return False
    if path.is_dir():
        import shutil

        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def _json_default(value):
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class MultimodalAnalysisService:
    """Coordina alineacion multimodal, persistencia y exportacion."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        video_repository: VideoRepository,
        transcription_repository: SQLiteTranscriptionRepository,
        acoustic_repository: SQLiteAcousticAnalysisRepository,
        visual_repository: SQLiteVisualAnalysisRepository,
        multimodal_repository: MultimodalAnalysisRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.video_repository = video_repository
        self.transcription_repository = transcription_repository
        self.acoustic_repository = acoustic_repository
        self.visual_repository = visual_repository
        self.multimodal_repository = multimodal_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.multimodal")
        self.options = normalize_multimodal_analysis_config(MultimodalAnalysisOptions())
        self._active_jobs: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _load_transcription(self, video_id: str) -> Transcription | None:
        transcription = self.transcription_repository.get_by_video_asset_id(video_id)
        return transcription if transcription is not None and transcription.status == TranscriptionStatus.COMPLETED else None

    def _load_acoustic(self, video_id: str) -> AcousticAnalysis | None:
        analysis = self.acoustic_repository.get_by_video_asset_id(video_id)
        return analysis if analysis is not None and analysis.status.value == "completed" else None

    def _load_visual(self, video_id: str) -> VisualAnalysis | None:
        analysis = self.visual_repository.get_by_video_asset_id(video_id)
        return analysis if analysis is not None and analysis.status.value == "completed" else None

    def _load_analysis(self, video_id: str) -> MultimodalAnalysis | None:
        return self.multimodal_repository.get_by_video_asset_id(video_id)

    def _analysis_root(self, video_id: str) -> Path:
        return self.paths.project_root / "cache" / "multimodal" / video_id

    def _export_root(self, video_id: str) -> Path:
        return self._analysis_root(video_id) / "exports"

    def _available_sources(
        self,
        *,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
    ) -> tuple[str, ...]:
        sources: list[str] = []
        if transcription is not None:
            sources.append("transcription")
        if acoustic_analysis is not None:
            sources.append("acoustic")
        if visual_analysis is not None:
            sources.append("visual")
        return tuple(sources)

    def _missing_sources(
        self,
        *,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
    ) -> tuple[str, ...]:
        sources: list[str] = []
        if transcription is None:
            sources.append("transcription")
        if acoustic_analysis is None:
            sources.append("acoustic")
        if visual_analysis is None:
            sources.append("visual")
        return tuple(sources)

    def _duration_seconds(
        self,
        *,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
    ) -> float:
        durations = [
            float(item)
            for item in (
                transcription.duration_seconds if transcription else None,
                acoustic_analysis.duration_seconds if acoustic_analysis else None,
                visual_analysis.duration_seconds if visual_analysis else None,
            )
            if item is not None
        ]
        if not durations:
            raise MultimodalAnalysisStateError("No hay fuentes de analisis disponibles para construir una linea temporal multimodal.")
        return max(durations)

    def _safe_duration_seconds(
        self,
        *,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
    ) -> float | None:
        try:
            return self._duration_seconds(
                transcription=transcription,
                acoustic_analysis=acoustic_analysis,
                visual_analysis=visual_analysis,
            )
        except MultimodalAnalysisStateError:
            return None

    def _scene_index_for_time(self, scenes: list[VisualScene], start_seconds: float, end_seconds: float) -> int | None:
        midpoint = (start_seconds + end_seconds) / 2.0
        for scene in scenes:
            if scene.start_seconds <= midpoint < scene.end_seconds:
                return scene.scene_index
        if scenes:
            if midpoint < scenes[0].start_seconds:
                return scenes[0].scene_index
            if midpoint >= scenes[-1].end_seconds:
                return scenes[-1].scene_index
        return None

    def _segment_text(self, segments: list[TranscriptionSegment], start_seconds: float, end_seconds: float) -> tuple[str, int]:
        selected = [segment.text.strip() for segment in segments if overlap_ratio(start_seconds, end_seconds, segment.start_seconds, segment.end_seconds) > 0.0 and segment.text.strip()]
        text = " ".join(selected).strip()
        words = len([word for word in text.split() if word])
        return text, words

    def _collect_windows(
        self,
        *,
        duration_seconds: float,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
    ) -> list[MultimodalTimelineWindowData]:
        transcription_segments = list(self.transcription_repository.list_segments(transcription.id)) if transcription else []
        acoustic_windows = self.acoustic_repository.list_windows(acoustic_analysis.id) if acoustic_analysis else []
        acoustic_events = self.acoustic_repository.list_events(acoustic_analysis.id) if acoustic_analysis else []
        visual_windows = self.visual_repository.list_windows(visual_analysis.id) if visual_analysis else []
        visual_events = self.visual_repository.list_events(visual_analysis.id) if visual_analysis else []
        visual_scenes = self.visual_repository.list_scenes(visual_analysis.id) if visual_analysis else []
        spans = build_window_spans(duration_seconds, self.options.window_size_seconds)
        if not spans:
            return []

        raw_windows: list[dict[str, object]] = []
        for span in spans:
            transcript_text, word_count = self._segment_text(transcription_segments, span.start_seconds, span.end_seconds)
            acoustic_overlaps = [window for window in acoustic_windows if overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) > 0.0]
            visual_overlaps = [window for window in visual_windows if overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) > 0.0]
            acoustic_energy = sum(window.normalized_energy * overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) for window in acoustic_overlaps)
            acoustic_change = sum(abs(window.normalized_energy - acoustic_overlaps[index - 1].normalized_energy) * 0.5 for index, window in enumerate(acoustic_overlaps) if index > 0)
            visual_motion = sum(window.motion_score * overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) for window in visual_overlaps)
            visual_change = sum(window.color_change_score * overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) for window in visual_overlaps)
            brightness_values = [window.brightness for window in visual_overlaps]
            brightness = sum(brightness_values) / len(brightness_values) if brightness_values else 0.0
            cut_count = sum(1 for event in self.visual_repository.list_events(visual_analysis.id) if event.start_seconds < span.end_seconds and event.end_seconds > span.start_seconds and event.event_type.value in {"hard_cut", "gradual_transition"})
            acoustic_event_count = sum(1 for event in acoustic_events if event.start_seconds < span.end_seconds and event.end_seconds > span.start_seconds)
            visual_event_count = sum(1 for event in visual_events if event.start_seconds < span.end_seconds and event.end_seconds > span.start_seconds)
            speech_ratio = sum(window.speech_probability * overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) for window in acoustic_overlaps)
            if acoustic_overlaps:
                speech_ratio = clamp01(speech_ratio / max(1e-9, sum(overlap_ratio(span.start_seconds, span.end_seconds, window.start_seconds, window.end_seconds) for window in acoustic_overlaps)))
            else:
                speech_ratio = 1.0 if transcript_text else 0.0
            silence_ratio = clamp01(1.0 - speech_ratio)
            speech_rate = (word_count / max(span.end_seconds - span.start_seconds, 1e-9)) * 60.0 if word_count else 0.0
            scene_index = self._scene_index_for_time(visual_scenes, span.start_seconds, span.end_seconds)
            raw_windows.append(
                {
                    "window_index": span.window_index,
                    "start_seconds": span.start_seconds,
                    "end_seconds": span.end_seconds,
                    "transcript_text": transcript_text,
                    "word_count": word_count,
                    "speech_ratio": speech_ratio,
                    "silence_ratio": silence_ratio,
                    "speech_rate": speech_rate,
                    "acoustic_energy": clamp01(acoustic_energy),
                    "acoustic_change": clamp01(acoustic_change),
                    "visual_motion": clamp01(visual_motion),
                    "visual_change": clamp01(visual_change),
                    "brightness": clamp01(brightness),
                    "cut_count": cut_count,
                    "scene_index": scene_index,
                    "acoustic_event_count": acoustic_event_count,
                    "visual_event_count": visual_event_count,
                }
            )

        speech_rate_norm = normalize_series([float(window["speech_rate"]) for window in raw_windows])
        acoustic_energy_norm = normalize_series([float(window["acoustic_energy"]) for window in raw_windows])
        acoustic_change_norm = normalize_series([float(window["acoustic_change"]) for window in raw_windows])
        visual_motion_norm = normalize_series([float(window["visual_motion"]) for window in raw_windows])
        visual_change_norm = normalize_series([float(window["visual_change"]) for window in raw_windows])
        brightness_norm = normalize_series([float(window["brightness"]) for window in raw_windows])
        windows: list[MultimodalTimelineWindowData] = []
        total_windows = len(raw_windows)
        for index, window in enumerate(raw_windows):
            context_indexes = [position for position in range(max(0, index - 2), min(total_windows, index + 3)) if position != index]
            context_activity = sum(float(raw_windows[position]["acoustic_energy"]) + float(raw_windows[position]["visual_motion"]) for position in context_indexes)
            context_count = max(1, len(context_indexes))
            context_activity /= context_count * 2.0
            coverage = 0.0
            if transcription is not None:
                coverage += 1.0
            if acoustic_analysis is not None:
                coverage += 1.0
            if visual_analysis is not None:
                coverage += 1.0
            coverage /= 3.0
            agreement = (
                float(window["speech_ratio"]) + float(window["acoustic_energy"]) + float(window["visual_motion"])
            ) / 3.0
            scores = compute_scores(
                acoustic_energy=acoustic_energy_norm[index],
                speech_rate=speech_rate_norm[index],
                visual_motion=visual_motion_norm[index],
                cut_count=int(window["cut_count"]),
                acoustic_event_count=int(window["acoustic_event_count"]),
                visual_event_count=int(window["visual_event_count"]),
                acoustic_change=acoustic_change_norm[index],
                visual_change=visual_change_norm[index],
                speech_ratio=float(window["speech_ratio"]),
                silence_ratio=float(window["silence_ratio"]),
                context_activity=context_activity,
                options=self.options,
                coverage=coverage,
                agreement=agreement,
            )
            window_dict = dict(window)
            window_dict.update(
                {
                    "speech_rate": float(window["speech_rate"]),
                    "acoustic_energy": acoustic_energy_norm[index],
                    "acoustic_change": acoustic_change_norm[index],
                    "visual_motion": visual_motion_norm[index],
                    "visual_change": visual_change_norm[index],
                    "brightness": brightness_norm[index],
                    "cut_count": int(window["cut_count"]),
                    "combined_activity_score": scores.combined_activity_score,
                    "transition_score": scores.transition_score,
                    "novelty_score": scores.novelty_score,
                    "confidence": scores.confidence,
                }
            )
            windows.append(
                MultimodalTimelineWindowData(
                    evidence=build_window_evidence(window_dict),
                    **window_dict,
                )
            )
        return windows

    def _add_scene_boundary_candidates(
        self,
        windows: list[MultimodalTimelineWindowData],
        candidates: list[MultimodalMomentCandidateData],
        visual_analysis: VisualAnalysis | None,
    ) -> list[MultimodalMomentCandidateData]:
        if visual_analysis is None:
            return candidates
        scenes = self.visual_repository.list_scenes(visual_analysis.id)
        if not scenes:
            return candidates
        seed_candidates = list(candidates)
        for scene in scenes:
            scene_windows = [window for window in windows if scene.start_seconds <= window.start_seconds < scene.end_seconds]
            if not scene_windows:
                continue
            leading = scene_windows[0]
            trailing = scene_windows[-1]
            if leading.combined_activity_score >= 0.45:
                seed_candidates.append(
                    MultimodalMomentCandidateData(
                        candidate_index=0,
                        start_seconds=leading.start_seconds,
                        end_seconds=min(leading.end_seconds, scene.start_seconds + self.options.window_size_seconds),
                        candidate_type=MultimodalCandidateType.SCENE_OPENING,
                        score=leading.combined_activity_score,
                        confidence=leading.confidence,
                        title="Scene Opening",
                        summary="scene_opening | evidence from scene boundary",
                        evidence={"scene_index": scene.scene_index, "boundary": "opening", "source": "visual_scene"},
                        source_window_start=leading.start_seconds,
                        source_window_end=leading.end_seconds,
                    )
                )
            if trailing.combined_activity_score >= 0.45:
                seed_candidates.append(
                    MultimodalMomentCandidateData(
                        candidate_index=0,
                        start_seconds=max(scene.start_seconds, trailing.start_seconds),
                        end_seconds=trailing.end_seconds,
                        candidate_type=MultimodalCandidateType.SCENE_CLOSING,
                        score=trailing.transition_score,
                        confidence=trailing.confidence,
                        title="Scene Closing",
                        summary="scene_closing | evidence from scene boundary",
                        evidence={"scene_index": scene.scene_index, "boundary": "closing", "source": "visual_scene"},
                        source_window_start=trailing.start_seconds,
                        source_window_end=trailing.end_seconds,
                    )
                )
        return seed_candidates

    def _build_analysis_entity(
        self,
        *,
        analysis_id: str,
        video: VideoAsset,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
        duration_seconds: float,
        windows: list[MultimodalTimelineWindowData],
        candidates: list[MultimodalMomentCandidateData],
        started_at: datetime,
        completed_at: datetime,
    ) -> tuple[MultimodalAnalysis, list[MultimodalTimelineWindow], list[MultimodalMomentCandidate]]:
        configuration_fingerprint = build_multimodal_configuration_fingerprint(self.options)
        source_fingerprint = build_multimodal_source_fingerprint(
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            duration_seconds=duration_seconds,
        )
        high_count = sum(1 for candidate in candidates if candidate.candidate_type == MultimodalCandidateType.HIGH_COMBINED_ACTIVITY)
        transition_count = sum(1 for candidate in candidates if candidate.candidate_type in {MultimodalCandidateType.ABRUPT_MULTIMODAL_CHANGE, MultimodalCandidateType.VISUAL_TRANSITION_WITH_SPEECH})
        silence_count = sum(1 for candidate in candidates if candidate.candidate_type == MultimodalCandidateType.LONG_SILENCE_OR_PAUSE or candidate.candidate_type == MultimodalCandidateType.LOW_ACTIVITY_SEGMENT)
        analysis = MultimodalAnalysis(
            id=analysis_id,
            video_asset_id=video.id,
            transcription_id=transcription.id if transcription else None,
            acoustic_analysis_id=acoustic_analysis.id if acoustic_analysis else None,
            visual_analysis_id=visual_analysis.id if visual_analysis else None,
            status=MultimodalAnalysisStatus.COMPLETED,
            analyzer_version=self.options.analyzer_version,
            configuration_fingerprint=configuration_fingerprint,
            source_fingerprint=source_fingerprint,
            duration_seconds=duration_seconds,
            window_size_seconds=self.options.window_size_seconds,
            window_count=len(windows),
            candidate_count=len(candidates),
            high_activity_candidate_count=high_count,
            transition_candidate_count=transition_count,
            silence_candidate_count=silence_count,
            started_at=started_at,
            completed_at=completed_at,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=completed_at,
            updated_at=completed_at,
        )
        persisted_windows: list[MultimodalTimelineWindow] = []
        for window in windows:
            persisted_windows.append(
                MultimodalTimelineWindow(
                    id=str(uuid4()),
                    multimodal_analysis_id=analysis.id,
                    window_index=window.window_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    transcript_text=window.transcript_text,
                    word_count=window.word_count,
                    speech_ratio=window.speech_ratio,
                    silence_ratio=window.silence_ratio,
                    speech_rate=window.speech_rate,
                    acoustic_energy=window.acoustic_energy,
                    acoustic_change=window.acoustic_change,
                    visual_motion=window.visual_motion,
                    visual_change=window.visual_change,
                    brightness=window.brightness,
                    cut_count=window.cut_count,
                    scene_index=window.scene_index,
                    acoustic_event_count=window.acoustic_event_count,
                    visual_event_count=window.visual_event_count,
                    combined_activity_score=window.combined_activity_score,
                    transition_score=window.transition_score,
                    novelty_score=window.novelty_score,
                    confidence=window.confidence,
                    evidence_json=json.dumps(window.evidence, ensure_ascii=False, sort_keys=True, default=_json_default),
                    created_at=completed_at,
                )
            )
        persisted_candidates: list[MultimodalMomentCandidate] = []
        for candidate in candidates:
            persisted_candidates.append(
                MultimodalMomentCandidate(
                    id=str(uuid4()),
                    multimodal_analysis_id=analysis.id,
                    candidate_index=candidate.candidate_index,
                    start_seconds=candidate.start_seconds,
                    end_seconds=candidate.end_seconds,
                    candidate_type=candidate.candidate_type,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    title=candidate.title,
                    summary=candidate.summary,
                    evidence_json=json.dumps(candidate.evidence, ensure_ascii=False, sort_keys=True, default=_json_default),
                    source_window_start=candidate.source_window_start,
                    source_window_end=candidate.source_window_end,
                    created_at=completed_at,
                )
            )
        return analysis, persisted_windows, persisted_candidates

    def _report(
        self,
        *,
        video: VideoAsset,
        transcription: Transcription | None,
        acoustic_analysis: AcousticAnalysis | None,
        visual_analysis: VisualAnalysis | None,
        analysis: MultimodalAnalysis | None,
        windows: list[MultimodalTimelineWindow] | None = None,
        candidates: list[MultimodalMomentCandidate] | None = None,
        status: MultimodalAnalysisStatus | None = None,
        is_stale: bool = False,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
        progress_message: str | None = None,
    ) -> MultimodalAnalysisReport:
        if analysis is not None:
            if windows is None:
                windows = self.multimodal_repository.list_windows(analysis.id)
            if candidates is None:
                candidates = self.multimodal_repository.list_candidates(analysis.id)
        resolved_status = status or (analysis.status if analysis else MultimodalAnalysisStatus.NOT_ANALYZED)
        computed_warnings = tuple(warnings) + tuple(
            f"Fuente {source} no disponible" for source in self._missing_sources(
                transcription=transcription,
                acoustic_analysis=acoustic_analysis,
                visual_analysis=visual_analysis,
            )
        )
        return MultimodalAnalysisReport(
            video=video,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            analysis=analysis,
            windows=tuple(windows or ()),
            candidates=tuple(candidates or ()),
            status=resolved_status,
            is_stale=is_stale,
            available_sources=self._available_sources(
                transcription=transcription,
                acoustic_analysis=acoustic_analysis,
                visual_analysis=visual_analysis,
            ),
            missing_sources=self._missing_sources(
                transcription=transcription,
                acoustic_analysis=acoustic_analysis,
                visual_analysis=visual_analysis,
            ),
            warnings=computed_warnings,
            errors=errors,
            progress_message=progress_message,
        )

    def analyze_multimodal(self, video_id: str, force: bool = False, *, progress_callback=None) -> MultimodalAnalysisReport:
        video = self._require_video(video_id)
        transcription = self._load_transcription(video.id)
        acoustic_analysis = self._load_acoustic(video.id)
        visual_analysis = self._load_visual(video.id)
        existing = self._load_analysis(video.id)
        source_snapshot = _snapshot_file(video)
        current_duration = self._safe_duration_seconds(
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
        )
        if existing and not force and not is_multimodal_analysis_stale(
            existing,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            options=self.options,
            duration_seconds=current_duration,
        ):
            return self.get_multimodal_analysis(video.id)
        if transcription is None and acoustic_analysis is None and visual_analysis is None:
            raise MultimodalAnalysisStateError("No existen fuentes de analisis disponibles para calcular la linea temporal multimodal.")
        if source_snapshot[0] is False:
            warnings = ("El archivo fuente no esta disponible; se usaran solo los analisis persistidos.",)
        else:
            warnings = ()
        if progress_callback is not None:
            progress_callback("Cargando fuentes", 0.05)
        duration_seconds = self._duration_seconds(
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
        )
        if progress_callback is not None:
            progress_callback("Alineando timelines", 0.20)
        windows = self._collect_windows(
            duration_seconds=duration_seconds,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
        )
        if progress_callback is not None:
            progress_callback("Normalizando señales", 0.40)
        candidate_seeds = detect_candidate_seeds(windows, self.options, duration_seconds=duration_seconds)
        if progress_callback is not None:
            progress_callback("Detectando cambios", 0.60)
        candidates = merge_candidate_seeds(candidate_seeds, self.options)
        candidates = [candidate for candidate in candidates if candidate.confidence >= self.options.candidate_confidence_threshold or candidate.score >= self.options.candidate_confidence_threshold]
        candidates = self._add_scene_boundary_candidates(windows, candidates, visual_analysis)
        candidates = sorted(candidates, key=lambda item: (item.start_seconds, item.end_seconds, item.score, item.candidate_type.value))
        if progress_callback is not None:
            progress_callback("Fusionando candidatos", 0.82)
        analysis_id = existing.id if existing else str(uuid4())
        started_at = utc_now()
        completed_at = utc_now()
        analysis, persisted_windows, persisted_candidates = self._build_analysis_entity(
            analysis_id=analysis_id,
            video=video,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            duration_seconds=duration_seconds,
            windows=windows,
            candidates=[
                MultimodalMomentCandidateData(
                    candidate_index=index,
                    start_seconds=candidate.start_seconds,
                    end_seconds=candidate.end_seconds,
                    candidate_type=candidate.candidate_type,
                    score=candidate.score,
                    confidence=candidate.confidence,
                    title=candidate.title,
                    summary=candidate.summary,
                    evidence=candidate.evidence,
                    source_window_start=candidate.source_window_start,
                    source_window_end=candidate.source_window_end,
                )
                for index, candidate in enumerate(candidates)
            ],
            started_at=started_at,
            completed_at=completed_at,
        )
        if progress_callback is not None:
            progress_callback("Guardando resultados", 0.95)
        persisted = self.multimodal_repository.upsert(analysis, persisted_windows, persisted_candidates)
        if progress_callback is not None:
            progress_callback("Completado", 1.0)
        return self._report(
            video=video,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            analysis=persisted,
            windows=self.multimodal_repository.list_windows(persisted.id),
            candidates=self.multimodal_repository.list_candidates(persisted.id),
            status=MultimodalAnalysisStatus.COMPLETED,
            is_stale=False,
            warnings=warnings,
            progress_message="Completado",
        )

    def get_multimodal_analysis(self, video_id: str) -> MultimodalAnalysisReport:
        video = self._require_video(video_id)
        transcription = self._load_transcription(video.id)
        acoustic_analysis = self._load_acoustic(video.id)
        visual_analysis = self._load_visual(video.id)
        analysis = self._load_analysis(video.id)
        current_duration = self._safe_duration_seconds(
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
        )
        is_stale = is_multimodal_analysis_stale(
            analysis,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            options=self.options,
            duration_seconds=current_duration,
        )
        if analysis is None:
            return self._report(
                video=video,
                transcription=transcription,
                acoustic_analysis=acoustic_analysis,
                visual_analysis=visual_analysis,
                analysis=None,
                status=MultimodalAnalysisStatus.NOT_ANALYZED,
                is_stale=False,
            )
        status = analysis.status
        if is_stale:
            status = MultimodalAnalysisStatus.STALE
        windows = self.multimodal_repository.list_windows(analysis.id)
        candidates = self.multimodal_repository.list_candidates(analysis.id)
        return self._report(
            video=video,
            transcription=transcription,
            acoustic_analysis=acoustic_analysis,
            visual_analysis=visual_analysis,
            analysis=analysis,
            windows=windows,
            candidates=candidates,
            status=status,
            is_stale=is_stale,
        )

    def get_multimodal_timeline(self, video_id: str) -> list[MultimodalTimelineWindow]:
        report = self.get_multimodal_analysis(video_id)
        return list(report.windows)

    def list_moment_candidates(self, video_id: str) -> list[MultimodalMomentCandidate]:
        report = self.get_multimodal_analysis(video_id)
        return list(report.candidates)

    def get_moment_candidate(self, candidate_id: str) -> MultimodalMomentCandidate:
        candidate = self.multimodal_repository.get_candidate_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError("El candidato solicitado no existe.")
        return candidate

    def is_multimodal_analysis_stale(self, video_id: str) -> bool:
        return self.get_multimodal_analysis(video_id).is_stale

    def delete_multimodal_analysis(self, video_id: str) -> bool:
        deleted = self.multimodal_repository.delete_by_video_asset_id(video_id)
        _safe_delete(self._analysis_root(video_id), root=self.paths.project_root / "cache")
        return deleted

    def export_multimodal_analysis(
        self,
        video_id: str,
        format_name: str,
        *,
        destination: Path | None = None,
    ) -> MultimodalAnalysisExportResult:
        report = self.get_multimodal_analysis(video_id)
        if report.analysis is None:
            raise MultimodalAnalysisStateError("No hay analisis multimodal disponible para exportar.")
        export_root = self._export_root(video_id)
        export_root.mkdir(parents=True, exist_ok=True)
        if destination is None:
            suffix = {
                "json": "json",
                "timeline-csv": "timeline.csv",
                "candidates-csv": "candidates.csv",
                "txt": "txt",
            }.get(format_name)
            if suffix is None:
                raise MultimodalAnalysisStateError(f"Formato de exportacion no soportado: {format_name}.")
            destination = export_root / f"multimodal_analysis.{suffix}"
        elif destination.is_dir():
            raise MultimodalAnalysisStateError("La ruta de exportacion debe ser un archivo, no un directorio.")

        if format_name == "json":
            content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default)
        elif format_name == "timeline-csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(report.windows[0].to_dict().keys()) if report.windows else [])
            if report.windows:
                writer.writeheader()
                for window in report.windows:
                    writer.writerow(window.to_dict())
            content = output.getvalue()
        elif format_name == "candidates-csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(report.candidates[0].to_dict().keys()) if report.candidates else [])
            if report.candidates:
                writer.writeheader()
                for candidate in report.candidates:
                    writer.writerow(candidate.to_dict())
            content = output.getvalue()
        elif format_name == "txt":
            lines = [
                f"Analisis multimodal: {report.status.value}",
                f"Video: {report.video.id}",
                f"Duracion: {report.analysis.duration_seconds:.3f} s",
                f"Ventanas: {len(report.windows)}",
                f"Candidatos: {len(report.candidates)}",
                f"Fuentes disponibles: {', '.join(report.available_sources) or 'ninguna'}",
                f"Fuentes faltantes: {', '.join(report.missing_sources) or 'ninguna'}",
            ]
            if report.analysis.warning_message:
                lines.append(f"Advertencia: {report.analysis.warning_message}")
            if report.analysis.error_message:
                lines.append(f"Error: {report.analysis.error_message}")
            content = "\n".join(lines) + "\n"
        else:
            raise MultimodalAnalysisStateError(f"Formato de exportacion no soportado: {format_name}.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        return MultimodalAnalysisExportResult(
            video=report.video,
            analysis=report.analysis,
            format=format_name,
            content=content,
            path=str(destination),
        )


def build_multimodal_analysis_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    video_repository: VideoRepository,
    transcription_repository: SQLiteTranscriptionRepository,
    acoustic_repository: SQLiteAcousticAnalysisRepository,
    visual_repository: SQLiteVisualAnalysisRepository,
    multimodal_repository: MultimodalAnalysisRepository,
    logger: logging.Logger | None = None,
) -> MultimodalAnalysisService:
    return MultimodalAnalysisService(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        transcription_repository=transcription_repository,
        acoustic_repository=acoustic_repository,
        visual_repository=visual_repository,
        multimodal_repository=multimodal_repository,
        logger=logger,
    )
