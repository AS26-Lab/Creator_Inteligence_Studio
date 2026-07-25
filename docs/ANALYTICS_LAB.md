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
