from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import MagicMock

from creator_intelligence_studio.application import bootstrap
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    DiagnosticState,
    EnvironmentDiagnostic,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_basic_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "config").mkdir()
            (root / "config" / "default.json").write_text(
                json.dumps(
                    {
                        "application_name": "Creator Intelligence Studio",
                        "environment": "development",
                        "log_level": "INFO",
                        "data_directory": "data",
                        "logs_directory": "logs",
                        "models_directory": "models",
                        "artifacts_directory": "artifacts",
                        "preferred_compute_backend": "cuda",
                        "allow_cpu_basic_mode": True,
                        "external_ai_enabled": False,
                    }
                ),
                encoding="utf-8",
            )

            settings = AppSettings.from_file(root / "config" / "default.json")
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = EnvironmentDiagnostic(
                application_name="Creator Intelligence Studio",
                application_version="0.1.0",
                project_root=root,
                os_name="Windows",
                os_version="10",
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

            with patch(
                "creator_intelligence_studio.application.bootstrap.discover_project_root",
                return_value=root,
            ), patch(
                "creator_intelligence_studio.application.bootstrap.load_settings",
                return_value=settings,
            ), patch(
                "creator_intelligence_studio.application.bootstrap.ProjectPaths.from_settings",
                return_value=paths,
            ), patch(
                "creator_intelligence_studio.application.bootstrap.setup_logging",
                return_value=MagicMock(info=lambda *args, **kwargs: None),
            ), patch(
                "creator_intelligence_studio.application.bootstrap.collect_environment_diagnostic",
                return_value=diagnostic,
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                code = bootstrap.run(stdout=stdout, stderr=stderr)

        self.assertEqual(code, 0)
        self.assertIn("Creator Intelligence Studio", stdout.getvalue())

    def test_diagnostic_json_mode_outputs_json(self) -> None:
        diagnostic = EnvironmentDiagnostic(
            application_name="Creator Intelligence Studio",
            application_version="0.1.0",
            project_root=Path("C:/project"),
            os_name="Windows",
            os_version="10",
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
                warnings=(),
            ),
            warnings=(),
            errors=(),
        )
        with patch(
            "creator_intelligence_studio.application.bootstrap._load_context",
            return_value=bootstrap.BootstrapContext(
                settings=AppSettings(
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
                ),
                paths=ProjectPaths.from_settings(
                    Path("C:/project"),
                    AppSettings(
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
                    ),
                ),
                diagnostic=diagnostic,
            ),
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = bootstrap.run(argv=["--diagnostic-json"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 0)
        json.loads(stdout.getvalue())
