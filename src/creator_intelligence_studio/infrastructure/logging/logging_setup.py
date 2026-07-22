"""Configuracion de logging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.paths import ProjectPaths

LOGGER_NAME = "creator_intelligence_studio"
_MANAGED_ATTR = "_cis_managed"
_CURRENT_LOG_FILE: Path | None = None


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _MANAGED_ATTR, False):
            logger.removeHandler(handler)
            handler.close()


def setup_logging(settings: AppSettings, paths: ProjectPaths) -> logging.Logger:
    """Inicializa logging de consola y archivo sin duplicar handlers."""

    global _CURRENT_LOG_FILE

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    logger.propagate = False

    log_file = paths.logs_directory / "creator_intelligence_studio.log"
    if _CURRENT_LOG_FILE != log_file:
        _remove_managed_handlers(logger)

    if any(getattr(handler, _MANAGED_ATTR, False) for handler in logger.handlers):
        _CURRENT_LOG_FILE = log_file
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(formatter)
    setattr(console_handler, _MANAGED_ATTR, True)
    logger.addHandler(console_handler)

    paths.logs_directory.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8", delay=True)
    file_handler.setFormatter(formatter)
    setattr(file_handler, _MANAGED_ATTR, True)
    logger.addHandler(file_handler)

    _CURRENT_LOG_FILE = log_file
    logger.debug("Logging inicializado en %s", log_file)
    return logger
