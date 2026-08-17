# Multi-Platform Integration Consolidation

Fecha de consulta y consolidacion: 2026-07-27.

Esta fase introduce una capa comun para YouTube, Instagram, TikTok y fuentes manuales sin mezclar datos ni semanticas.

## Alcance

- registry comun de conexiones;
- health y capabilities por plataforma;
- disponibilidad de datos automaticos y manuales;
- sync groups unificados;
- reportes y privacidad consolidados;
- sin escritura remota, scraping ni Research API.

## Contratos

- cada conector nativo sigue siendo la fuente de verdad;
- la capa comun solo agrega resumen, estado, salud, capacidades y disponibilidad;
- los snapshots privados y manuales siguen separados;
- el publishing sigue deshabilitado.

## Fase siguiente

Multi-Platform Integration Consolidation es la fase v35-E. Sigue a YouTube Read-First, Instagram Read-Only y TikTok Read-Only, y prepara el terreno para `Market / Trend Intelligence Foundation` (v36) sin iniciar esa fase.
Strategic Planning can inspect platform snapshot state for capacity and balance, while preserving the connector layer as read-only in this phase.

The same platform state can be reused by [`docs/CONTENT_BRIEF_AND_PRE_PRODUCTION_FOUNDATION.md`](docs/CONTENT_BRIEF_AND_PRE_PRODUCTION_FOUNDATION.md) to shape platform-specific brief adaptations.
