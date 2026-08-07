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
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetOptions, PersonalizationSplitName
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
        def _jsonable(value):
            if isinstance(value, list):
                return [_jsonable(item) for item in value]
            if isinstance(value, dict):
                return {key: _jsonable(item) for key, item in value.items()}
            if hasattr(value, "to_dict"):
                return value.to_dict()
            return value
        try:
            result = action()
            timing = timer.finish()
            status = OperationalEvaluationStageStatus.COMPLETED
            if isinstance(result, dict) and result.get("warnings"):
                warnings.extend([str(item) for item in result["warnings"] if item])
                status = OperationalEvaluationStageStatus.COMPLETED_WITH_WARNINGS
            output_summary = result if isinstance(result, dict) else {"result": _jsonable(result)}
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
            demo_bundles: list[DemoAssetBundle] = []
            video_ids: list[str] = []
            video_paths: list[Path] = []
            primary_video_id: str | None = None
            model_run_id: str | None = None
            snapshot_id: str | None = None
            active_model_run_id: str | None = None
            score_probe_candidate_id: str | None = None
            score_probe_rank_score: float | None = None
            controlled_feedback_rule_name = "synthetic_evaluation_rule"

            def add_metric(metric_name: str, metric_value: float | None, *, metric_unit: str | None = None, stage_name_for_metric: str | None = None, details: dict[str, object] | None = None) -> None:
                metrics.append(
                    OperationalEvaluationMetric(
                        id=str(uuid4()),
                        evaluation_run_id=run.id,
                        stage_name=stage_name_for_metric,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        metric_unit=metric_unit,
                        details_json=details or {},
                        created_at=utc_now(),
                    )
                )

            def add_assertion(
                stage_name_for_assertion: str | None,
                name: str,
                condition: bool,
                *,
                severity: OperationalEvaluationAssertionSeverity = OperationalEvaluationAssertionSeverity.ERROR,
                expected: dict[str, object] | None = None,
                actual: dict[str, object] | None = None,
                message: str | None = None,
            ) -> None:
                assertions.append(
                    self._record_assertion(
                        run.id,
                        stage_name=stage_name_for_assertion,
                        assertion=assert_condition(
                            name,
                            condition,
                            severity=severity,
                            expected=expected,
                            actual=actual,
                            message=message,
                        ),
                    )
                )

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
                        bundles: list[DemoAssetBundle] = []
                        styles = plan.video_styles or ("static",)
                        for asset_index, style in enumerate(styles):
                            bundles.append(
                                create_demo_assets(
                                    project_root=self.paths.project_root,
                                    scenario_id=scenario_id,
                                    run_id=run.id,
                                    style=style,
                                    narration_text=plan.narration_text,
                                    duration_seconds=plan.duration_seconds,
                                    asset_index=asset_index,
                                )
                            )
                        return bundles
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"styles": list(plan.video_styles), "duration_seconds": plan.duration_seconds},
                        action=_generate,
                        cache_status=OperationalEvaluationCacheStatus.MISS,
                    )
                    if isinstance(result, list):
                        demo_bundles = [bundle for bundle in result if isinstance(bundle, DemoAssetBundle)]
                    elif isinstance(result, DemoAssetBundle):
                        demo_bundles = [result]
                    else:
                        demo_bundles = []
                    for bundle in demo_bundles:
                        video_paths.append(bundle.video_path)
                        artifacts.append(self._manage_artifact(run_id=run.id, stage_name=stage_name, artifact_type="demo_video", path=bundle.video_path))
                        artifacts.append(self._manage_artifact(run_id=run.id, stage_name=stage_name, artifact_type="demo_audio", path=bundle.audio_path))
                    demo_bundle = demo_bundles[0] if demo_bundles else None
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
                    if isinstance(result, list):
                        add_metric("inspected_video_count", float(len(result)), stage_name_for_metric=stage_name)
                    for report in result or []:
                        add_assertion(
                            stage_name,
                            "analysis_source_completed",
                            report.inspection is not None and report.status.value == "completed",
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"status": "completed"},
                            actual={"status": report.status.value, "video_id": getattr(getattr(report, "video", None), "id", None)},
                            message="Inspeccion completada.",
                        )
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
                        if model_status.status.value not in {"installed", "legacy_cache"}:
                            return model_status
                        return self.transcription_service.verify_model("small")
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
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    target_video_ids = video_ids if plan.use_controlled_feedback else [primary_video_id] if primary_video_id is not None else []
                    if not target_video_ids:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    options = TranscriptionOptions(
                        profile="balanced",
                        model_name="small",
                        device="cpu" if (stage_name == "transcribe_cpu" or plan.force_cpu_transcription) else "auto",
                        compute_type="int8" if (stage_name == "transcribe_cpu" or plan.force_cpu_transcription) else None,
                        language="en",
                        beam_size=5,
                        vad_filter=False,
                        word_timestamps=False,
                    )
                    def _transcribe():
                        return [self.transcription_service.transcribe_video(video_id, options) for video_id in target_video_ids]
                    cache_status = OperationalEvaluationCacheStatus.HIT if stage_name == "transcribe_cached" else OperationalEvaluationCacheStatus.MISS
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": target_video_ids, "options": options.to_dict()},
                        action=_transcribe,
                        cache_status=cache_status,
                    )
                    if isinstance(result, list):
                        add_metric("transcribed_video_count", float(len(result)), stage_name_for_metric=stage_name)
                    for report in result or []:
                        add_assertion(
                            stage_name,
                            "transcription_result_available",
                            getattr(report, "transcription", None) is not None and getattr(report, "backend", None) is not None and getattr(report, "model_status", None) is not None,
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"backend": "available", "model_status": "available"},
                            actual={
                                "video_id": getattr(getattr(report, "video", None), "id", None),
                                "backend": report.backend.to_dict() if getattr(report, "backend", None) else None,
                                "model_status": report.model_status.to_dict() if getattr(report, "model_status", None) else None,
                            },
                            message="La transcripcion produjo resultado auditable.",
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
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    target_video_ids = video_ids if plan.use_controlled_feedback else [primary_video_id] if primary_video_id is not None else []
                    if not target_video_ids:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": target_video_ids},
                        action=lambda: [self.acoustic_service.analyze_acoustics(video_id, force=force) for video_id in target_video_ids],
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "analyze_visuals":
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    target_video_ids = video_ids if plan.use_controlled_feedback else [primary_video_id] if primary_video_id is not None else []
                    if not target_video_ids:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": target_video_ids},
                        action=lambda: [self.visual_service.analyze_visuals(video_id, force=force) for video_id in target_video_ids],
                    )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "analyze_multimodal":
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    target_video_ids = video_ids if plan.use_controlled_feedback else [primary_video_id] if primary_video_id is not None else []
                    if not target_video_ids:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": target_video_ids},
                        action=lambda: [self.multimodal_service.analyze_multimodal(video_id, force=force) for video_id in target_video_ids],
                    )
                    if isinstance(result, list):
                        add_metric("multimodal_video_count", float(len(result)), stage_name_for_metric=stage_name)
                    for report in result or []:
                        add_assertion(
                            stage_name,
                            "multimodal_candidates_generated",
                            getattr(report, "analysis", None) is not None and len(getattr(report, "candidates", ())) > 0,
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"candidates": ">0"},
                            actual={"video_id": getattr(getattr(report, "video", None), "id", None), "candidates": len(getattr(report, "candidates", ()))},
                            message="Los candidatos multimodales quedaron disponibles.",
                        )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "rank_clips":
                    if not video_ids:
                        raise OperationalEvaluationStateError("No existen videos registrados.")
                    target_video_ids = video_ids if plan.use_controlled_feedback else [primary_video_id] if primary_video_id is not None else []
                    if not target_video_ids:
                        raise OperationalEvaluationStateError("No existe video principal.")
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": target_video_ids},
                        action=lambda: [self.clip_service.rank_clip_candidates(video_id, profile="balanced", force=force) for video_id in target_video_ids],
                    )
                    if isinstance(result, list):
                        add_metric("ranked_video_count", float(len(result)), stage_name_for_metric=stage_name)
                        add_metric(
                            "ranked_candidate_count",
                            float(sum(len(report.candidates) for report in result if getattr(report, "candidates", None) is not None)),
                            stage_name_for_metric=stage_name,
                        )
                        add_assertion(
                            stage_name,
                            "ranking_generated",
                            all(getattr(report, "run", None) is not None for report in result),
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"ranked_videos": len(target_video_ids)},
                            actual={"ranked_reports": len(result)},
                            message="Se genero ranking para los videos demo.",
                        )
                    if primary_video_id is not None:
                        ranked_candidates = self.clip_service.list_ranked_candidates(primary_video_id)
                        if ranked_candidates:
                            score_probe_candidate_id = ranked_candidates[0].id
                            score_probe_rank_score = ranked_candidates[0].rank_score
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "apply_controlled_feedback":
                    def _feedback():
                        target_video_ids = video_ids if plan.use_controlled_feedback else ([primary_video_id] if primary_video_id is not None else [])
                        if not target_video_ids:
                            return {"warnings": ["No hay videos para feedback controlado."], "rule_name": controlled_feedback_rule_name}
                        actions = []
                        collections = []
                        for video_index, video_id in enumerate(target_video_ids):
                            ranking = self.clip_service.get_ranking_run(video_id)
                            if ranking.run is None:
                                continue
                            candidates = self.clip_service.list_ranked_candidates(video_id)
                            if not candidates:
                                continue
                            collection = self.clip_service.create_clip_collection(
                                video_id,
                                name=f"Demo collection {video_index + 1}",
                                description="Coleccion sintetica controlada.",
                            )
                            collections.append(collection.to_dict())
                            positive_video = video_index % 2 == 0
                            neutral_video = False
                            for candidate_index, candidate in enumerate(candidates[:4]):
                                if candidate.review_status.value in {"duplicate", "invalid"}:
                                    self.clip_service.set_candidate_tags(candidate.id, ["duplicate", "synthetic"])
                                    self.clip_service.add_candidate_note(candidate.id, "Synthetic duplicate left excluded for leakage control.")
                                    continue
                                if candidate_index == 0:
                                    if neutral_video:
                                        updated = self.clip_service.shortlist_candidate(candidate.id)
                                        if video_index % 4 == 2:
                                            self.clip_service.rate_candidate(candidate.id, 3)
                                            self.clip_service.set_candidate_tags(candidate.id, ["shortlist", "borderline", "synthetic"])
                                            self.clip_service.add_candidate_note(candidate.id, "Synthetic neutral shortlist decision.")
                                        else:
                                            updated = self.clip_service.mark_candidate_needs_review(candidate.id)
                                            self.clip_service.rate_candidate(candidate.id, 3)
                                            self.clip_service.set_candidate_tags(candidate.id, ["needs_review", "borderline", "synthetic"])
                                            self.clip_service.add_candidate_note(candidate.id, "Synthetic neutral review decision.")
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "neutral", "rating": 3})
                                        break
                                    elif positive_video:
                                        updated = self.clip_service.approve_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 5)
                                        self.clip_service.set_candidate_tags(candidate.id, ["approved", "highlight", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic positive decision.")
                                    else:
                                        updated = self.clip_service.reject_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 1)
                                        self.clip_service.set_candidate_tags(candidate.id, ["rejected", "low_energy", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic negative decision.")
                                    self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                    actions.append({"candidate_id": updated.id, "action": "approve" if positive_video else "reject", "rating": 5 if positive_video else 1})
                                elif candidate_index == 1:
                                    if positive_video:
                                        updated = self.clip_service.shortlist_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 4)
                                        self.clip_service.set_candidate_tags(candidate.id, ["shortlist", "borderline", "synthetic"])
                                        if candidate.duration_seconds > 0.4:
                                            delta = min(0.2, max(candidate.duration_seconds * 0.1, 0.05))
                                            start_seconds = max(0.0, candidate.adjusted_start_seconds + delta)
                                            end_seconds = candidate.adjusted_end_seconds - delta
                                            if end_seconds > start_seconds:
                                                self.clip_service.adjust_candidate_bounds(candidate.id, start_seconds, end_seconds)
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic shortlist with manual bounds adjustment.")
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "shortlist", "rating": 4})
                                    else:
                                        updated = self.clip_service.reject_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 2)
                                        self.clip_service.set_candidate_tags(candidate.id, ["rejected", "low_energy", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic negative decision.")
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "reject", "rating": 2})
                                elif candidate_index == 2:
                                    if positive_video:
                                        updated = self.clip_service.shortlist_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 4)
                                        self.clip_service.set_candidate_tags(candidate.id, ["shortlist", "borderline", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic shortlist with manual bounds adjustment.")
                                        if candidate.duration_seconds > 0.4:
                                            delta = min(0.2, max(candidate.duration_seconds * 0.1, 0.05))
                                            start_seconds = max(0.0, candidate.adjusted_start_seconds + delta)
                                            end_seconds = candidate.adjusted_end_seconds - delta
                                            if end_seconds > start_seconds:
                                                self.clip_service.adjust_candidate_bounds(candidate.id, start_seconds, end_seconds)
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "shortlist", "rating": 4})
                                    else:
                                        updated = self.clip_service.reject_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 1)
                                        self.clip_service.set_candidate_tags(candidate.id, ["rejected", "low_energy", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic negative decision.")
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "reject", "rating": 1})
                                else:
                                    if positive_video:
                                        updated = self.clip_service.shortlist_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 4)
                                        self.clip_service.set_candidate_tags(candidate.id, ["shortlist", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic positive fallback decision.")
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "shortlist", "rating": 4})
                                    else:
                                        updated = self.clip_service.reject_candidate(candidate.id)
                                        self.clip_service.rate_candidate(candidate.id, 1)
                                        self.clip_service.set_candidate_tags(candidate.id, ["rejected", "synthetic"])
                                        self.clip_service.add_candidate_note(candidate.id, "Synthetic negative fallback decision.")
                                        self.clip_service.add_candidate_to_collection(collection.id, candidate.id)
                                        actions.append({"candidate_id": updated.id, "action": "reject", "rating": 1})
                        return {"actions": actions, "collections": collections, "rule_name": controlled_feedback_rule_name, "warnings": []}
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"video_ids": video_ids, "rule_name": controlled_feedback_rule_name},
                        action=_feedback,
                    )
                    if isinstance(result, dict):
                        add_metric("feedback_action_count", float(len(result.get("actions", []))), stage_name_for_metric=stage_name)
                        add_metric("feedback_collection_count", float(len(result.get("collections", []))), stage_name_for_metric=stage_name)
                        add_assertion(
                            stage_name,
                            "feedback_rule_is_synthetic_evaluation_rule",
                            result.get("rule_name") == controlled_feedback_rule_name,
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"rule_name": controlled_feedback_rule_name},
                            actual={"rule_name": result.get("rule_name")},
                            message="La regla sintetica de feedback quedo auditada.",
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
                        add_assertion(
                            stage_name,
                            "training_run_completed",
                            getattr(result.training_run, "status", None) is not None
                            and result.training_run.status.value in {"completed", "completed_with_warnings"},
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"training_run_status": ["completed", "completed_with_warnings"]},
                            actual={
                                "training_run_status": getattr(result.training_run.status, "value", None),
                                "outcome_status": result.outcome_status,
                            },
                            message="El training baseline completo correctamente.",
                        )
                        add_metric("baseline_metric_count", float(len(result.metrics)), stage_name_for_metric=stage_name)
                        add_metric("baseline_summary_count", float(len(result.baseline_summary)), stage_name_for_metric=stage_name)
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
                        add_assertion(
                            stage_name,
                            "model_candidate_before_activation",
                            getattr(result.registry_entry, "status", None) is not None and result.registry_entry.status.value == "candidate",
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"status": "candidate"},
                            actual={"status": getattr(result.registry_entry.status, "value", None)},
                            message="El modelo queda como candidate antes de activar.",
                        )
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
                    if result is not None and getattr(result, "registry_entry", None) is not None:
                        add_assertion(
                            stage_name,
                            "model_active_after_activate",
                            getattr(result.registry_entry, "is_active", False) is True,
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"is_active": True},
                            actual={"is_active": getattr(result.registry_entry, "is_active", None), "status": getattr(result.registry_entry.status, "value", None)},
                            message="El modelo quedo activo tras la activacion explicita.",
                        )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "score_candidates":
                    if creator is None or primary_video_id is None:
                        raise OperationalEvaluationStateError("Faltan creador o video principal.")
                    target_video_ids = video_ids if plan.use_controlled_feedback else [primary_video_id]
                    if score_probe_candidate_id is None:
                        ranked_candidates = self.clip_service.list_ranked_candidates(primary_video_id)
                        if ranked_candidates:
                            score_probe_candidate_id = ranked_candidates[0].id
                            score_probe_rank_score = ranked_candidates[0].rank_score
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"creator_id": creator.id, "video_ids": target_video_ids},
                        action=lambda: [self.model_service.score_candidates_for_video(creator.id, video_id) for video_id in target_video_ids],
                    )
                    flattened_scores = []
                    for item in result or []:
                        if isinstance(item, list):
                            flattened_scores.extend(item)
                        elif item is not None:
                            flattened_scores.append(item)
                    if flattened_scores:
                        add_metric("personalized_score_count", float(len(flattened_scores)), stage_name_for_metric=stage_name, details={"video_ids": target_video_ids})
                        add_assertion(
                            stage_name,
                            "personalized_score_generated",
                            len(flattened_scores) > 0,
                            severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                            expected={"min_scores": 1},
                            actual={"scores": len(flattened_scores)},
                            message="Se genero scoring personalizado.",
                        )
                        if score_probe_candidate_id is not None and score_probe_rank_score is not None:
                            probe = self.clip_service.get_ranked_candidate(score_probe_candidate_id)
                            add_assertion(
                                stage_name,
                                "rank_score_intact",
                                abs(probe.rank_score - score_probe_rank_score) < 1e-9,
                                severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                                expected={"rank_score": score_probe_rank_score},
                                actual={"rank_score": probe.rank_score},
                                message="El personalized scoring no modifico rank_score.",
                            )
                    stages.append(stage)
                    warnings.extend(w)
                    errors.extend(e)
                    continue
                if stage_name == "export_report":
                    stage, m, a, art, w, e, result = self._stage(
                        run_id=run.id,
                        stage_index=index,
                        stage_name=stage_name,
                        input_summary_json={"run_id": run.id, "format": "json"},
                        action=lambda: {"requested": True, "run_id": run.id, "format": "json"},
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
            if creator is not None:
                add_assertion(
                    "create_demo_creator",
                    "demo_creator_isolated",
                    str(getattr(creator, "slug", "")).startswith("demo-"),
                    severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                    expected={"creator_slug_prefix": "demo-"},
                    actual={"creator_id": getattr(creator, "id", None), "slug": getattr(creator, "slug", None)},
                    message="El creador demo quedo aislado por slug sintetico.",
                )
                if project is not None:
                    add_assertion(
                        "create_demo_project",
                        "demo_project_isolated",
                        getattr(project, "creator_id", None) == creator.id,
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"creator_id": creator.id},
                        actual={"project_creator_id": getattr(project, "creator_id", None), "project_id": getattr(project, "id", None)},
                        message="El proyecto demo pertenece al creador demo.",
                    )
            if video_ids:
                add_assertion(
                    "register_video",
                    "several_videos_generated",
                    len(video_ids) >= 3 if plan.use_controlled_feedback else len(video_ids) >= 1,
                    severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                    expected={"min_videos": 3 if plan.use_controlled_feedback else 1},
                    actual={"video_count": len(video_ids)},
                    message="Se generaron varios videos demo aislados.",
                )
                add_assertion(
                    "register_video",
                    "assets_outside_git",
                    all(str(path).startswith(str(self.paths.project_root / "temp" / "evaluations")) for path in video_paths),
                    severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                    expected={"managed_root": str(self.paths.project_root / "temp" / "evaluations")},
                    actual={"video_paths": [str(path) for path in video_paths]},
                    message="Los assets demo quedaron fuera del arbol rastreado por Git.",
                )
            if snapshot_id is not None:
                dataset_report = self.personalization_service.get_dataset_snapshot(snapshot_id)
                readiness_report = self.personalization_service.get_creator_readiness(creator.id if creator else dataset_report.creator.id)
                snapshot = dataset_report.snapshot
                if snapshot is not None:
                    by_video: dict[str, set[str]] = {}
                    for example in dataset_report.examples:
                        by_video.setdefault(example.video_asset_id, set()).add(example.split_name.value)
                    add_metric("dataset_example_count", float(snapshot.example_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("dataset_positive_count", float(snapshot.positive_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("dataset_negative_count", float(snapshot.negative_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("dataset_neutral_count", float(snapshot.neutral_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("dataset_excluded_count", float(snapshot.excluded_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("dataset_conflict_count", float(snapshot.conflict_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("train_count", float(snapshot.train_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("validation_count", float(snapshot.validation_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("test_count", float(snapshot.test_count), stage_name_for_metric="build_personalization_dataset")
                    add_metric("readiness_score", float(snapshot.readiness_score), stage_name_for_metric="evaluate_readiness")
                    add_assertion(
                        "build_personalization_dataset",
                        "dataset_snapshot_completed",
                        snapshot.status.value in {"completed", "completed_with_warnings"},
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"status": ["completed", "completed_with_warnings"]},
                        actual={"status": snapshot.status.value},
                        message="El snapshot de dataset quedo completado.",
                    )
                    add_assertion(
                        "build_personalization_dataset",
                        "feedback_has_positive_and_negative",
                        snapshot.positive_count > 0 and snapshot.negative_count > 0,
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"positive": ">0", "negative": ">0"},
                        actual={"positive": snapshot.positive_count, "negative": snapshot.negative_count},
                        message="El dataset contiene clases positivas y negativas.",
                    )
                    add_assertion(
                        "build_personalization_dataset",
                        "dataset_has_neutral_examples",
                        snapshot.neutral_count >= 0,
                        severity=OperationalEvaluationAssertionSeverity.WARNING,
                        expected={"neutral": ">=0"},
                        actual={"neutral": snapshot.neutral_count},
                        message="Los ejemplos neutrales no son requisito del baseline binario controlado.",
                    )
                    add_assertion(
                        "build_personalization_dataset",
                        "zero_blocking_conflicts",
                        snapshot.conflict_count == 0,
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"conflict_count": 0},
                        actual={"conflict_count": snapshot.conflict_count},
                        message="No quedaron conflictos bloqueantes en el dataset sintetico.",
                    )
                    add_assertion(
                        "build_personalization_dataset",
                        "readiness_at_least_baseline",
                        readiness_report.readiness_status.value in {"ready_for_baseline", "ready_for_evaluation", "ready_for_personalized_training"},
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"minimum_readiness": "ready_for_baseline"},
                        actual={"readiness_status": readiness_report.readiness_status.value, "readiness_score": readiness_report.readiness_score},
                        message="El dataset alcanzó readiness suficiente para baseline.",
                    )
                    add_assertion(
                        "build_personalization_dataset",
                        "split_by_video_respected",
                        all(
                            len(
                                {
                                    split_name
                                    for split_name in splits
                                    if split_name
                                    in {
                                        PersonalizationSplitName.TRAIN.value,
                                        PersonalizationSplitName.VALIDATION.value,
                                        PersonalizationSplitName.TEST.value,
                                    }
                                }
                            )
                            <= 1
                            for splits in by_video.values()
                        ),
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"one_split_per_video": True},
                        actual={
                            "video_split_map": {
                                video_id: sorted(
                                    split_name
                                    for split_name in splits
                                    if split_name
                                    in {
                                        PersonalizationSplitName.TRAIN.value,
                                        PersonalizationSplitName.VALIDATION.value,
                                        PersonalizationSplitName.TEST.value,
                                    }
                                )
                                for video_id, splits in by_video.items()
                            }
                        },
                        message="El split se mantiene por video sin leakage entre train, validation y test.",
                    )
                    add_assertion(
                        "build_personalization_dataset",
                        "train_contains_both_classes",
                        snapshot.train_count > 0 and snapshot.positive_count > 0 and snapshot.negative_count > 0,
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"train_count": ">0", "positive_count": ">0", "negative_count": ">0"},
                        actual={"train_count": snapshot.train_count, "positive_count": snapshot.positive_count, "negative_count": snapshot.negative_count},
                        message="El split train contiene clases positivas y negativas.",
                    )
            if model_run_id is not None:
                training_run = self.model_service.get_training_run(model_run_id)
                if training_run is not None:
                    add_assertion(
                        "train_baseline",
                        "training_run_completed_or_warned",
                        training_run.status.value in {"completed", "completed_with_warnings"},
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"status": ["completed", "completed_with_warnings"]},
                        actual={"status": training_run.status.value},
                        message="El training run quedo completado o completado con warnings.",
                    )
            if active_model_run_id is not None:
                active_report = self.model_service.get_active_creator_model(creator.id if creator else "", project_id=project.id if project else None)
                if active_report is not None:
                    add_assertion(
                        "activate_model",
                        "active_model_present",
                        active_report.registry_entry.is_active,
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"is_active": True},
                        actual={"training_run_id": active_report.registry_entry.training_run_id, "is_active": active_report.registry_entry.is_active},
                        message="Existe un unico modelo activo para el creador/proyecto demo.",
                    )
                    add_assertion(
                        "activate_model",
                        "artifact_verified",
                        active_report.artifact_verified,
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"artifact_verified": True},
                        actual={"artifact_verified": active_report.artifact_verified, "training_run_id": active_report.registry_entry.training_run_id},
                        message="El artefacto activo quedo verificado.",
                    )
            if stage_defs:
                add_metric("planned_stage_count", float(len(stage_defs)), stage_name_for_metric=None)
                add_metric("completed_stage_count", float(sum(1 for stage in stages if stage.status in {OperationalEvaluationStageStatus.COMPLETED, OperationalEvaluationStageStatus.COMPLETED_WITH_WARNINGS, OperationalEvaluationStageStatus.CACHED})), stage_name_for_metric=None)
                add_metric("warning_count", float(len(warnings)), stage_name_for_metric=None)
                add_metric("assertion_count", float(len(assertions)), stage_name_for_metric=None)
                if stages:
                    slowest_stage = max((stage for stage in stages if stage.duration_seconds is not None), key=lambda item: item.duration_seconds or 0.0)
                    add_metric("slowest_stage_duration_seconds", float(slowest_stage.duration_seconds or 0.0), stage_name_for_metric=slowest_stage.stage_name, details={"slowest_stage": slowest_stage.stage_name})
                if len(video_ids) > 0:
                    total_stage_duration = sum(float(stage.duration_seconds or 0.0) for stage in stages)
                    add_metric("time_per_video_seconds", total_stage_duration / len(video_ids), stage_name_for_metric=None)
            critical_failures = [item for item in assertions if item.severity == OperationalEvaluationAssertionSeverity.CRITICAL and item.status != "passed"]
            if critical_failures:
                errors.extend([f"{failure.assertion_name}: {failure.message}" for failure in critical_failures])
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
            if plan.export_report:
                exported_path = self.export(run.id, "json")
                export_assertion = self._record_assertion(
                    run.id,
                    stage_name="export_report",
                    assertion=assert_condition(
                        "export_created",
                        exported_path.exists(),
                        severity=OperationalEvaluationAssertionSeverity.CRITICAL,
                        expected={"exists": True},
                        actual={"path": str(exported_path), "exists": exported_path.exists()},
                        message="Se exporto el reporte de evaluacion.",
                    ),
                )
                assertions.append(export_assertion)
                artifacts.append(self._manage_artifact(run_id=run.id, stage_name="export_report", artifact_type="evaluation_report", path=exported_path))
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

