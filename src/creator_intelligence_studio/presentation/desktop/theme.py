"""Tema visual de la interfaz de escritorio."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication


BASE_FONT_PT = 11
TITLE_FONT_PT = 20
SECTION_FONT_PT = 14
METRIC_VALUE_PT = 22
SIDEBAR_WIDTH = 220
INSPECTOR_EMPTY_WIDTH = 250
INSPECTOR_ACTIVE_WIDTH = 320
TOPBAR_CONTROL_MIN_WIDTH = 150

PALETTE = {
    "background": "#091521",
    "panel": "#112234",
    "surface": "#17293d",
    "surface_alt": "#203247",
    "border": "#30455e",
    "text": "#edf3f8",
    "text_muted": "#9fb3c9",
    "accent": "#2f8cff",
    "accent_ml": "#8b6bff",
    "success": "#25c5b7",
    "warning": "#f0b44c",
    "error": "#ef5f6c",
}


def stylesheet_path() -> Path:
    """Ruta al archivo QSS."""

    return Path(__file__).with_name("styles.qss")


def load_stylesheet() -> str:
    """Carga la hoja de estilos de escritorio."""

    return stylesheet_path().read_text(encoding="utf-8")


def apply_theme(app: QApplication) -> None:
    """Aplica la identidad visual a la aplicacion Qt."""

    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())
