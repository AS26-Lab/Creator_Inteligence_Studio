"""Arranque de la interfaz de escritorio."""

from __future__ import annotations

import os
import sys
from typing import Sequence

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.bootstrap import ServiceContext
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from creator_intelligence_studio.presentation.desktop.theme import apply_theme
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


def launch_gui(context: ServiceContext, *, stdout=None, stderr=None, argv: Sequence[str] | None = None) -> int:
    """Inicia la aplicacion de escritorio."""

    app = QApplication(list(argv or sys.argv))
    app.setApplicationName(context.settings.application_name)
    apply_theme(app)

    workspace = WorkspaceViewModel(
        service=context.service,
        media_service=context.media_service,
        audio_service=context.audio_service,
        transcription_service=context.transcription_service,
        diagnostic=context.diagnostic,
        settings=context.settings,
        paths=context.paths,
    )
    window = MainWindow(workspace)
    window.show()

    auto_exit = os.environ.get("CIS_GUI_AUTO_EXIT_MS")
    if auto_exit:
        try:
            delay = int(auto_exit)
        except ValueError:
            delay = 0
        if delay > 0:
            QTimer.singleShot(delay, app.quit)

    return app.exec()
