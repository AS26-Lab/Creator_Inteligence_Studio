"""Estado agregado y ejecucion guiada del pipeline por video."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from creator_intelligence_studio.application.services.acoustic_analysis_service import AcousticAnalysisService
from creator_intelligence_studio.application.services.audio_preparation_service import AudioPreparationService
from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.clip_ranking_service import ClipRankingService
from creator_intelligence_studio.application.services.media_inspection_service import MediaInspectionService
from creator_intelligence_studio.application.services.multimodal_analysis_service import MultimodalAnalysisService
from creator_intelligence_studio.application.services.personalization_dataset_service import PersonalizationDatasetService
from creator_intelligence_studio.application.services.transcription_service import TranscriptionService
from creator_intelligence_studio.application.services.visual_analysis_service import VisualAnalysisService
from creator_intelligence_studio.domain.errors import NotFoundError
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationReadinessStatus
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionOptions, TranscriptionModelStatus
from creator_intelligence_studio.shared.dates import to_iso_z


@dataclass(frozen=True, slots=True)
class VideoPipelineStageStatus:
    name: str
    display_name: str
    status: str
    available: bool
    stale: bool
    completed_at: str | None
    summary: str
    error: str | None
    action_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "status": self.status,
            "available": self.available,
            "stale": self.stale,
            "completed_at": self.completed_at,
            "summary": self.summary,
            "error": self.error,
            "action_id": self.action_id,
        }


@dataclass(frozen=True, slots=True)
class VideoPipelineStatus:
    video_id: str
    current_stage: str
    recommended_action: str
    overall_status: str
    progress_percent: float
    blocked_reason: str | None
    warnings: tuple[str, ...]
    stages: tuple[VideoPipelineStageStatus, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "video_id": self.video_id,
            "current_stage": self.current_stage,
            "recommended_action": self.recommended_action,
            "overall_status": self.overall_status,
            "progress_percent": self.progress_percent,
            "blocked_reason": self.blocked_reason,
            "warnings": list(self.warnings),
            "stages": [stage.to_dict() for stage in self.stages],
        }


@dataclass(frozen=True, slots=True)
class VideoWorkflowStepResult:
    stage_name: str
    status: str
    message: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_name": self.stage_name,
            "status": self.status,
            "message": self.message,
            "updated_at": self.updated_at,
        }


class VideoPipelineService:
    """Agrega estados publicos y ejecuta el siguiente paso recomendado."""

    def __init__(
        self,
        *,
        catalog_service: CatalogService,
        media_service: MediaInspectionService,
        audio_service: AudioPreparationService,
        transcription_service: TranscriptionService,
        acoustic_service: AcousticAnalysisService,
        visual_service: VisualAnalysisService,
        multimodal_service: MultimodalAnalysisService,
        clip_service: ClipRankingService,
        personalization_service: PersonalizationDatasetService | None = None,
    ) -> None:
        self.catalog_service = catalog_service
        self.media_service = media_service
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.acoustic_service = acoustic_service
        self.visual_service = visual_service
        self.multimodal_service = multimodal_service
        self.clip_service = clip_service
        self.personalization_service = personalization_service

    def _require_video(self, video_id: str):
        video = self.catalog_service.get_video(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _status_label(self, value: str) -> str:
        return {
            "not_prepared": "pending",
            "queued": "running",
            "extracting": "running",
            "completed": "completed",
            "failed": "failed",
            "file_missing": "failed",
            "no_audio_stream": "blocked",
            "tool_unavailable": "unavailable",
            "stale": "stale",
            "not_transcribed": "pending",
            "loading_model": "running",
            "model_unavailable": "blocked",
            "not_analyzed": "pending",
            "not_ranked": "pending",
            "completed_with_warnings": "completed_with_warnings",
            "blocked_by_conflicts": "blocked",
            "blocked_by_quality": "blocked",
        }.get(value, value)

    def _safe_status(self, loader, fallback_status: str = "unavailable"):
        try:
            return loader()
        except Exception:
            return None, fallback_status, ()

    def _build_stage(
        self,
        *,
        name: str,
        display_name: str,
        status: str,
        available: bool,
        stale: bool,
        completed_at: str | None,
        summary: str,
        error: str | None = None,
        action_id: str | None = None,
    ) -> VideoPipelineStageStatus:
        return VideoPipelineStageStatus(
            name=name,
            display_name=display_name,
            status=status,
            available=available,
            stale=stale,
            completed_at=completed_at,
            summary=summary,
            error=error,
            action_id=action_id,
        )

    def get_video_pipeline_status(self, video_id: str) -> VideoPipelineStatus:
        video = self._require_video(video_id)
        warnings: list[str] = []
        stages: list[VideoPipelineStageStatus] = []

        inspection = self.media_service.get_video_inspection(video.id)
        inspection_status = inspection.status.value if inspection else "not_inspected"
        inspection_stale = bool(inspection.is_stale) if inspection else False
        inspection_available = bool(video.file_available)
        stages.append(
            self._build_stage(
                name="inspection",
                display_name="Inspeccion",
                status=self._status_label(inspection_status if inspection else ("available" if inspection_available else "blocked")),
                available=inspection_available or inspection is not None,
                stale=inspection_stale,
                completed_at=to_iso_z(inspection.inspection.inspected_at) if inspection and inspection.inspection else None,
                summary=inspection.status.value if inspection else ("Archivo disponible" if inspection_available else "Archivo faltante"),
                error=(inspection.errors[0] if inspection and inspection.errors else None),
                action_id="inspect_video" if inspection_available else None,
            )
        )
        audio = self.audio_service.get_prepared_audio(video.id)
        stages.append(
            self._build_stage(
                name="audio",
                display_name="Audio",
                status=self._status_label(audio.status.value if audio else ("available" if inspection and not inspection.is_stale and inspection.file_available else "pending")),
                available=bool(inspection and inspection.file_available),
                stale=bool(audio.is_stale) if audio else False,
                completed_at=to_iso_z(audio.prepared_audio.extraction_completed_at) if audio and audio.prepared_audio else None,
                summary=audio.status.value if audio else "Pendiente",
                error=(audio.errors[0] if audio and audio.errors else None),
                action_id="prepare_audio" if inspection and inspection.file_available else None,
            )
        )
        transcription = self.transcription_service.get_transcription(video.id)
        model_status = self.transcription_service.get_model_status(transcription.transcription.model_name if transcription.transcription else "small")
        transcription_available = bool(audio and audio.status.value == "completed")
        transcription_status = transcription.status.value if transcription else "not_transcribed"
        stages.append(
            self._build_stage(
                name="transcription",
                display_name="Transcripcion",
                status=self._status_label(transcription_status if transcription else ("available" if transcription_available else "pending")),
                available=transcription_available,
                stale=bool(transcription.is_stale) if transcription else False,
                completed_at=to_iso_z(transcription.transcription.completed_at) if transcription and transcription.transcription else None,
                summary=transcription.status.value if transcription else ("Modelo: " + model_status.status.value),
                error=(transcription.errors[0] if transcription and transcription.errors else None),
                action_id="transcribe_video" if transcription_available and model_status.status == TranscriptionModelStatus.INSTALLED else None,
            )
        )
        acoustic = self.acoustic_service.get_acoustic_analysis(video.id)
        acoustic_available = bool(transcription and transcription.status.value == "completed")
        stages.append(
            self._build_stage(
                name="acoustic",
                display_name="Acustica",
                status=self._status_label(acoustic.status.value if acoustic else ("available" if acoustic_available else "pending")),
                available=acoustic_available,
                stale=bool(acoustic.is_stale) if acoustic else False,
                completed_at=to_iso_z(acoustic.analysis.completed_at) if acoustic and acoustic.analysis else None,
                summary=acoustic.status.value if acoustic else "Pendiente",
                error=(acoustic.errors[0] if acoustic and acoustic.errors else None),
                action_id="analyze_acoustics" if acoustic_available else None,
            )
        )
        visual = self.visual_service.get_visual_analysis(video.id)
        visual_available = bool(inspection and inspection.status.value == "completed")
        stages.append(
            self._build_stage(
                name="visual",
                display_name="Visual",
                status=self._status_label(visual.status.value if visual else ("available" if visual_available else "pending")),
                available=visual_available,
                stale=bool(visual.is_stale) if visual else False,
                completed_at=to_iso_z(visual.analysis.completed_at) if visual and visual.analysis else None,
                summary=visual.status.value if visual else "Pendiente",
                error=(visual.errors[0] if visual and visual.errors else None),
                action_id="analyze_visuals" if visual_available else None,
            )
        )
        multimodal = self.multimodal_service.get_multimodal_analysis(video.id)
        multimodal_available = bool(acoustic and acoustic.status.value == "completed" and visual and visual.status.value == "completed")
        stages.append(
            self._build_stage(
                name="multimodal",
                display_name="Multimodal",
                status=self._status_label(multimodal.status.value if multimodal else ("available" if multimodal_available else "pending")),
                available=multimodal_available,
                stale=bool(multimodal.is_stale) if multimodal else False,
                completed_at=to_iso_z(multimodal.analysis.completed_at) if multimodal and multimodal.analysis else None,
                summary=multimodal.status.value if multimodal else "Pendiente",
                error=(multimodal.errors[0] if multimodal and multimodal.errors else None),
                action_id="analyze_multimodal" if multimodal_available else None,
            )
        )
        ranking = self.clip_service.get_ranking_run(video.id)
        ranking_available = bool(multimodal and multimodal.analysis is not None)
        stages.append(
            self._build_stage(
                name="ranking",
                display_name="Ranking",
                status=self._status_label(ranking.status.value if ranking else ("available" if ranking_available else "pending")),
                available=ranking_available,
                stale=bool(ranking.is_stale) if ranking else False,
                completed_at=to_iso_z(ranking.run.completed_at) if ranking and ranking.run and ranking.run.completed_at else None,
                summary=ranking.status.value if ranking else "Pendiente",
                error=(ranking.errors[0] if ranking and ranking.errors else None),
                action_id="rank_clip_candidates" if ranking_available else None,
            )
        )

        current_stage = next((stage.name for stage in stages if stage.status not in {"completed", "completed_with_warnings"}), stages[-1].name if stages else "inspection")
        progress_weights = {
            "inspection": 0.10,
            "audio": 0.12,
            "transcription": 0.20,
            "acoustic": 0.13,
            "visual": 0.13,
            "multimodal": 0.17,
            "ranking": 0.15,
        }
        completed = 0.0
        for stage in stages:
            completed += progress_weights.get(stage.name, 0.0) if stage.status in {"completed", "completed_with_warnings", "stale"} else 0.0
            if stage.status == "stale":
                warnings.append(f"{stage.display_name} desactualizado")

        blocked_reason = None
        recommended_action = "Revisar clips"
        overall_status = "pending"
        if not video.file_available:
            blocked_reason = "El archivo de video no esta disponible."
            recommended_action = "Importar o restablecer el archivo de video"
            overall_status = "blocked"
        elif stages[0].status in {"pending", "available", "blocked", "unavailable"}:
            recommended_action = "Inspeccionar video"
            overall_status = "available"
        elif stages[1].status in {"pending", "available", "blocked", "unavailable"}:
            recommended_action = "Preparar audio"
        elif stages[2].status in {"pending", "available", "blocked", "unavailable"}:
            if model_status.status == TranscriptionModelStatus.INSTALLED:
                recommended_action = "Transcribir"
            else:
                recommended_action = "Instalar o verificar el modelo de transcripcion"
                blocked_reason = model_status.notes or "El modelo de transcripcion no esta instalado."
                overall_status = "blocked"
        elif stages[3].status in {"pending", "available"}:
            recommended_action = "Ejecutar analisis"
        elif stages[4].status in {"pending", "available"}:
            recommended_action = "Ejecutar analisis"
        elif stages[5].status in {"pending", "available"}:
            recommended_action = "Ejecutar analisis multimodal"
        elif stages[6].status in {"pending", "available"}:
            recommended_action = "Generar candidatos"
        else:
            render_recommended = bool(ranking and ranking.run and ranking.run.selected_count > 0)
            recommended_action = "Renderizar clips aprobados" if render_recommended else "Revisar clips"
            if self.personalization_service is not None:
                try:
                    project = self.catalog_service.get_project(video.project_id)
                    readiness = self.personalization_service.get_creator_readiness(project.creator_id)
                    if readiness.readiness_status in {
                        PersonalizationReadinessStatus.READY_FOR_BASELINE,
                        PersonalizationReadinessStatus.READY_FOR_EVALUATION,
                        PersonalizationReadinessStatus.READY_FOR_PERSONALIZED_TRAINING,
                    }:
                        recommended_action = "Crear snapshot de personalizacion"
                    elif readiness.readiness_status in {
                        PersonalizationReadinessStatus.COLLECTING_FEEDBACK,
                        PersonalizationReadinessStatus.LIMITED,
                    } and not render_recommended:
                        recommended_action = "Continua revisando candidatos para personalizar"
                    if readiness.recommendations:
                        warnings.extend(readiness.recommendations)
                except Exception:
                    pass

        if any(stage.status == "failed" for stage in stages):
            overall_status = "failed"
        elif any(stage.status == "blocked" for stage in stages):
            overall_status = "blocked"
        elif any(stage.status == "stale" for stage in stages):
            overall_status = "stale"
        elif all(stage.status == "completed" for stage in stages):
            overall_status = "completed"
        elif any(stage.status == "completed_with_warnings" for stage in stages):
            overall_status = "completed_with_warnings"

        if blocked_reason is None and any(stage.status in {"blocked", "unavailable"} for stage in stages):
            blocked_reason = next((stage.error or stage.summary for stage in stages if stage.status in {"blocked", "unavailable"}), None)

        return VideoPipelineStatus(
            video_id=video.id,
            current_stage=current_stage,
            recommended_action=recommended_action,
            overall_status=overall_status,
            progress_percent=round(min(100.0, max(0.0, completed * 100.0)), 1),
            blocked_reason=blocked_reason,
            warnings=tuple(dict.fromkeys(warnings)),
            stages=tuple(stages),
        )

    def _transcription_options(self, device: str = "auto", profile: str = "balanced") -> TranscriptionOptions:
        return TranscriptionOptions(profile=profile, device=device, model_name="small")

    def run_next_step(
        self,
        video_id: str,
        *,
        transcription_device: str = "auto",
        transcription_profile: str = "balanced",
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> VideoWorkflowStepResult:
        status = self.get_video_pipeline_status(video_id)
        self._require_video(video_id)
        if status.current_stage == "inspection":
            self.media_service.inspect_video(video_id, force=False)
            return VideoWorkflowStepResult("inspection", "completed", "Video inspeccionado", to_iso_z(datetime.now(timezone.utc)))
        if status.current_stage == "audio":
            self.audio_service.prepare_audio(video_id, force=False)
            return VideoWorkflowStepResult("audio", "completed", "Audio preparado", to_iso_z(datetime.now(timezone.utc)))
        if status.current_stage == "transcription":
            self.transcription_service.transcribe_video(video_id, self._transcription_options(transcription_device, transcription_profile), progress_callback=progress_callback)
            return VideoWorkflowStepResult("transcription", "completed", "Transcripcion completada", to_iso_z(datetime.now(timezone.utc)))
        if status.current_stage == "acoustic":
            self.acoustic_service.analyze_acoustics(video_id, force=False, progress_callback=progress_callback)
            return VideoWorkflowStepResult("acoustic", "completed", "Analisis acustico completado", to_iso_z(datetime.now(timezone.utc)))
        if status.current_stage == "visual":
            self.visual_service.analyze_visuals(video_id, force=False, progress_callback=progress_callback)
            return VideoWorkflowStepResult("visual", "completed", "Analisis visual completado", to_iso_z(datetime.now(timezone.utc)))
        if status.current_stage == "multimodal":
            self.multimodal_service.analyze_multimodal(video_id, force=False, progress_callback=progress_callback)
            return VideoWorkflowStepResult("multimodal", "completed", "Analisis multimodal completado", to_iso_z(datetime.now(timezone.utc)))
        self.clip_service.rank_clip_candidates(video_id, force=False, progress_callback=progress_callback)
        return VideoWorkflowStepResult("ranking", "completed", "Ranking de clips completado", to_iso_z(datetime.now(timezone.utc)))

    def run_until_ranking(
        self,
        video_id: str,
        *,
        transcription_device: str = "auto",
        transcription_profile: str = "balanced",
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> list[VideoWorkflowStepResult]:
        results: list[VideoWorkflowStepResult] = []
        for step_name in ("inspection", "audio", "transcription", "acoustic", "visual", "multimodal", "ranking"):
            status = self.get_video_pipeline_status(video_id)
            if status.current_stage not in {step_name, "inspection", "audio", "transcription", "acoustic", "visual", "multimodal", "ranking"}:
                break
            result = self.run_next_step(
                video_id,
                transcription_device=transcription_device,
                transcription_profile=transcription_profile,
                progress_callback=progress_callback,
            )
            results.append(result)
            if result.stage_name == "ranking":
                break
        return results

    def run_stage_group(
        self,
        video_id: str,
        group_name: str,
        *,
        transcription_device: str = "auto",
        transcription_profile: str = "balanced",
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> list[VideoWorkflowStepResult]:
        group_order = {
            "importacion": ("inspection",),
            "preparacion": ("inspection", "audio"),
            "comprension": ("inspection", "audio", "transcription", "acoustic", "visual", "multimodal"),
            "seleccion": ("inspection", "audio", "transcription", "acoustic", "visual", "multimodal", "ranking"),
        }
        stages = group_order.get(group_name, group_order["seleccion"])
        results: list[VideoWorkflowStepResult] = []
        for expected_stage in stages:
            status = self.get_video_pipeline_status(video_id)
            if status.current_stage != expected_stage:
                continue
            result = self.run_next_step(
                video_id,
                transcription_device=transcription_device,
                transcription_profile=transcription_profile,
                progress_callback=progress_callback,
            )
            results.append(result)
            if result.stage_name == stages[-1]:
                break
        return results

    def retry_stage(
        self,
        video_id: str,
        stage_name: str,
        *,
        transcription_device: str = "auto",
        transcription_profile: str = "balanced",
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> VideoWorkflowStepResult:
        if stage_name == "inspection":
            self.media_service.inspect_video(video_id, force=True)
            return VideoWorkflowStepResult("inspection", "completed", "Inspeccion rehecha", to_iso_z(datetime.now(timezone.utc)))
        if stage_name == "audio":
            self.audio_service.prepare_audio(video_id, force=True)
            return VideoWorkflowStepResult("audio", "completed", "Audio regenerado", to_iso_z(datetime.now(timezone.utc)))
        if stage_name == "transcription":
            self.transcription_service.transcribe_video(video_id, self._transcription_options(transcription_device, transcription_profile), progress_callback=progress_callback)
            return VideoWorkflowStepResult("transcription", "completed", "Transcripcion rehecha", to_iso_z(datetime.now(timezone.utc)))
        if stage_name == "acoustic":
            self.acoustic_service.analyze_acoustics(video_id, force=True, progress_callback=progress_callback)
            return VideoWorkflowStepResult("acoustic", "completed", "Analisis acustico rehecho", to_iso_z(datetime.now(timezone.utc)))
        if stage_name == "visual":
            self.visual_service.analyze_visuals(video_id, force=True, progress_callback=progress_callback)
            return VideoWorkflowStepResult("visual", "completed", "Analisis visual rehecho", to_iso_z(datetime.now(timezone.utc)))
        if stage_name == "multimodal":
            self.multimodal_service.analyze_multimodal(video_id, force=True, progress_callback=progress_callback)
            return VideoWorkflowStepResult("multimodal", "completed", "Analisis multimodal rehecho", to_iso_z(datetime.now(timezone.utc)))
        self.clip_service.rank_clip_candidates(video_id, force=True, progress_callback=progress_callback)
        return VideoWorkflowStepResult("ranking", "completed", "Ranking rehecho", to_iso_z(datetime.now(timezone.utc)))
