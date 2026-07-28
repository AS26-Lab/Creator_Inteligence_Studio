# Analytics Data Foundation

## Scope

Base manual de analitica historica para Creator Intelligence Studio.

## What it does

- registra plataformas, canales y publicaciones;
- importa CSV y XLSX;
- normaliza metricas observadas;
- conserva snapshots historicos;
- detecta duplicados y filas invalidas;
- exporta datos normalizados;
- mantiene trazabilidad a la fuente.

## What it does not do

- no usa APIs externas;
- no hace causalidad;
- no genera recomendaciones;
- no introduce ML;
- no reemplaza la revision humana;
- no confunde ausencia con cero.

## Platforms

- `youtube_longform`
- `youtube_short`
- `instagram_reel`
- `tiktok`
- `manual_other`

## Next phase

Analytics Lab consume estas publicaciones normalizadas para cohortes, comparaciones y findings sin sobreescribir snapshots.
Experiments and Verifiable Learning consume recomendaciones, decisiones y evaluaciones como memoria estructurada.
YouTube Read-Only Integration puede alimentar estos registros con canales, videos, thumbnails y metricas oficiales sin exponer permisos de escritura.

Audience Model Foundation consume estas mismas publicaciones, snapshots y metricas importadas para modelar comportamiento observado por creador, sin inventar demografia, sin PII y sin convertir fuentes de trafico en identidad.
## TikTok Read-Only Integration

TikTok Read-Only Integration feeds the same local foundation with creator-scoped profile snapshots, public video metadata, public counters and explicit unavailable states. Manual CSV/XLSX imports continue to hold private analytics that Display API does not expose. Missing TikTok analytics never become zero.
## Instagram Read-Only Integration

Instagram Read-Only Integration adds imported account and media snapshots to the same local foundation. Instagram metrics remain semantically separate from YouTube and manual imports, and missing Instagram data stays missing instead of being forced to zero.

## Market and Trend Intelligence Foundation

Market and Trend Intelligence Foundation uses this same local foundation as historical evidence and keeps public cumulative counters separate from manual period imports and private analytics.
Strategic Planning can reference analytics snapshots and metric availability when selecting objectives, metrics and review checkpoints.
