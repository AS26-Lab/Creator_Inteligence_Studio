from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.paths import (
    ProjectPaths,
    discover_project_root,
    resolve_configured_path,
)


class PathTests(unittest.TestCase):
    def test_discover_project_root(self) -> None:
        root = discover_project_root()
        self.assertTrue((root / "pyproject.toml").exists())
        self.assertTrue((root / "docs").exists())

    def test_resolve_configured_path(self) -> None:
        root = Path("C:/project")
        self.assertEqual(resolve_configured_path(root, "data"), root / "data")

    def test_controlled_directory_creation(self) -> None:
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
            paths.ensure_runtime_directories()
            self.assertTrue(paths.data_directory.exists())
            self.assertTrue(paths.logs_directory.exists())
            self.assertTrue(paths.models_directory.exists())
            self.assertTrue(paths.artifacts_directory.exists())

