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
        NavigationItem("integrations", "Integrations"),
        NavigationItem("creators", "Creadores"),
        NavigationItem("projects", "Proyectos"),
        NavigationItem("videos", "Videos"),
        NavigationItem("youtube", "YouTube"),
        NavigationItem("instagram", "Instagram"),
        NavigationItem("tiktok", "TikTok"),
        NavigationItem("analytics", "Analytics"),
        NavigationItem("analytics_lab", "Analytics Lab"),
        NavigationItem("experiments", "Experiments"),
        NavigationItem("creator_memory", "Creator Memory"),
        NavigationItem("creator_language", "Creator Language"),
        NavigationItem("workflow", "Workflow"),
        NavigationItem("tasks", "Task Center"),
        NavigationItem("onboarding", "Onboarding"),
        NavigationItem("transcription", "Transcripcion"),
        NavigationItem("subtitles", "Subtitulos"),
        NavigationItem("analysis", "Analisis"),
        NavigationItem("visual", "Analisis visual"),
        NavigationItem("multimodal", "Analisis multimodal"),
        NavigationItem("clips", "Clips"),
        NavigationItem("personalization", "Personalizacion"),
        NavigationItem("evaluation", "Evaluacion operativa"),
        NavigationItem("thumbnails", "Thumbnail Lab"),
        NavigationItem("audience", "Audiencia"),
        NavigationItem("trends", "Tendencias", enabled=False, badge="Proximamente"),
        NavigationItem("script_voice", "Script & Voice", enabled=False, badge="Proximamente"),
        NavigationItem("models", "Modelos"),
        NavigationItem("system", "Sistema"),
    ]
