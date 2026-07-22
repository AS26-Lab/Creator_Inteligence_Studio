from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
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
