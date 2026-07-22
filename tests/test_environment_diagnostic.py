from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic import (
    collect_environment_diagnostic,
)
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    DiagnosticState,
    EnvironmentDiagnostic,
    GpuInfo,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


class EnvironmentDiagnosticTests(unittest.TestCase):
    def test_diagnostic_without_nvidia_smi(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = AppSettings(
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
            )
            paths = ProjectPaths.from_settings(root, settings)

            with patch(
                "creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic.shutil.which",
                return_value=None,
            ):
                diagnostic = collect_environment_diagnostic(settings=settings, paths=paths)

        self.assertFalse(diagnostic.nvidia_smi_available)
        self.assertTrue(diagnostic.state.ready_for_basic_mode)
        self.assertTrue(diagnostic.state.cuda_runtime_not_verified)
        self.assertIsNone(diagnostic.cuda_version_reported)

    def test_serialization_to_json(self) -> None:
        diagnostic = EnvironmentDiagnostic(
            application_name="Creator Intelligence Studio",
            application_version="0.1.0",
            project_root=Path("C:/project"),
            os_name="Windows",
            os_version="10",
            os_architecture="64bit",
            python_version="3.11.9",
            python_executable="C:/Python/python.exe",
            cpu_reported="CPU",
            logical_processors=12,
            nvidia_smi_available=True,
            gpu_devices=(GpuInfo(name="NVIDIA", driver_version="576.52", memory_total_mib=8192),),
            nvidia_driver_version="576.52",
            cuda_version_reported="12.9",
            git_available=True,
            git_version="git version 2.54.0",
            free_space_bytes=123,
            preferred_compute_backend="cuda",
            state=DiagnosticState(
                ready_for_basic_mode=True,
                cuda_driver_detected=True,
                cuda_runtime_not_verified=False,
                warnings=("Aviso",),
            ),
            warnings=("Aviso",),
            errors=(),
        )
        payload = diagnostic.to_json()
        parsed = json.loads(payload)
        self.assertEqual(parsed["application_name"], "Creator Intelligence Studio")
        self.assertEqual(parsed["state"]["ready_for_basic_mode"], True)

