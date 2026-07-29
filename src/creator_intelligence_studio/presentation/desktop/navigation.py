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
        NavigationItem("market", "Market"),
        NavigationItem("creators", "Creadores"),
        NavigationItem("projects", "Proyectos"),
        NavigationItem("videos", "Videos"),
        NavigationItem("youtube", "YouTube"),
        NavigationItem("instagram", "Instagram"),
        NavigationItem("tiktok", "TikTok"),
        NavigationItem("analytics", "Analytics"),
        NavigationItem("analytics_lab", "Analytics Lab"),
        NavigationItem("experiments", "Experiments"),
        NavigationItem("recommendations", "Recommendations"),
        NavigationItem("planning_overview", "Strategic Planning"),
        NavigationItem("planning_objectives", "Objectives"),
        NavigationItem("planning_themes", "Themes"),
        NavigationItem("planning_pillars", "Content Pillars"),
        NavigationItem("planning_initiatives", "Initiatives"),
        NavigationItem("planning_campaigns", "Campaigns"),
        NavigationItem("planning_series", "Series"),
        NavigationItem("planning_roadmap", "Roadmap"),
        NavigationItem("planning_backlog", "Backlog"),
        NavigationItem("planning_capacity", "Capacity"),
        NavigationItem("planning_dependencies", "Dependencies"),
        NavigationItem("planning_milestones", "Milestones"),
        NavigationItem("planning_scenarios", "Scenarios"),
        NavigationItem("planning_reviews", "Reviews"),
        NavigationItem("planning_history", "History"),
        NavigationItem("planning_settings", "Settings"),
        NavigationItem("planning_privacy", "Privacy"),
        NavigationItem("briefs_overview", "Content Briefs"),
        NavigationItem("brief_requests", "Brief Requests"),
        NavigationItem("briefs", "Briefs"),
        NavigationItem("brief_detail", "Brief Detail"),
        NavigationItem("brief_audience", "Audience"),
        NavigationItem("brief_promise_angle", "Promise & Angle"),
        NavigationItem("brief_message", "Message"),
        NavigationItem("brief_structure", "Structure"),
        NavigationItem("brief_claims", "Claims"),
        NavigationItem("brief_packaging", "Packaging"),
        NavigationItem("brief_platform_adaptations", "Platform Adaptations"),
        NavigationItem("brief_references", "References"),
        NavigationItem("brief_rights", "Rights"),
        NavigationItem("brief_assets", "Assets"),
        NavigationItem("brief_preproduction", "Pre-Production"),
        NavigationItem("brief_shot_plan", "Shot Plan"),
        NavigationItem("brief_checklist", "Checklists"),
        NavigationItem("brief_approval_gates", "Approval Gates"),
        NavigationItem("brief_readiness", "Readiness"),
        NavigationItem("brief_risks", "Risks"),
        NavigationItem("brief_reviews", "Reviews"),
        NavigationItem("brief_history", "History"),
        NavigationItem("brief_settings", "Settings"),
        NavigationItem("brief_privacy", "Privacy"),
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
