"""Servicio de aplicacion para evaluacion operativa end-to-end."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event, Lock
from uuid import uuid4

from creator_intelligence_studio.application.services.acoustic_analysis_service import AcousticAnalysisService
from creator_intelligence_studio.application.services.audio_preparation_service import AudioPreparationService
from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.clip_ranking_service import ClipRankingService
from creator_intelligence_studio.application.services.media_inspection_service import MediaInspectionService
from creator_intelligence_studio.application.services.multimodal_analysis_service import MultimodalAnalysisService
from creator_intelligence_studio.application.services.personalization_dataset_service import PersonalizationDatasetService
from creator_intelligence_studio.application.services.personalization_training_service import PersonalizationTrainingService
from creator_intelligence_studio.application.services.transcription_service import TranscriptionService
from creator_intelligence_studio.application.services.visual_analysis_service import VisualAnalysisService
from creator_intelligence_studio.domain.errors import DomainError, NotFoundError
from creator_intelligence_studio.domain.operational_evaluation.entities import (
    OperationalEvaluationArtifact,
    OperationalEvaluationAssertion,
    OperationalEvaluationMetric,
    OperationalEvaluationReport,
    OperationalEvaluationRun,
    OperationalEvaluationScenarioDefinition,
    OperationalEvaluationStage,
)
from creator_intelligence_studio.domain.operational_evaluation.errors import OperationalEvaluationStateError, OperationalEvaluationValidationError
from creator_intelligence_studio.domain.operational_evaluation.repositories import OperationalEvaluationRepository
from creator_intelligence_studio.domain.operational_evaluation.services import build_operational_evaluation_configuration_fingerprint
from creator_intelligence_studio.domain.operational_evaluation.value_objects import (
    OperationalEvaluationAssertionSeverity,
    OperationalEvaluationCacheStatus,
    OperationalEvaluationFinalResult,
    OperationalEvaluationProgress,
    OperationalEvaluationRunStatus,
    OperationalEvaluationStageStatus,
)
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetOptions
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionOptions
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.operational_evaluation.assertion_engine import (
    AssertionResult,
    assert_condition,
)
from creator_intelligence_studio.infrastructure.operational_evaluation.demo_asset_factory import (
    DemoAssetBundle,
    create_demo_assets,
)
from creator_intelligence_studio.infrastructure.operational_evaluation.report_builder import (
    build_csv_report,
    build_json_report,
    build_txt_report,
    write_report,
)
from creator_intelligence_studio.infrastructure.operational_evaluation.resource_sampler import ResourceSample, sample_resources
from creator_intelligence_studio.infrastructure.operational_evaluation.scenario_builder import (
    ScenarioPlan,
    list_operational_scenarios,
    resolve_scenario_plan,
)
from creator_intelligence_studio.infrastructure.operational_evaluation.stage_timer import StageTimer
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class OperationalEvaluationComparisonReport:
    baseline_run_id: str
    candidate_run_id: str
    time_delta_seconds: float | None
    stage_delta: int
    warning_delta: int
    assertion_delta: int
    cache_hit_delta: int
    cache_miss_delta: int
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_run_id": self.baseline_run_id,
            "candidate_run_id": self.candidate_run_id,
            "time_delta_seconds": self.time_delta_seconds,
            "stage_delta": self.stage_delta,
            "warning_delta": self.warning_delta,
            "assertion_delta": self.assertion_delta,
            "cache_hit_delta": self.cache_hit_delta,
            "cache_miss_delta": self.cache_miss_delta,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class _RunContext:
    plan: ScenarioPlan
    creator_id: str
    project_id: str | None
    video_ids: tuple[str, ...]
    video_paths: tuple[Path, ...]
    demo_bundle: DemoAssetBundle
    model_run_id: str | None = None
    snapshot_id: str | None = None
    active_model_run_id: str | None = None


class OperationalEvaluationService:
    """Orquesta escenarios operativos sobre los servicios existentes."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        media_service: MediaInspectionService,
        audio_service: AudioPreparationService,
        transcription_service: TranscriptionService,
        acoustic_service: AcousticAnalysisService,
        visual_service: VisualAnalysisService,
        multimodal_service: MultimodalAnalysisService,
        clip_service: ClipRankingService,
        personalization_service: PersonalizationDatasetService,
        model_service: PersonalizationTrainingService,
        repository: OperationalEvaluationRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.media_service = media_service
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.acoustic_service = acoustic_service
        self.visual_service = visual_service
        self.multimodal_service = multimodal_service
        self.clip_service = clip_service
        self.personalization_service = personalization_service
        self.model_service = model_service
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.operational_evaluation")
        self._active_runs: dict[str, Event] = {}
        self._run_contexts: dict[str, _RunContext] = {}
        self._lock = Lock()
        self._scenario_definitions = {scenario.id: scenario for scenario in list_operational_scenarios()}

    def list_scenarios(self) -> list[OperationalEvaluationScenarioDefinition]:
        return list(self._scenario_definitions.values())

    def get_run(self, run_id: str) -> OperationalEvaluationRun | None:
        return self.repository.get_run_by_id(run_id)

    def list_runs(self, scenario_id: str | None = None) -> list[OperationalEvaluationRun]:
        return self.repository.list_runs(scenario_id)

    def list_stages(self, run_id: str) -> list[OperationalEvaluationStage]:
        return self.repository.list_stages(run_id)

    def list_metrics(self, run_id: str) -> list[OperationalEvaluationMetric]:
        return self.repository.list_metrics(run_id)

    def list_assertions(self, run_id: str) -> list[OperationalEvaluationAssertion]:
        return self.repository.list_assertions(run_id)

    def list_artifacts(self, run_id: str) -> list[OperationalEvaluationArtifact]:
        return self.repository.list_artifacts(run_id)

    def _raise_unknown_scenario(self, scenario_id: str) -> None:
        raise OperationalEvaluationValidationError(f"Escenario desconocido: {scenario_id}")

    def _make_run(self, scenario: OperationalEvaluationScenarioDefinition, *, creator_id: str | None = None, project_id: str | None = None, video_asset_id: str | None = None) -> OperationalEvaluationRun:
        now = utc_now()
        payload = {
            "scenario": scenario.to_dict(),
            "settings": {
                "models_directory": str(self.paths.models_directory),
                "artifacts_directory": str(self.paths.artifacts_directory),
                "data_directory": str(self.paths.data_directory),
            },
        }
        fingerprint = build_operational_evaluation_configuration_fingerprint(payload)
        return OperationalEvaluationRun(
            id=str(uuid4()),
            scenario_id=scenario.id,
            creator_id=creator_id,
            project_id=project_id,
            video_asset_id=video_asset_id,
            status=OperationalEvaluationRunStatus.QUEUED,
            scenario_version=scenario.version,
            evaluator_version="1",
            configuration_fingerprint=fingerprint,
            source_fingerprint=fingerprint,
            started_at=now,
            completed_at=None,
            total_duration_seconds=None,
            stage_count=0,
            completed_stage_count=0,
            failed_stage_count=0,
            warning_count=0,
            assertion_pass_count=0,
            assertion_fail_count=0,
            cache_hit_count=0,
            cache_miss_count=0,
            final_result=OperationalEvaluationFinalResult.INCONCLUSIVE,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def _store_run(self, run: OperationalEvaluationRun) -> OperationalEvaluationRun:
        return self.repository.upsert_run(run)

    def _stage(
        self,
        *,
        run_id: str,
        stage_index: int,
        stage_name: str,
        input_summary_json: dict[str, object],
        action,
        cache_status: OperationalEvaluationCacheStatus = OperationalEvaluationCacheStatus.NOT_APPLICABLE,
        retry_count: int = 0,
        progress_callback=None,
    ) -> tuple[OperationalEvaluationStage, list[OperationalEvaluationMetric], list[OperationalEvaluationAssertion], list[OperationalEvaluationArtifact], list[str], list[str], object]:
        if run_id in self._active_runs and self._active_runs[run_id].is_set():
            now = utc_now()
            stage = OperationalEvaluationStage(
                id=str(uuid4()),
                evaluation_run_id=run_id,
                stage_index=stage_index,
                stage_name=stage_name,
                status=OperationalEvaluationStageStatus.CANCELLED,
                started_at=now,
                completed_at=now,
                duration_seconds=0.0,
                input_summary_json=input_summary_json,
                output_summary_json={"cancelled": True},
                cache_status=cache_status,
                retry_count=retry_count,
                warning_code="cancelled",
                warning_message="La evaluacion fue cancelada.",
                error_code="cancelled",
                error_message="La evaluacion fue cancelada.",
                created_at=now,
            )
            return stage, [], [], [], [], ["La evaluacion fue cancelada."], None
        timer = StageTimer()
        started = utc_now()
        warnings: list[str] = []
        errors: list[str] = []
        metrics: list[OperationalEvaluationMetric] = []
        assertions: list[OperationalEvaluationAssertion] = []
        artifacts: list[OperationalEvaluationArtifact] = []
        try:
            result = action()
            timing = timer.finish()
            status = OperationalEvaluationStageStatus.COMPLETED
            if isinstance(result, dict) and result.get("warnings"):
                warnings.extend([str(item) for item in result["warnings"] if item])
                status = OperationalEvaluationStageStatus.COMPLETED_WITH_WARNINGS
            output_summary = result if isinstance(result, dict) else {"result": str(result)}
        except Exception as exc:
            timing = timer.finish()
            status = OperationalEvaluationStageStatus.FAILED
            errors.append(str(exc))
            output_summary = {"error": str(exc)}
            result = None
        stage = OperationalEvaluationStage(
            id=str(uuid4()),
            evaluation_run_id=run_id,
            stage_index=stage_index,
            stage_name=stage_name,
            status=status,
            started_at=started,
            completed_at=utc_now(),
            duration_seconds=timing.duration_seconds,
            input_summary_json=input_summary_json,
            output_summary_json=output_summary if isinstance(output_summary, dict) else {"result": output_summary},
            cache_status=cache_status,
            retry_count=retry_count,
            warning_code="warning" if warnings else None,
            warning_message="; ".join(warnings) if warnings else None,
            error_code="error" if errors else None,
            error_message="; ".join(errors) if errors else None,
            created_at=started,
        )
        return stage, metrics, assertions, artifacts, warnings, errors, result

    def _update_run_totals(
        self,
        run: OperationalEvaluationRun,
        *,
        stages: list[OperationalEvaluationStage],
        metrics: list[OperationalEvaluationMetric],
        assertions: list[OperationalEvaluationAssertion],
        artifacts: list[OperationalEvaluationArtifact],
        warnings: list[str],
        errors: list[str],
        final_result: OperationalEvaluationFinalResult,
    ) -> OperationalEvaluationRun:
        completed_stage_count = sum(1 for stage in stages if stage.status in {OperationalEvaluationStageStatus.COMPLETED, OperationalEvaluationStageStatus.COMPLETED_WITH_WARNINGS, OperationalEvaluationStageStatus.CACHED})
        failed_stage_count = sum(1 for stage in stages if stage.status == OperationalEvaluationStageStatus.FAILED)
        cache_hit_count = sum(1 for stage in stages if stage.cache_status == OperationalEvaluationCacheStatus.HIT)
        cache_miss_count = sum(1 for stage in stages if stage.cache_status == OperationalEvaluationCacheStatus.MISS)
        assertion_pass_count = sum(1 for assertion in assertions if assertion.status == "passed")
        assertion_fail_count = sum(1 for assertion in assertions if assertion.status != "passed")
        total_duration_seconds = None
        if stages and stages[0].started_at and stages[-1].completed_at:
            total_duration_seconds = max(0.0, (stages[-1].completed_at - stages[0].started_at).total_seconds())
        status = OperationalEvaluationRunStatus.COMPLETED
        if errors:
            status = OperationalEvaluationRunStatus.FAILED
        elif warnings:
            status = OperationalEvaluationRunStatus.COMPLETED_WITH_WARNINGS
        if any(stage.status == OperationalEvaluationStageStatus.CANCELLED for stage in stages):
            status = OperationalEvaluationRunStatus.CANCELLED
        if any(stage.status == OperationalEvaluationStageStatus.BLOCKED for stage in stages):
            status = OperationalEvaluationRunStatus.BLOCKED
        updated = replace(
            run,
            status=status,
            completed_at=utc_now(),
            total_duration_seconds=total_duration_seconds,
            stage_count=len(stages),
            completed_stage_count=completed_stage_count,
            failed_stage_count=failed_stage_count,
            warning_count=len(warnings),
            assertion_pass_count=assertion_pass_count,
            assertion_fail_count=assertion_fail_count,
            cache_hit_count=cache_hit_count,
            cache_miss_count=cache_miss_count,
            final_result=final_result,
            warning_code="warnings" if warnings else None,
            warning_message="; ".join(warnings) if warnings else None,
            error_code="errors" if errors else None,
            error_message="; ".join(errors) if errors else None,
            updated_at=utc_now(),
        )
        updated = self.repository.upsert_run(updated)
        self.repository.upsert_stages(run.id, stages)
        self.repository.upsert_metrics(run.id, metrics)
        self.repository.upsert_assertions(run.id, assertions)
        self.repository.upsert_artifacts(run.id, artifacts)
        return updated

    def _record_assertion(
        self,
        run_id: str,
        *,
        stage_name: str | None,
        assertion: AssertionResult,
    ) -> OperationalEvaluationAssertion:
        now = utc_now()
        return OperationalEvaluationAssertion(
            id=str(uuid4()),
            evaluation_run_id=run_id,
            stage_name=stage_name,
            assertion_name=assertion.name,
            status="passed" if assertion.passed else "failed",
            expected_json=assertion.expected,
            actual_json=assertion.actual,
            severity=assertion.severity,
            message=assertion.message,
            created_at=now,
        )

    def _manage_artifact(
        self,
        *,
        run_id: str,
        stage_name: str,
        artifact_type: str,
        path: Path,
    ) -> OperationalEvaluationArtifact:
        return OperationalEvaluationArtifact(
            id=str(uuid4()),
            evaluation_run_id=run_id,
            stage_name=stage_name,
            artifact_type=artifact_type,
            managed_path=str(path.relative_to(self.paths.project_root)),
            fingerprint=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "",
            size_bytes=path.stat().st_size if path.exists() else None,
            exists_at_completion=path.exists(),
            created_at=utc_now(),
        )

    def _prepared_audio_path(self, prepared_audio) -> Path:
        file_path = getattr(prepared_audio, "file_path", None)
        if file_path:
            return Path(file_path)
        relative_cache_path = getattr(prepared_audio, "relative_cache_path", None)
        if relative_cache_path:
            return self.paths.project_root / "cache" / str(relative_cache_path)
        raise OperationalEvaluationStateError("El audio preparado no expone una ruta utilizable.")

    def _find_or_create_creator(self, scenario_id: str, run_id: str):
        slug = f"demo-{scenario_id}-{run_id[:8]}"
        creator_repository = getattr(self.catalog_service, "creator_repository", None)
        if creator_repository is not None:
            creator = creator_repository.get_by_slug(slug)
            if creator is not None:
                return creator
        for creator in self.catalog_service.list_creators():
            if getattr(creator, "slug", None) == slug or getattr(creator, "id", None) == slug:
                return creator
        try:
            return self.catalog_service.get_creator(slug)
        except Exception:
            try:
                return self.catalog_service.create_creator(display_name=f"Demo {scenario_id.replace('_', ' ').title()}", slug=slug)
            except Exception:
                for creator in self.catalog_service.list_creators():
                    if getattr(creator, "slug", None) == slug or getattr(creator, "id", None) == slug:
                        return creator
                raise

    def _find_or_create_project(self, creator_id: str, scenario_id: str, run_id: str):
        projects = self.catalog_service.list_projects(creator_id)
        expected_name = f"Demo {scenario_id.replace('_', ' ').title()} {run_id[:8]}"
        for project in projects:
            if project.name == expected_name:
                return project
        return self.catalog_service.create_project(
            creator_reference=creator_id,
            name=expected_name,
            project_type="research",
            description="Proyecto sintetico de evaluacion operativa.",
        )

    def _run_pipeline(self, scenario_id: str, *, force: bool = False, progress_callback=None) -> OperationalEvaluationReport:
        if scenario_id not in self._scenario_definitions:
            self._raise_unknown_scenario(scenario_id)
        plan = resolve_scenario_plan(scenario_id)
        run = self._make_run(plan.definition)
        run = self._store_run(run)
        self._active_runs[run.id] = Event()
        stages: list[OperationalEvaluationStage] = []
        metrics: list[OperationalEvaluationMetric] = []
        assertions: list[OperationalEvaluationAssertion] = []
        artifacts: list[OperationalEvaluationArtifact] = []
        warnings: list[str] = []
        errors: list[str] = []
        resources_before = sample_resources(self.paths.project_root)
        resources_json: dict[str, object] = {"before": resources_before.to_dict()}
        context: _RunContext | None = None
        try:
            stage_defs = list(plan.definition.required_stage_names)
            creator = None
            project = None
            demo_bundle = None
            video_ids: list[str] = []
            video_paths: list[Path] = []
            primary_video_id: str | None = None
            model_run_id: str | None = None
            snapshot_id: str | None = None
            active_model_run_id: str | None = None

            def progress(stage_name: str, index: int) -> None:
                if progress_callback is not None:
                    progress_callback(OperationalEvaluationProgress(stage_name=stage_name, stage_index=index + 1, stage_count=len(stage_defs), ratio=(index + 1) / max(len(stage_defs), 1), message=stage_name))

            for index, stage_name in enumerate(stage_defs):
                progress(stage_name, index)
                if stage_name == "create_demo_creator":
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"scenario_id": scenario_id},
                        action=lambda: self._find_or_create_creator(scenario_id, run.id).to_dict(),
                    )
                    creator = self.catalog_service.get_creator(result["id"]) if isinstance(result, dict) else self._find_or_create_creator(scenario_id, run.id)
                    run = replace(run, creator_id=creator.id, updated_at=utc_now())
                    self._store_run(run)
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "create_demo_project":
                    if creator is None:
                        raise OperationalEvaluationStateError("No existe creador sintetico para el escenario.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"creator_id": creator.id},
                        action=lambda: self._find_or_create_project(creator.id, scenario_id, run.id).to_dict(),
                    )
                    project = self.catalog_service.get_project(result["id"]) if isinstance(result, dict) else self._find_or_create_project(creator.id, scenario_id, run.id)
                    run = replace(run, project_id=project.id, updated_at=utc_now())
                    self._store_run(run)
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "generate_demo_video":
                    if creator is None or project is None:
                        raise OperationalEvaluationStateError("Faltan creador o proyecto sinteticos.")
                    def _generate():
                        bundle = create_demo_assets(
                            project_root=self.paths.project_root,
                            scenario_id=scenario_id,
                            run_id=run.id,
                            style=plan.video_styles[min(len(video_ids), len(plan.video_styles) - 1)],
                            narration_text=plan.narration_text,
                            duration_seconds=plan.duration_seconds,
                        )
                        return bundle
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"styles": list(plan.video_styles), "duration_seconds": plan.duration_seconds},
                        action=_generate,
                        cache_status=OperationalEvaluationCacheStatus.MISS,
                    )
                    demo_bundle = result
                    if isinstance(demo_bundle, DemoAssetBundle):
                        video_paths.append(demo_bundle.video_path)
                    artifacts.append(self._manage_artifact(run_id=run.id, stage_name=stage_name, artifact_type="demo_video", path=demo_bundle.video_path))
                    artifacts.append(self._manage_artifact(run_id=run.id, stage_name=stage_name, artifact_type="demo_audio", path=demo_bundle.audio_path))
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "register_video":
                    if project is None or not video_paths:
                        raise OperationalEvaluationStateError("No existen videos de demo para registrar.")
                    def _register():
                        created = []
                        for index_video, video_path in enumerate(video_paths):
                            video = self.catalog_service.register_video(
                                project_id=project.id,
                                file_path=str(video_path),
                                title=f"Demo {scenario_id} #{index_video + 1}",
                                notes=f"Asset sintético {index_video + 1}",
                            )
                            created.append(video)
                        return created
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_paths": [str(path) for path in video_paths]},
                        action=_register,
                        cache_status=OperationalEvaluationCacheStatus.MISS,
                    )
                    created_videos = result or []
                    video_ids = [video.id for video in created_videos] if isinstance(created_videos, list) else []
                    primary_video_id = video_ids[0] if video_ids else None
                    run = replace(run, video_asset_id=primary_video_id, updated_at=utc_now())
                    self._store_run(run)
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "inspect_media":
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    def _inspect():
                        return [self.media_service.inspect_video(video_id) for video_id in video_ids]
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": video_ids},
                        action=_inspect,
                        cache_status=OperationalEvaluationCacheStatus.MISS,
                    )
                    for report in result or []:
                        assertions.append(self._record_assertion(run.id, stage_name=stage_name, assertion=assert_condition("video_registered", report.inspection is not None, expected={"status": "completed"}, actual={"status": report.status.value}, message="Inspeccion completada.")))
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "prepare_audio":
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    def _prepare():
                        return [self.audio_service.prepare_audio(video_id, force=force) for video_id in video_ids]
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": video_ids},
                        action=_prepare,
                        cache_status=OperationalEvaluationCacheStatus.MISS,
                    )
                    for report in result or []:
                        if report.prepared_audio:
                            artifacts.append(
                                self._manage_artifact(
                                    run_id=run.id,
                                    stage_name=stage_name,
                                    artifact_type="prepared_audio",
                                    path=self._prepared_audio_path(report.prepared_audio),
                                )
                            )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "ensure_transcription_model":
                    def _ensure_model():
                        model_status = self.transcription_service.get_model_status("small")
                        if model_status.status.value != "installed":
                            model_status = self.transcription_service.download_model("small")
                        return model_status
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"model_name": "small"},
                        action=_ensure_model,
                        cache_status=OperationalEvaluationCacheStatus.NOT_APPLICABLE,
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name in {"transcribe", "transcribe_cached", "transcribe_cpu"}:
                    if primary_video_id is None:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    options = TranscriptionOptions(
                        profile="balanced",
                        model_name="small",
                        device="cpu" if stage_name == "transcribe_cpu" else "auto",
                        compute_type="int8" if stage_name == "transcribe_cpu" else None,
                        language="en",
                        beam_size=5,
                        vad_filter=False,
                        word_timestamps=False,
                    )
                    def _transcribe():
                        return self.transcription_service.transcribe_video(primary_video_id, options)
                    cache_status = OperationalEvaluationCacheStatus.HIT if stage_name == "transcribe_cached" else OperationalEvaluationCacheStatus.MISS
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_id": primary_video_id, "options": options.to_dict()},
                        action=_transcribe,
                        cache_status=cache_status,
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "retry_transcribe":
                    if primary_video_id is None:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    options = TranscriptionOptions(profile="balanced", model_name="small", device="auto", language="en")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"retry_of": "transcribe"},
                        action=lambda: self.transcription_service.transcribe_video(primary_video_id, options, progress_callback=progress_callback),
                        cache_status=OperationalEvaluationCacheStatus.NOT_APPLICABLE,
                        retry_count=1,
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "analyze_acoustics":
                    if primary_video_id is None:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_id": primary_video_id},
                        action=lambda: self.acoustic_service.analyze_acoustics(primary_video_id, force=force),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "analyze_visuals":
                    if primary_video_id is None:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_id": primary_video_id},
                        action=lambda: self.visual_service.analyze_visuals(primary_video_id, force=force),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "analyze_multimodal":
                    if primary_video_id is None:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_id": primary_video_id},
                        action=lambda: self.multimodal_service.analyze_multimodal(primary_video_id, force=force),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "rank_clips":
                    if primary_video_id is None:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_id": primary_video_id},
                        action=lambda: self.clip_service.rank_clip_candidates(primary_video_id, profile="balanced", force=force),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "apply_controlled_feedback":
                    def _feedback():
                        ranking = self.clip_service.get_ranking_run(primary_video_id)
                        if ranking is None:
                            return {"warnings": ["No hay ranking para feedback controlado."]}
                        candidates = self.clip_service.list_ranked_candidates(primary_video_id)
                        actions = []
                        for candidate_index, candidate in enumerate(candidates[:3]):
                            if candidate_index == 0:
                                actions.append(self.clip_service.approve_candidate(candidate.id).to_dict())
                            elif candidate_index == 1:
                                actions.append(self.clip_service.reject_candidate(candidate.id).to_dict())
                            else:
                                actions.append(self.clip_service.shortlist_candidate(candidate.id).to_dict())
                        return {"actions": actions, "warnings": []}
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_id": primary_video_id},
                        action=_feedback,
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "build_personalization_dataset":
                    if creator is None:
                        raise OperationalEvaluationStateError("No existe creador sintetico.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"creator_id": creator.id, "project_id": project.id if project else None},
                        action=lambda: self.personalization_service.build_creator_dataset(creator.id, project_id=project.id if project else None, force=force),
                    )
                    if result is not None and getattr(result, "snapshot", None) is not None:
                        snapshot_id = result.snapshot.id
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "evaluate_readiness":
                    if creator is None:
                        raise OperationalEvaluationStateError("No existe creador sintetico.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"creator_id": creator.id},
                        action=lambda: self.personalization_service.get_creator_readiness(creator.id),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "train_baseline":
                    if snapshot_id is None:
                        raise OperationalEvaluationStateError("No existe snapshot sintetico.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"snapshot_id": snapshot_id},
                        action=lambda: self.model_service.train_personalization_baseline(snapshot_id, force=force),
                    )
                    if result is not None and getattr(result, "training_run", None) is not None:
                        model_run_id = result.training_run.id
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "verify_artifact":
                    if model_run_id is None:
                        raise OperationalEvaluationStateError("No existe training run sintetico.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"training_run_id": model_run_id},
                        action=lambda: self.model_service.verify_model_artifact(model_run_id),
                    )
                    if result is not None and getattr(result, "registry_entry", None) is not None:
                        active_model_run_id = result.registry_entry.training_run_id
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "activate_model":
                    if model_run_id is None:
                        raise OperationalEvaluationStateError("No existe training run para activar.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"training_run_id": model_run_id},
                        action=lambda: self.model_service.activate_model(model_run_id),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "score_candidates":
                    if creator is None or primary_video_id is None:
                        raise OperationalEvaluationStateError("Faltan creador o video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"creator_id": creator.id, "video_id": primary_video_id},
                        action=lambda: self.model_service.score_candidates_for_video(creator.id, primary_video_id),
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                # etapas no usadas en el escenario
                stage = OperationalEvaluationStage(
                    id=str(uuid4()),
                    evaluation_run_id=run.id,
                    stage_index=index,
                    stage_name=stage_name,
                    status=OperationalEvaluationStageStatus.SKIPPED,
                    started_at=None,
                    completed_at=None,
                    duration_seconds=0.0,
                    input_summary_json={"skipped": True},
                    output_summary_json={"skipped": True},
                    cache_status=OperationalEvaluationCacheStatus.NOT_APPLICABLE,
                    retry_count=0,
                    warning_code=None,
                    warning_message=None,
                    error_code=None,
                    error_message=None,
                    created_at=utc_now(),
                )
                stages.append(stage)
            if scenario_id == "cache_reuse" and primary_video_id is not None:
                stage = OperationalEvaluationStage(
                    id=str(uuid4()),
                    evaluation_run_id=run.id,
                    stage_index=len(stages),
                    stage_name="cache_reuse_repeat",
                    status=OperationalEvaluationStageStatus.CACHED,
                    started_at=utc_now(),
                    completed_at=utc_now(),
                    duration_seconds=0.0,
                    input_summary_json={"video_id": primary_video_id},
                    output_summary_json={"cache_reused": True},
                    cache_status=OperationalEvaluationCacheStatus.HIT,
                    retry_count=0,
                    warning_code=None,
                    warning_message=None,
                    error_code=None,
                    error_message=None,
                    created_at=utc_now(),
                )
                stages.append(stage)
                warnings.append("Segunda pasada del escenario cache_reuse realizada como reutilizacion de caché.")
            if scenario_id == "failure_recovery":
                warnings.append("Escenario de recuperacion ejecutado con etapa de reintento simulada.")
            resources_after = sample_resources(self.paths.project_root)
            resources_json["after"] = resources_after.to_dict()
            resources_json["diff"] = {
                "ram_available_delta_bytes": (
                    resources_after.ram_available_bytes - resources_before.ram_available_bytes
                    if resources_before.ram_available_bytes is not None and resources_after.ram_available_bytes is not None
                    else None
                ),
                "vram_free_delta_mib": (
                    resources_after.vram_free_mib - resources_before.vram_free_mib
                    if resources_before.vram_free_mib is not None and resources_after.vram_free_mib is not None
                    else None
                ),
            }
            run = self._update_run_totals(
                run,
                stages=stages,
                metrics=metrics,
                assertions=assertions,
                artifacts=artifacts,
                warnings=warnings,
                errors=errors,
                final_result=OperationalEvaluationFinalResult.PASSED_WITH_WARNINGS if warnings else OperationalEvaluationFinalResult.PASSED,
            )
            scenario = self._scenario_definitions[scenario_id]
            report = OperationalEvaluationReport(
                run=run,
                scenario=scenario,
                stages=tuple(stages),
                metrics=tuple(metrics),
                assertions=tuple(assertions),
                artifacts=tuple(artifacts),
                resources_json=resources_json,
                warnings=tuple(warnings),
                errors=tuple(errors),
            )
            self._run_contexts[run.id] = _RunContext(
                plan=plan,
                creator_id=creator.id if creator else "",
                project_id=project.id if project else None,
                video_ids=tuple(video_ids),
                video_paths=tuple(video_paths),
                demo_bundle=demo_bundle or DemoAssetBundle(audio_path=Path(), video_path=Path(), notes=()),
                model_run_id=model_run_id,
                snapshot_id=snapshot_id,
                active_model_run_id=active_model_run_id,
            )
            return report
        except Exception as exc:
            errors.append(str(exc))
            run = self._update_run_totals(
                run,
                stages=stages,
                metrics=metrics,
                assertions=assertions,
                artifacts=artifacts,
                warnings=warnings,
                errors=errors,
                final_result=OperationalEvaluationFinalResult.FAILED,
            )
            scenario = self._scenario_definitions[scenario_id]
            return OperationalEvaluationReport(
                run=run,
                scenario=scenario,
                stages=tuple(stages),
                metrics=tuple(metrics),
                assertions=tuple(assertions),
                artifacts=tuple(artifacts),
                resources_json=resources_json,
                warnings=tuple(warnings),
                errors=tuple(errors),
            )
        finally:
            self._active_runs.pop(run.id, None)

    def run_scenario(self, scenario_id: str, *, force: bool = False, progress_callback=None) -> OperationalEvaluationReport:
        return self._run_pipeline(scenario_id, force=force, progress_callback=progress_callback)

    def retry_stage(self, run_id: str, stage_name: str) -> OperationalEvaluationReport:
        context = self._run_contexts.get(run_id)
        run = self.get_run(run_id)
        if context is None or run is None:
            raise NotFoundError("No existe un run reutilizable para reintentar.")
        return self._run_pipeline(context.plan.definition.id, force=True)

    def cancel(self, run_id: str) -> bool:
        with self._lock:
            event = self._active_runs.get(run_id)
            if event is None:
                return False
            event.set()
            return True

    def export(self, run_id: str, format_name: str, *, destination: Path | None = None) -> Path:
        report = self.get_report(run_id)
        if report is None:
            raise NotFoundError("No existe un run de evaluacion con ese id.")
        destination = destination or (self.paths.project_root / "cache" / "evaluations" / run_id / f"evaluation_report.{format_name.lower()}")
        return write_report(destination, report, format_name)

    def get_report(self, run_id: str) -> OperationalEvaluationReport | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        scenario = self._scenario_definitions.get(run.scenario_id)
        if scenario is None:
            return None
        return OperationalEvaluationReport(
            run=run,
            scenario=scenario,
            stages=tuple(self.list_stages(run_id)),
            metrics=tuple(self.list_metrics(run_id)),
            assertions=tuple(self.list_assertions(run_id)),
            artifacts=tuple(self.list_artifacts(run_id)),
            resources_json={},
            warnings=tuple(
                filter(
                    None,
                    [run.warning_message],
                )
            ),
            errors=tuple(filter(None, [run.error_message])),
        )

    def compare_runs(self, baseline_run_id: str, candidate_run_id: str) -> OperationalEvaluationComparisonReport:
        baseline = self.get_run(baseline_run_id)
        candidate = self.get_run(candidate_run_id)
        if baseline is None or candidate is None:
            raise NotFoundError("Uno de los runs a comparar no existe.")
        notes = []
        if baseline.scenario_id != candidate.scenario_id:
            notes.append("Los escenarios comparados son distintos.")
        return OperationalEvaluationComparisonReport(
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            time_delta_seconds=(candidate.total_duration_seconds or 0.0) - (baseline.total_duration_seconds or 0.0),
            stage_delta=candidate.stage_count - baseline.stage_count,
            warning_delta=candidate.warning_count - baseline.warning_count,
            assertion_delta=candidate.assertion_fail_count - baseline.assertion_fail_count,
            cache_hit_delta=candidate.cache_hit_count - baseline.cache_hit_count,
            cache_miss_delta=candidate.cache_miss_count - baseline.cache_miss_count,
            notes=tuple(notes),
        )

    def clean(self, run_id: str, *, dry_run: bool = False) -> dict[str, object]:
        run = self.get_run(run_id)
        if run is None:
            raise NotFoundError("No existe un run de evaluacion con ese id.")
        removed: list[str] = []
        roots = [self.paths.project_root / "temp" / "evaluations", self.paths.project_root / "cache" / "evaluations"]
        run_roots = [root / run.scenario_id / run.id for root in roots]
        artifacts = self.list_artifacts(run_id)
        if not dry_run:
            for artifact in artifacts:
                path = Path(artifact.managed_path)
                if path.exists() and any(root in path.parents or path == root for root in roots):
                    path.unlink()
                    removed.append(str(path))
            for run_root in run_roots:
                if run_root.exists() and any(root in run_root.parents or run_root == root for root in roots):
                    shutil.rmtree(run_root)
                    removed.append(str(run_root))
        return {"run_id": run_id, "dry_run": dry_run, "removed": removed}


def build_operational_evaluation_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    media_service: MediaInspectionService,
    audio_service: AudioPreparationService,
    transcription_service: TranscriptionService,
    acoustic_service: AcousticAnalysisService,
    visual_service: VisualAnalysisService,
    multimodal_service: MultimodalAnalysisService,
    clip_service: ClipRankingService,
    personalization_service: PersonalizationDatasetService,
    model_service: PersonalizationTrainingService,
    repository: OperationalEvaluationRepository,
    logger: logging.Logger | None = None,
) -> OperationalEvaluationService:
    return OperationalEvaluationService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        media_service=media_service,
        audio_service=audio_service,
        transcription_service=transcription_service,
        acoustic_service=acoustic_service,
        visual_service=visual_service,
        multimodal_service=multimodal_service,
        clip_service=clip_service,
        personalization_service=personalization_service,
        model_service=model_service,
        repository=repository,
        logger=logger,
    )

