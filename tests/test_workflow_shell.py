from __future__ import annotations

import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.video_pipeline_service import VideoPipelineService
from creator_intelligence_studio.domain.errors import NotFoundError, StateError
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelStatus
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.error_mapping import map_error
from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord, WorkspaceUiStateStore
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
from creator_intelligence_studio.presentation.desktop.views.workflow_view import WorkflowView
from creator_intelligence_studio.shared.paths import ProjectPaths
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service


def make_settings() -> AppSettings:
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
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
    )


def make_diagnostic(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=root,
        os_name="Windows",
        os_version="11",
        os_architecture="x86_64",
        python_version="3.11.9",
        python_executable="python.exe",
        cpu_reported="CPU",
        logical_processors=8,
        nvidia_smi_available=True,
        gpu_devices=(SimpleNamespace(name="GPU", memory_total_mib=8192, driver_version="576.52"),),
        nvidia_driver_version="576.52",
        cuda_version_reported="12.9",
        git_available=True,
        git_version="git version 2.54.0",
        free_space_bytes=1_000_000,
        preferred_compute_backend="cuda",
        state=SimpleNamespace(ready_for_basic_mode=True, cuda_driver_detected=True, cuda_runtime_not_verified=True, warnings=()),
        warnings=(),
        errors=(),
    )


class _StageState:
    def __init__(self) -> None:
        self.inspected = False
        self.audio = False
        self.transcribed = False
        self.acoustic = False
        self.visual = False
        self.multimodal = False
        self.ranked = False


def _completed_report(name: str, *, stale: bool = False):
    return SimpleNamespace(
        status=SimpleNamespace(value="completed" if not stale else "stale"),
        is_stale=stale,
        analysis=SimpleNamespace(completed_at=None) if name != "transcription" else None,
        inspection=SimpleNamespace(inspected_at=None) if name == "inspection" else None,
        prepared_audio=SimpleNamespace(extraction_completed_at=None) if name == "audio" else None,
        transcription=SimpleNamespace(model_name="small", completed_at=None) if name == "transcription" else None,
        windows=(),
        scenes=(),
        events=(),
        warnings=(),
        errors=(),
        summary=None,
        file_available=True,
        selected_stream=None,
        cache_path=None,
        metadata_path=None,
        backend=SimpleNamespace(status=SimpleNamespace(value="installed"), model_name="small"),
        model_status=SimpleNamespace(status=SimpleNamespace(value="installed"), model_name="small"),
    )


