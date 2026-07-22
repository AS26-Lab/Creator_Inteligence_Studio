from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from creator_intelligence_studio.application import bootstrap
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    DiagnosticState,
    EnvironmentDiagnostic,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


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


def make_diagnostic(root: Path) -> EnvironmentDiagnostic:
    return EnvironmentDiagnostic(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=root,
        os_name="Windows",
        os_version="10.0.19045",
        os_architecture="64bit",
        python_version="3.11.9",
        python_executable="python.exe",
        cpu_reported="CPU",
        logical_processors=12,
        nvidia_smi_available=False,
        preferred_compute_backend="cuda",
        state=DiagnosticState(
            ready_for_basic_mode=True,
            cuda_driver_detected=False,
            cuda_runtime_not_verified=True,
            warnings=("CUDA no verificada",),
        ),
        warnings=("CUDA no verificada",),
        errors=(),
    )


def make_audio_service():
    return MagicMock(
        prepare_audio=MagicMock(return_value=MagicMock(status=MagicMock(value="not_prepared"), is_stale=False)),
        get_prepared_audio=MagicMock(return_value=None),
        is_prepared_audio_stale=MagicMock(return_value=False),
        verify_prepared_audio=MagicMock(return_value=MagicMock(status=MagicMock(value="not_prepared"), is_stale=False)),
        delete_prepared_audio_cache=MagicMock(return_value=MagicMock(deleted_record=False, deleted_files=())),
    )


def make_transcription_service():
    report = MagicMock(
        status=MagicMock(value="not_transcribed"),
        is_stale=False,
        transcription=None,
        segments=(),
        backend=None,
        model_status=None,
        warnings=(),
        errors=(),
        progress_message=None,
    )
    model = MagicMock(model_name="small", installed=False)
    model.to_dict = MagicMock(return_value={"model_name": "small"})
    backend = MagicMock(available=False, backend="cpu", device_count=0, supported_compute_types=(), to_dict=lambda: {})
    verification = SimpleNamespace(
        backend=backend,
        model_statuses=(model,),
        notes=(),
        to_dict=lambda: {"backend": backend.to_dict(), "model_statuses": [model.to_dict()], "notes": []},
    )
    return MagicMock(
        verify_transcription_backend=MagicMock(return_value=verification),
        list_models=MagicMock(return_value=(model,)),
        get_model_status=MagicMock(return_value=model),
        verify_model=MagicMock(return_value=model),
        download_model=MagicMock(return_value=model),
        remove_model=MagicMock(return_value=False),
        transcribe_video=MagicMock(return_value=report),
        get_transcription=MagicMock(return_value=report),
        is_transcription_stale=MagicMock(return_value=False),
        cancel_transcription=MagicMock(return_value=False),
        delete_transcription=MagicMock(return_value=False),
        export_transcription=MagicMock(return_value=MagicMock(path="cache/transcriptions/video/transcription.txt", to_dict=lambda: {})),
    )


def make_acoustic_service():
    report = MagicMock(
        status=MagicMock(value="not_analyzed"),
        is_stale=False,
        analysis=None,
        windows=(),
        events=(),
        warnings=(),
        errors=(),
        progress_message=None,
    )
    return MagicMock(
        analyze_acoustics=MagicMock(return_value=report),
        get_acoustic_analysis=MagicMock(return_value=report),
        get_acoustic_timeline=MagicMock(return_value=()),
        list_acoustic_events=MagicMock(return_value=()),
        is_acoustic_analysis_stale=MagicMock(return_value=False),
        delete_acoustic_analysis=MagicMock(return_value=False),
        export_acoustic_analysis=MagicMock(return_value=MagicMock(path="cache/acoustic/video/acoustic_analysis.json", to_dict=lambda: {})),
    )


def make_visual_service():
    report = MagicMock(
        status=MagicMock(value="not_analyzed"),
        is_stale=False,
        analysis=None,
        windows=(),
        scenes=(),
        events=(),
        warnings=(),
        errors=(),
        progress_message=None,
    )
    report.to_dict = MagicMock(return_value={"status": "not_analyzed", "is_stale": False, "analysis": None, "windows": [], "scenes": [], "events": []})
    return MagicMock(
        analyze_visuals=MagicMock(return_value=report),
        get_visual_analysis=MagicMock(return_value=report),
        get_visual_timeline=MagicMock(return_value=()),
        list_visual_scenes=MagicMock(return_value=()),
        list_visual_events=MagicMock(return_value=()),
        is_visual_analysis_stale=MagicMock(return_value=False),
        delete_visual_analysis=MagicMock(return_value=False),
        export_visual_analysis=MagicMock(return_value=MagicMock(path="cache/visual/video/visual_analysis.json", to_dict=lambda: {})),
    )


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_basic_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = make_diagnostic(root)

            with patch(
                "creator_intelligence_studio.application.bootstrap._load_context",
                return_value=bootstrap.BootstrapContext(
                    settings=settings,
                    paths=paths,
                    diagnostic=diagnostic,
                    logger=logging.getLogger("test"),
                ),
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(stdout=stdout, stderr=stderr)

        self.assertEqual(code, 0)
        self.assertIn("Creator Intelligence Studio", stdout.getvalue())

    def test_diagnostic_json_mode_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = make_diagnostic(root)

            with patch(
                "creator_intelligence_studio.application.bootstrap._load_context",
                return_value=bootstrap.BootstrapContext(
                    settings=settings,
                    paths=paths,
                    diagnostic=diagnostic,
                    logger=logging.getLogger("test"),
                ),
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(argv=["--diagnostic-json"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 0)
        json.loads(stdout.getvalue())

    def test_bootstrap_creator_command_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            diagnostic = make_diagnostic(root)
            service_context = bootstrap.ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
                service=MagicMock(),
                media_service=MagicMock(),
                audio_service=make_audio_service(),
                transcription_service=make_transcription_service(),
                acoustic_service=make_acoustic_service(),
                visual_service=make_visual_service(),
            )

            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=service_context,
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(
                    argv=["creator", "create", "--name", "Prueba"],
                    stdout=stdout,
                    stderr=stderr,
                )

        self.assertEqual(code, 0)
        self.assertIn("Creador creado correctamente", stdout.getvalue())

    def test_bootstrap_gui_flag_delegates_to_gui_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = make_diagnostic(root)
            service_context = bootstrap.ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
                service=MagicMock(),
                media_service=MagicMock(),
                audio_service=make_audio_service(),
                transcription_service=make_transcription_service(),
                acoustic_service=make_acoustic_service(),
                visual_service=make_visual_service(),
            )

            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=service_context,
            ), patch(
                "creator_intelligence_studio.presentation.desktop.app.launch_gui",
                return_value=0,
            ) as launch_gui:
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(argv=["--gui"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 0)
        launch_gui.assert_called_once()

    def test_transcription_backend_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = make_diagnostic(root)
            service_context = bootstrap.ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
                service=MagicMock(),
                media_service=MagicMock(),
                audio_service=make_audio_service(),
                transcription_service=make_transcription_service(),
                acoustic_service=make_acoustic_service(),
                visual_service=make_visual_service(),
            )

            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=service_context,
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(argv=["transcription", "backend", "--json"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertIn("backend", payload)

    def test_visual_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = make_diagnostic(root)
            service_context = bootstrap.ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
                service=MagicMock(),
                media_service=MagicMock(),
                audio_service=make_audio_service(),
                transcription_service=make_transcription_service(),
                acoustic_service=make_acoustic_service(),
                visual_service=make_visual_service(),
            )

            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=service_context,
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(argv=["visual", "show", "--video-id", "video-1", "--json"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertIn("status", payload)
