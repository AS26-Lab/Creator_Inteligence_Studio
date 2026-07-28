# Analytics Lab

## Scope

Primera capa de comparacion estadistica y aprendizaje analitico sobre publicaciones historicas.

## What it does

- define cohortes comparables;
- calcula medianas, percentiles, MAD y robust z-score;
- compara publicaciones con ventanas compatibles;
- detecta anomalias explicables;
- genera findings trazables con evidencia, limite y confianza;
- produce reportes semanales reproducibles;
- conserva cache y reproducibilidad por fingerprint.

## What it does not do

- no afirma causalidad;
- no usa APIs externas;
- no entrena modelos;
- no genera recomendaciones automaticas;
- no reemplaza la revision humana;
- no compara plataformas o metricas no equivalentes sin warning.

## Notes

Analytics Lab consume la base multiplataforma de `docs/ANALYTICS_DATA_FOUNDATION.md` y separa hechos, inferencias e hipotesis.
Cuando YouTube Read-Only Integration esta activa, los imports remotos y los snapshots historicos pasan a ser evidencia adicional para cohortes, comparaciones y findings, sin mezclar metricas observadas con causalidad.

Thumbnail Lab and Titles Foundation uses these historical metrics, cohorts, and percentiles to judge whether a title or thumbnail is aligned with the creator's real performance history.

Audience Model Foundation reusa esos mismos insumos como señales agregadas para acquisition, consumption, conversion, loyalty, engagement, affinities y contradictions, siempre con lenguaje de evidencia y no de personas individuales.
## Instagram Read-Only Integration

Instagram Read-Only Integration feeds Analytics Lab only through imported local snapshots and official insights. It does not add write operations, scraping, inferred demographics or metric equivalence across platforms.
## TikTok Read-Only Integration

TikTok Read-Only Integration feeds Analytics Lab only through compatible public snapshots and cumulative counters. Private watch time, completion, retention and traffic source remain manual imports or unavailable states; they are not derived from public views.

## Market and Trend Intelligence Foundation

Market and Trend Intelligence Foundation contributes external trend signals as local evidence, but Analytics Lab keeps cumulative public counters, manual period imports and platform-specific semantics separate.
Strategic Planning links to Analytics Lab reports for measurement and review, but does not invent missing metrics.
