# Experiments and Verifiable Learning

## Scope

Registro controlado de recomendacion, decision humana, ejecucion real, evaluacion y memoria de aprendizaje verificable.

## What it does

- registra recomendaciones existentes o manuales;
- registra decisiones humanas sobre esas recomendaciones;
- registra la variante realmente usada;
- compara control y treatment con ventanas comparables;
- genera evaluaciones, outcomes y reportes reproducibles;
- conserva aprendizajes provisionales con evidencia y revisiones;
- preserva el historial sin promover reglas automaticamente.

## What it does not do

- no genera recomendaciones con LLM;
- no entrena ML;
- no activa experimentos automaticos;
- no convierte correlacion en causalidad;
- no modifica reglas centrales ni preferencias historicas;
- no usa APIs externas.

## Notes

La fase separa siempre recomendacion, decision, ejecucion, resultado, interpretacion, aprendizaje provisional y regla confirmada.

La siguiente fase es Creator Memory / Creator Profile Foundation, que reutiliza aprendizajes y evidencia para construir memoria creativa versionada por creador sin convertirla en generacion automatica.
Creator Language / Narrative Profile se ubica despues como capa local de analisis linguistico y narrativo, y solo propone candidatos revisables hacia Creator Memory.

Thumbnail Lab and Titles Foundation can link packaging versions, decisions, experiments, and outcomes so that later learning can retain what was approved, rejected, or selected.
