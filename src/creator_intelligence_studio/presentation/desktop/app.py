"""Arranque de la interfaz de escritorio."""

from __future__ import annotations

import os
import sys
import traceback
from typing import Sequence

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.bootstrap import ServiceContext
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from creator_intelligence_studio.presentation.desktop.theme import apply_theme
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel


def _gui_test_mode_enabled() -> bool:
    return os.environ.get("CIS_GUI_TEST_MODE") == "1"


def _sanitize_gui_environment(*, stderr=None) -> None:
    stderr = sys.stderr if stderr is None else stderr
    if _gui_test_mode_enabled():
        return
    ignored_keys = []
    for key in ("QT_QPA_PLATFORM", "CIS_GUI_AUTO_EXIT_MS", "CIS_GUI_TEST_MODE", "CIS_RUN_GUI_TESTS"):
        if key in os.environ:
            os.environ.pop(key, None)
            ignored_keys.append(key)
    if ignored_keys:
        print(
            "Advertencia: se ignoraron variables de pruebas GUI en un arranque interactivo: "
            + ", ".join(sorted(ignored_keys)),
            file=stderr,
        )


def launch_gui(context: ServiceContext, *, stdout=None, stderr=None, argv: Sequence[str] | None = None) -> int:
    """Inicia la aplicacion de escritorio."""

    del stdout
    _sanitize_gui_environment(stderr=stderr)

    try:
        app = QApplication(list(argv or sys.argv))
        app.setApplicationName(context.settings.application_name)
        apply_theme(app)

        workspace = WorkspaceViewModel(
            service=context.service,
            media_service=context.media_service,
            audio_service=context.audio_service,
            transcription_service=context.transcription_service,
            acoustic_service=context.acoustic_service,
            visual_service=context.visual_service,
            multimodal_service=context.multimodal_service,
            clip_service=context.clip_service,
            ai_runtime_service=context.ai_runtime_service,
            render_service=context.render_service,
            subtitle_service=context.subtitle_service,
            analytics_service=context.analytics_service,
            analytics_lab_service=context.analytics_lab_service,
            experiment_service=context.experiment_service,
            recommendation_service=context.recommendation_service,
            planning_service=context.planning_service,
            brief_service=context.brief_service,
            production_service=context.production_service,
            creator_memory_service=context.creator_memory_service,
            creator_language_service=context.creator_language_service,
            creative_packaging_service=context.creative_packaging_service,
            youtube_service=context.youtube_service,
            instagram_service=context.instagram_service,
            tiktok_service=context.tiktok_service,
            personalization_service=context.personalization_service,
            model_service=context.model_service,
            evaluation_service=context.evaluation_service,
            diagnostic=context.diagnostic,
            settings=context.settings,
            paths=context.paths,
        )
        window = MainWindow(workspace)
        window.show()
        if str(app.platformName()).lower() != "offscreen":
            window.raise_()
            window.activateWindow()

        auto_exit = os.environ.get("CIS_GUI_AUTO_EXIT_MS") if _gui_test_mode_enabled() else None
        if auto_exit:
            try:
                delay = int(auto_exit)
            except ValueError:
                delay = 0
            if delay > 0:
                QTimer.singleShot(delay, app.quit)
        return app.exec()
    except Exception:
        print("Error inesperado durante el arranque grafico.", file=stderr)
        traceback.print_exc(file=stderr)
        return 1
