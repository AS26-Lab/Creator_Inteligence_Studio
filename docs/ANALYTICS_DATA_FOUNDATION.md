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