def make_workspace(root: Path) -> WorkspaceViewModel:
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    catalog = build_catalog_service(settings, paths, logger=__import__("logging").getLogger("test"))
    creator = catalog.create_creator(display_name="Demo Creator", slug="demo-creator")
    project = catalog.create_project(creator_reference=creator.id, name="Demo Project", project_type="long_form")
    source = root / "video.mp4"
    source.write_bytes(b"demo")
    video = catalog.register_video(project_id=project.id, file_path=str(source), title="Demo Video")

    state = _StageState()

    class MediaService:
        def verify_media_tools(self):
            return SimpleNamespace(ffmpeg=SimpleNamespace(available=True, version="6.1"), ffprobe=SimpleNamespace(available=True, version="6.1"), warnings=(), available=True)

        def get_video_inspection(self, video_id: str):
            return _completed_report("inspection") if state.inspected else None

        def inspect_video(self, video_id: str, force: bool = False):
            state.inspected = True
            return _completed_report("inspection")

        def is_inspection_stale(self, video_id: str) -> bool:
            return False

    class AudioService:
        def prepare_audio(self, video_id: str, force: bool = False):
            state.audio = True
            return _completed_report("audio")

        def get_prepared_audio(self, video_id: str):
            return _completed_report("audio") if state.audio else None

        def is_prepared_audio_stale(self, video_id: str) -> bool:
            return False

        def verify_prepared_audio(self, video_id: str):
            return _completed_report("audio")

        def delete_prepared_audio_cache(self, video_id: str):
            return SimpleNamespace(deleted_record=False, deleted_files=())

    class TranscriptionService:
        def verify_transcription_backend(self):
            return SimpleNamespace(backend=SimpleNamespace(available=True, backend="cpu", device_count=1, supported_compute_types=("int8",), cuda_runtime_available=False, cudnn_available=False, dll_directories=(), to_dict=lambda: {}), model_statuses=(), notes=())

        def list_models(self):
            return (SimpleNamespace(model_name="small", status=TranscriptionModelStatus.INSTALLED, path="models/small", notes="ok"),)

        def get_model_status(self, model_name: str):
            return SimpleNamespace(model_name=model_name, status=TranscriptionModelStatus.INSTALLED, path="models/small", notes="ok")

        def verify_model(self, model_name: str):
            return self.get_model_status(model_name)

        def download_model(self, model_name: str, **kwargs):
            return self.get_model_status(model_name)

        def remove_model(self, model_name: str):
            return False

        def transcribe_video(self, video_id: str, options, **kwargs):
            state.transcribed = True
            return _completed_report("transcription")

        def get_transcription(self, video_id: str):
            return _completed_report("transcription") if state.transcribed else SimpleNamespace(status=SimpleNamespace(value="not_transcribed"), is_stale=False, transcription=None, segments=(), backend=None, model_status=None, warnings=(), errors=(), progress_message=None)

        def is_transcription_stale(self, video_id: str) -> bool:
            return False

        def cancel_transcription(self, video_id: str) -> bool:
            return False

        def delete_transcription(self, video_id: str) -> bool:
            return False

    class AcousticService:
        def analyze_acoustics(self, video_id: str, force: bool = False, *, progress_callback=None):
            state.acoustic = True
            return _completed_report("acoustic")

        def get_acoustic_analysis(self, video_id: str):
            return _completed_report("acoustic") if state.acoustic else SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), events=(), warnings=(), errors=(), progress_message=None)

        def get_acoustic_timeline(self, video_id: str):
            return ()

        def list_acoustic_events(self, video_id: str):
            return ()

        def is_acoustic_analysis_stale(self, video_id: str) -> bool:
            return False

        def delete_acoustic_analysis(self, video_id: str) -> bool:
            return False

    class VisualService:
        def analyze_visuals(self, video_id: str, force: bool = False, *, progress_callback=None):
            state.visual = True
            return _completed_report("visual")

        def get_visual_analysis(self, video_id: str):
            return _completed_report("visual") if state.visual else SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), scenes=(), events=(), warnings=(), errors=(), progress_message=None)

        def get_visual_timeline(self, video_id: str):
            return ()

        def list_visual_scenes(self, video_id: str):
            return ()

        def list_visual_events(self, video_id: str):
            return ()

        def is_visual_analysis_stale(self, video_id: str) -> bool:
            return False

        def delete_visual_analysis(self, video_id: str) -> bool:
            return False

    class MultimodalService:
        def analyze_multimodal(self, video_id: str, force: bool = False, *, progress_callback=None):
            state.multimodal = True
            return SimpleNamespace(status=SimpleNamespace(value="completed"), is_stale=False, analysis=SimpleNamespace(completed_at=None, duration_seconds=10.0), transcription=SimpleNamespace(id="tx"), acoustic_analysis=SimpleNamespace(id="ac"), visual_analysis=SimpleNamespace(id="vis"), windows=(), candidates=(), available_sources=("transcription", "acoustic", "visual"), missing_sources=(), warnings=(), errors=(), progress_message=None)

        def get_multimodal_analysis(self, video_id: str):
            return self.analyze_multimodal(video_id) if state.multimodal else SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, transcription=None, acoustic_analysis=None, visual_analysis=None, windows=(), candidates=(), available_sources=(), missing_sources=(), warnings=(), errors=(), progress_message=None)

        def get_multimodal_timeline(self, video_id: str):
            return ()

        def list_moment_candidates(self, video_id: str):
            return ()

        def get_moment_candidate(self, candidate_id: str):
            return None

        def is_multimodal_analysis_stale(self, video_id: str) -> bool:
            return False

        def delete_multimodal_analysis(self, video_id: str) -> bool:
            return False

    class ClipService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def rank_clip_candidates(self, video_id: str, profile: str = "balanced", force: bool = False, *, progress_callback=None):
            self.calls.append("ranking")
            state.ranked = True
            candidate = SimpleNamespace(id="cand-1", multimodal_candidate_id="cand-1", review_status=SimpleNamespace(value="unreviewed"), user_rating=None, tags=(), adjusted_start_seconds=0.0, adjusted_end_seconds=1.0, original_start_seconds=0.0, original_end_seconds=1.0)
            return SimpleNamespace(video=SimpleNamespace(id=video_id), multimodal_report=MultimodalService().get_multimodal_analysis(video_id), run=SimpleNamespace(id="run-1", completed_at=None, ranked_candidate_count=1, selected_count=1, rejected_count=0, review_count=0), candidates=(candidate,), status=SimpleNamespace(value="completed"), is_stale=False, available_sources=("transcription", "acoustic", "visual"), missing_sources=(), warnings=(), errors=(), progress_message=None)

        def get_ranking_run(self, video_id: str):
            if state.ranked:
                return self.rank_clip_candidates(video_id)
            return SimpleNamespace(video=SimpleNamespace(id=video_id), multimodal_report=None, run=None, candidates=(), status=SimpleNamespace(value="not_ranked"), is_stale=False, available_sources=(), missing_sources=(), warnings=(), errors=(), progress_message=None)

        def list_ranked_candidates(self, video_id: str, filters=None, sort=None):
            return ()

        def get_ranked_candidate(self, candidate_id: str):
            return None

        def approve_candidate(self, candidate_id: str):
            return None

        def reject_candidate(self, candidate_id: str):
            return None

        def shortlist_candidate(self, candidate_id: str):
            return None

        def mark_candidate_needs_review(self, candidate_id: str):
            return None

        def rate_candidate(self, candidate_id: str, rating: int):
            return None

        def add_candidate_note(self, candidate_id: str, note: str):
            return None

        def set_candidate_tags(self, candidate_id: str, tags: list[str]):
            return None

        def adjust_candidate_bounds(self, candidate_id: str, start_seconds: float, end_seconds: float):
            return None

        def reset_candidate_review(self, candidate_id: str):
            return None

        def get_candidate_review_history(self, candidate_id: str):
            return ()

        def is_clip_ranking_stale(self, video_id: str) -> bool:
            return False

        def delete_clip_ranking(self, video_id: str) -> bool:
            return False

        def create_clip_collection(self, video_id: str, name: str, description: str | None = None):
            return SimpleNamespace(id="collection-1", name=name)

        def add_candidate_to_collection(self, collection_id: str, candidate_id: str):
            return None

        def remove_candidate_from_collection(self, collection_id: str, candidate_id: str) -> bool:
            return False

        def export_clip_plan(self, video_id: str, format_name: str):
            return SimpleNamespace(path="cache/clips/export.json")

    workspace = WorkspaceViewModel(
        service=catalog,
        media_service=MediaService(),
        audio_service=AudioService(),
        transcription_service=TranscriptionService(),
        acoustic_service=AcousticService(),
        visual_service=VisualService(),
        multimodal_service=MultimodalService(),
        clip_service=ClipService(),
        diagnostic=make_diagnostic(root),
        settings=settings,
        paths=paths,
    )
    workspace.select_creator(creator.id)
    workspace.select_project(project.id)
    workspace.select_video(video.id)
    return workspace


class WorkflowShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_pipeline_status_and_execution_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = make_workspace(root)
            status = workspace.video_pipeline_status(workspace.selected_video_id)
            self.assertEqual(status.current_stage, "inspection")
            self.assertEqual(status.recommended_action, "Inspeccionar video")

            next_result = workspace.run_pipeline_next_step(workspace.selected_video_id)
            self.assertEqual(next_result.stage_name, "inspection")
            status = workspace.video_pipeline_status(workspace.selected_video_id)
            self.assertEqual(status.current_stage, "audio")

            results = workspace.run_pipeline_until_ranking(workspace.selected_video_id)
            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[-1].stage_name, "ranking")
            status = workspace.video_pipeline_status(workspace.selected_video_id)
            self.assertEqual(status.recommended_action, "Renderizar clips aprobados")

    def test_background_tasks_and_task_center(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = make_workspace(root)
            task = workspace.register_background_task(title="Workflow de video", status="running", video_id=workspace.selected_video_id, video_title="Demo Video", stage_name="inspection")
            self.assertEqual(len(workspace.background_tasks()), 1)

            view = TaskCenterView(workspace)
            view.refresh()
            self.assertEqual(view.table.rowCount(), 1)
            self.assertEqual(view.table.item(0, 0).text(), "Workflow de video")
            workspace.interrupt_background_task(task.task_id, "Interrumpida")
            self.assertEqual(workspace.background_tasks()[0].status, "interrupted")

    def test_background_tasks_include_subtitle_deliveries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = make_workspace(root)
            now = datetime.now(timezone.utc)
            job = SimpleNamespace(
                id="job-1",
                video_asset_id=workspace.selected_video_id,
                ranked_clip_candidate_id="candidate-1",
                collection_id=None,
                status=SimpleNamespace(value="completed"),
                progress_percent=100.0,
                warning_message=None,
                error_message=None,
                created_at=now,
                updated_at=now,
                cancelled_at=None,
                completed_at=now,
                to_dict=lambda: {"id": "job-1"},
            )
            delivery = SimpleNamespace(
                id="delivery-1",
                render_job_id=job.id,
                subtitle_track_id="track-1",
                subtitle_mode=SimpleNamespace(value="sidecar_srt"),
                status=SimpleNamespace(value="completed"),
                progress_percent=100.0,
                warning_message=None,
                error_message=None,
                created_at=now,
                updated_at=now,
                cancelled_at=None,
                completed_at=now,
                to_dict=lambda: {"id": "delivery-1"},
            )
            workspace.render_service = SimpleNamespace(
                list_render_jobs=lambda: (job,),
                list_render_deliveries=lambda job_id: (delivery,) if job_id == job.id else (),
            )
            tasks = workspace.background_tasks()
            self.assertEqual(len(tasks), 2)
            self.assertEqual({task.task_id for task in tasks}, {"job-1", "delivery-1"})
            self.assertIn("Entrega de subtitulos", {task.title for task in tasks})

            view = TaskCenterView(workspace)
            view.refresh()
            self.assertEqual(view.table.rowCount(), 2)
            titles = {view.table.item(row, 0).text() for row in range(view.table.rowCount())}
            self.assertIn("Entrega de subtitulos", titles)

    def test_render_subtitles_cli_handlers(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["render", "subtitles", "capabilities"])
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = dispatch(
            args,
            service=SimpleNamespace(),
            media_service=SimpleNamespace(),
            audio_service=SimpleNamespace(),
            transcription_service=SimpleNamespace(),
            acoustic_service=SimpleNamespace(),
            visual_service=SimpleNamespace(),
            multimodal_service=SimpleNamespace(),
            clip_service=SimpleNamespace(),
            render_service=SimpleNamespace(
                render_subtitle_capabilities=lambda: {"sidecar_available": True, "burn_in_available": True},
                render_subtitle_styles=lambda: ({"preset": "clean"},),
            ),
            subtitle_service=SimpleNamespace(),
            personalization_service=SimpleNamespace(),
            diagnostic=SimpleNamespace(to_json=lambda: "{}", state=SimpleNamespace(ready_for_basic_mode=True)),
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(code, 0)
        self.assertIn("sidecar_available", stdout.getvalue())

    def test_error_translation_and_state_persistence(self) -> None:
        self.assertEqual(map_error(NotFoundError("faltante")).title, "Elemento no encontrado")
        self.assertEqual(map_error(StateError("bloqueado")).title, "La accion no esta disponible")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = WorkspaceUiStateStore(Path(temp_dir) / "ui.json")
            state = store.update(store.load(), active_creator_id="creator-1", last_page="workflow")
            self.assertEqual(state.active_creator_id, "creator-1")
            self.assertEqual(store.load().last_page, "workflow")

    def test_workflow_view_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = make_workspace(root)
            view = WorkflowView(workspace)
            view.refresh()
            self.assertGreaterEqual(view.stage_table.rowCount(), 1)
            self.assertIn("Inspeccion", view.stage_table.item(0, 0).text())
