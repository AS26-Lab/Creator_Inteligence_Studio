from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.logging.logging_setup import setup_logging
from creator_intelligence_studio.shared.paths import ProjectPaths


class LoggingTests(unittest.TestCase):
    def test_logging_does_not_duplicate_handlers(self) -> None:
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
            logger_one = setup_logging(settings=settings, paths=paths)
            handler_count_one = len(logger_one.handlers)
            logger_two = setup_logging(settings=settings, paths=paths)
            handler_count_two = len(logger_two.handlers)

        self.assertEqual(handler_count_one, handler_count_two)
        self.assertEqual(handler_count_one, 2)

