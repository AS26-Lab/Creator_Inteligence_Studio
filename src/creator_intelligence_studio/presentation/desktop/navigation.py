"""Definiciones de navegacion de la interfaz de escritorio."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NavigationItem:
    """Elemento de navegacion lateral."""

    key: str
    label: str
    enabled: bool = True
    badge: str | None = None


def build_navigation_items() -> list[NavigationItem]:
    """Construye la navegacion principal."""

    return [
        NavigationItem("home", "Inicio"),
        NavigationItem("creators", "Creadores"),
        NavigationItem("projects", "Proyectos"),
        NavigationItem("videos", "Videos"),
        NavigationItem("analysis", "Análisis", enabled=False, badge="Próximamente"),
        NavigationItem("clips", "Clips", enabled=False, badge="Próximamente"),
        NavigationItem("thumbnails", "Miniaturas", enabled=False, badge="Próximamente"),
        NavigationItem("audience", "Audiencia", enabled=False, badge="Próximamente"),
        NavigationItem("trends", "Tendencias", enabled=False, badge="Próximamente"),
        NavigationItem("script_voice", "Script & Voice", enabled=False, badge="Próximamente"),
        NavigationItem("models", "Modelos", enabled=False, badge="Próximamente"),
        NavigationItem("system", "Sistema"),
    ]
