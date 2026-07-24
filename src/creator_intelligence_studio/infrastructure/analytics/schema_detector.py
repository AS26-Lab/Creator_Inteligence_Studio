"""Deteccion de schema y sugerencias de mapeo para analytics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.analytics.metric_definitions import default_metric_definitions
from creator_intelligence_studio.domain.analytics.services import normalize_key, spec_aliases_map

from .csv_importer import load_csv_table
from .excel_importer import load_xlsx_table
from .models import SchemaDetectionResult, SchemaFieldSuggestion


_FIELD_ALIASES = {
    "views": ("views", "visualizaciones", "vistas", "reproducciones"),
    "impressions": ("impressions", "impresiones"),
    "reach": ("reach", "alcance"),
    "ctr": ("ctr", "click_through_rate", "tasa_de_clics", "porcentaje_de_clics"),
    "watch_time_minutes": ("watch_time", "watch_time_minutes", "tiempo_de_reproduccion", "minutos_vistos", "total_play_time", "tiempo_total_de_reproduccion"),
    "average_view_duration_seconds": ("average_view_duration", "duracion_media", "avg_view_duration", "average_watch_time", "avg_watch_time", "tiempo_promedio_de_reproduccion"),
    "average_percentage_viewed": ("average_percentage_viewed", "porcentaje_medio_visto"),
    "completion_rate": ("completion_rate", "watched_full_video", "tasa_de_completado"),
    "engaged_views": ("engaged_views", "vistas_con_engagement"),
    "subscribers_gained": ("subscribers_gained", "subscribers gained", "suscriptores_ganados"),
    "followers_gained": ("followers_gained", "followers gained", "seguidores_ganados"),
    "likes": ("likes", "me_gusta"),
    "comments": ("comments", "comentarios"),
    "shares": ("shares", "compartidos"),
    "saves": ("saves", "guardados"),
    "profile_visits": ("profile_visits", "profile visits", "visitas_al_perfil", "profile_views", "profile views", "vistas_de_perfil"),
    "traffic_to_longform": ("traffic_to_longform", "trafico_a_largo"),
    "traffic_from_shorts": ("traffic_from_shorts", "trafico_desde_shorts"),
    "published_at": ("published_at", "published at", "fecha_de_publicacion", "fecha"),
    "title": ("title", "titulo"),
    "external_publication_id": ("video_id", "content_id", "publication_id"),
}


def _guess_target(header: str) -> tuple[str | None, float, tuple[str, ...]]:
    normalized = normalize_key(header)
    for target, aliases in _FIELD_ALIASES.items():
        if normalized == normalize_key(target) or normalized in {normalize_key(alias) for alias in aliases}:
            return target, 1.0, ()
    metric_map = spec_aliases_map(default_metric_definitions())
    if normalized in metric_map:
        return metric_map[normalized], 0.9, ()
    for target, aliases in _FIELD_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return target, 0.6, ("ambiguous_mapping",)
    return None, 0.0, ("unknown_metric",)


def detect_schema(path: Path, *, sheet_name: str | None = None, max_bytes: int = 25_000_000) -> SchemaDetectionResult:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        table = load_csv_table(path, max_bytes=max_bytes, delimiter="\t" if suffix == ".tsv" else None)
    elif suffix == ".xlsx":
        table = load_xlsx_table(path, sheet_name=sheet_name, max_bytes=max_bytes)
    else:
        table = load_csv_table(path, max_bytes=max_bytes)
    suggestions: list[SchemaFieldSuggestion] = []
    ambiguous: list[str] = []
    for header in table.headers:
        target, confidence, warnings = _guess_target(header)
        if target is None:
            ambiguous.append(header)
            continue
        suggestions.append(
            SchemaFieldSuggestion(
                source_field=header,
                target_field=target,
                confidence=confidence,
                transformation="identity",
                origin="auto",
                warning_codes=warnings,
            )
        )
    return SchemaDetectionResult(
        path=path,
        source_type=table.source_type,
        source_fingerprint=table.source_fingerprint,
        source_filename=table.source_filename,
        delimiter=table.delimiter,
        sheet_name=table.sheet_name,
        headers=table.headers,
        suggestions=tuple(suggestions),
        ambiguous_fields=tuple(ambiguous),
        warnings=table.warnings,
        errors=table.errors,
    )
