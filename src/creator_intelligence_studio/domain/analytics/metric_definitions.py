"""Catalogo normalizado inicial de metricas de analytics."""

from __future__ import annotations

from dataclasses import dataclass

from .value_objects import AnalyticsAggregationType, AnalyticsMetricCategory, AnalyticsValueType


@dataclass(frozen=True, slots=True)
class AnalyticsMetricDefinitionSpec:
    metric_key: str
    display_name: str
    category: AnalyticsMetricCategory
    unit: str
    value_type: AnalyticsValueType
    aggregation_type: AnalyticsAggregationType
    higher_is_better: bool | None
    description: str
    aliases: tuple[str, ...]
    applicability: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_key": self.metric_key,
            "display_name": self.display_name,
            "category": self.category.value,
            "unit": self.unit,
            "value_type": self.value_type.value,
            "aggregation_type": self.aggregation_type.value,
            "higher_is_better": self.higher_is_better,
            "description": self.description,
            "aliases": list(self.aliases),
            "applicability": list(self.applicability),
        }


def default_metric_definitions() -> tuple[AnalyticsMetricDefinitionSpec, ...]:
    discovery = AnalyticsMetricCategory.DISCOVERY
    attention = AnalyticsMetricCategory.ATTENTION
    conversion = AnalyticsMetricCategory.CONVERSION
    interaction = AnalyticsMetricCategory.INTERACTION
    relation = AnalyticsMetricCategory.RELATION
    context = AnalyticsMetricCategory.CONTEXT
    numeric = AnalyticsValueType.NUMERIC
    text = AnalyticsValueType.TEXT
    category = AnalyticsValueType.CATEGORY
    latest = AnalyticsAggregationType.LATEST
    sum_ = AnalyticsAggregationType.SUM
    avg = AnalyticsAggregationType.AVG
    max_ = AnalyticsAggregationType.MAX
    all_platforms = ("youtube_longform", "youtube_short", "instagram_reel", "tiktok", "manual_other")
    youtube_family = ("youtube_longform", "youtube_short")
    short_video_platforms = ("youtube_short", "instagram_reel", "tiktok", "manual_other")
    social_platforms = ("instagram_reel", "tiktok", "manual_other")

    return (
        AnalyticsMetricDefinitionSpec("views", "Views", discovery, "count", numeric, sum_, True, "Visualizaciones o reproducciones observadas.", ("views", "visualizaciones", "vistas", "reproducciones"), all_platforms),
        AnalyticsMetricDefinitionSpec("impressions", "Impressions", discovery, "count", numeric, sum_, True, "Veces que la publicacion fue mostrada.", ("impressions", "impresiones"), youtube_family),
        AnalyticsMetricDefinitionSpec("reach", "Reach", discovery, "count", numeric, sum_, True, "Alcance unico observado.", ("reach", "alcance"), social_platforms),
        AnalyticsMetricDefinitionSpec("ctr", "CTR", discovery, "percent", numeric, avg, True, "Tasa de clics observada.", ("ctr", "click-through rate", "tasa de clics", "porcentaje de clics"), ("youtube_longform",)),
        AnalyticsMetricDefinitionSpec("unique_viewers", "Unique viewers", discovery, "count", numeric, max_, True, "Espectadores unicos observados.", ("unique_viewers", "espectadores unicos"), youtube_family),
        AnalyticsMetricDefinitionSpec("traffic_source", "Traffic source", discovery, "category", category, latest, None, "Fuente de trafico principal observada.", ("traffic_source", "fuente de trafico"), youtube_family),
        AnalyticsMetricDefinitionSpec("watch_time_minutes", "Watch time minutes", attention, "minutes", numeric, sum_, True, "Tiempo total de reproduccion observado.", ("watch time", "watch_time_minutes", "tiempo de reproduccion", "minutos vistos"), all_platforms),
        AnalyticsMetricDefinitionSpec("average_view_duration_seconds", "Average view duration seconds", attention, "seconds", numeric, avg, True, "Duracion media de vision por reproduccion.", ("average view duration", "duracion media", "avg_view_duration"), youtube_family),
        AnalyticsMetricDefinitionSpec("average_percentage_viewed", "Average percentage viewed", attention, "percent", numeric, avg, True, "Porcentaje medio visto.", ("average percentage viewed", "porcentaje medio visto"), all_platforms),
        AnalyticsMetricDefinitionSpec("retention_30_seconds", "Retention 30 seconds", attention, "percent", numeric, avg, True, "Retencion a 30 segundos.", ("retention_30_seconds", "retention 30s", "retencion 30 segundos"), youtube_family),
        AnalyticsMetricDefinitionSpec("completion_rate", "Completion rate", attention, "percent", numeric, avg, True, "Tasa de completado observada.", ("completion_rate", "tasa de completado", "completion rate"), short_video_platforms),
        AnalyticsMetricDefinitionSpec("engaged_views", "Engaged views", attention, "count", numeric, sum_, True, "Vistas con engagement observadas.", ("engaged_views", "vistas con engagement"), short_video_platforms),
        AnalyticsMetricDefinitionSpec("rewatch_rate", "Rewatch rate", attention, "ratio", numeric, avg, True, "Tasa de re-vision observada.", ("rewatch_rate", "tasa de re-vision"), short_video_platforms),
        AnalyticsMetricDefinitionSpec("subscribers_gained", "Subscribers gained", conversion, "count", numeric, sum_, True, "Suscriptores ganados observados.", ("subscribers gained", "subscribers_gained", "suscriptores ganados"), youtube_family + social_platforms),
        AnalyticsMetricDefinitionSpec("subscribers_lost", "Subscribers lost", conversion, "count", numeric, sum_, False, "Suscriptores perdidos observados.", ("subscribers lost", "subscribers_lost", "suscriptores perdidos"), youtube_family),
        AnalyticsMetricDefinitionSpec("followers_gained", "Followers gained", conversion, "count", numeric, sum_, True, "Seguidores ganados observados.", ("followers gained", "followers_gained", "seguidores ganados"), social_platforms),
        AnalyticsMetricDefinitionSpec("profile_visits", "Profile visits", conversion, "count", numeric, sum_, True, "Visitas al perfil observadas.", ("profile_visits", "profile visits", "visitas al perfil"), social_platforms),
        AnalyticsMetricDefinitionSpec("returning_viewers", "Returning viewers", conversion, "count", numeric, max_, True, "Espectadores recurrentes observados.", ("returning_viewers", "espectadores recurrentes"), youtube_family),
        AnalyticsMetricDefinitionSpec("likes", "Likes", interaction, "count", numeric, sum_, True, "Me gusta observados.", ("likes", "me gusta"), all_platforms),
        AnalyticsMetricDefinitionSpec("comments", "Comments", interaction, "count", numeric, sum_, True, "Comentarios observados.", ("comments", "comentarios"), all_platforms),
        AnalyticsMetricDefinitionSpec("shares", "Shares", interaction, "count", numeric, sum_, True, "Compartidos observados.", ("shares", "compartidos"), all_platforms),
        AnalyticsMetricDefinitionSpec("saves", "Saves", interaction, "count", numeric, sum_, True, "Guardados observados.", ("saves", "guardados"), social_platforms),
        AnalyticsMetricDefinitionSpec("dislikes", "Dislikes", interaction, "count", numeric, sum_, False, "No me gusta observados cuando existan.", ("dislikes", "no me gusta"), youtube_family),
        AnalyticsMetricDefinitionSpec("traffic_from_shorts", "Traffic from shorts", relation, "count", numeric, sum_, True, "Trafico derivado desde shorts.", ("traffic_from_shorts", "trafico desde shorts"), youtube_family),
        AnalyticsMetricDefinitionSpec("traffic_to_longform", "Traffic to longform", relation, "count", numeric, sum_, True, "Trafico derivado hacia contenido largo.", ("traffic_to_longform", "trafico a largo"), youtube_family),
        AnalyticsMetricDefinitionSpec("related_video_clicks", "Related video clicks", relation, "count", numeric, sum_, True, "Clicks hacia videos relacionados.", ("related_video_clicks", "related video clicks"), youtube_family),
        AnalyticsMetricDefinitionSpec("published_at", "Published at", context, "text", text, latest, None, "Fecha de publicacion observada.", ("published at", "fecha de publicacion", "fecha"), all_platforms),
        AnalyticsMetricDefinitionSpec("duration_seconds", "Duration seconds", context, "seconds", numeric, latest, None, "Duracion del contenido en segundos.", ("duration_seconds", "duration", "duracion"), all_platforms),
        AnalyticsMetricDefinitionSpec("content_type", "Content type", context, "category", category, latest, None, "Tipo de contenido observado.", ("content_type", "tipo de contenido"), all_platforms),
        AnalyticsMetricDefinitionSpec("platform", "Platform", context, "category", category, latest, None, "Plataforma observada.", ("platform", "plataforma"), all_platforms),
        AnalyticsMetricDefinitionSpec("topic", "Topic", context, "text", text, latest, None, "Tema o foco del contenido.", ("topic", "tema"), all_platforms),
        AnalyticsMetricDefinitionSpec("format", "Format", context, "category", category, latest, None, "Formato editorial observado.", ("format", "formato"), all_platforms),
        AnalyticsMetricDefinitionSpec("language", "Language", context, "category", category, latest, None, "Idioma observado.", ("language", "idioma"), all_platforms),
    )
