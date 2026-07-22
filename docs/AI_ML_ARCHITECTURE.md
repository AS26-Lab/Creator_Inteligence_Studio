# AI / ML Architecture - Creator Intelligence Studio

## Principios

- empezar con reglas, estadísticas y similitud;
- usar embeddings y ranking antes que modelos complejos;
- aprender con feedback humano;
- evaluar de forma reproducible;
- mantener independencia de proveedor;
- priorizar CUDA cuando exista GPU compatible;
- permitir fallback limitado sin GPU.

## Componentes

### Rules Engine

- reglas explícitas;
- heurísticas auditables;
- decisiones deterministas cuando sea posible.

### Embeddings

- representación semántica de texto, clips y artefactos;
- base para búsqueda, similitud y ranking;
- almacenamiento versionado.

### Classifiers

- clasificación de segmentos;
- detección de categorías;
- riesgo de texto artificial;
- riesgo de caída de retención;
- compatibilidad con voz del creador.

### Rankers

- ranking de clips;
- ranking de hooks;
- ranking de recomendaciones;
- ranking de candidatos por contexto.

## Datasets

- ejemplos aprobados;
- ejemplos rechazados;
- correcciones;
- datos de rendimiento;
- resultados de análisis;
- contexto del creador;
- etiquetas humanas cuando existan.

Los datasets deben quedar separados por creador cuando correspondan.

## Entrenamiento

- entrenamiento incremental o por lotes;
- control de versión de datos;
- control de versión de modelo;
- registro de métricas;
- comparación con baseline.

No se contempla entrenar un modelo fundacional desde cero.

## Evaluación

- precisión;
- recall;
- F1;
- correlación con feedback;
- utilidad operativa;
- estabilidad entre versiones;
- costo computacional;
- latencia.

## Model Registry

- nombre del modelo;
- versión;
- backend;
- entradas esperadas;
- salidas;
- métricas;
- estado;
- compatibilidad;
- ubicación local.

## Versionado

- versiones de dataset;
- versiones de features;
- versiones de modelo;
- versiones de pipeline;
- versiones de evaluadores.

## CUDA

- inferencia acelerada como primera elección;
- entrenamiento acelerado cuando sea viable;
- control de memoria;
- control de batch;
- fallback de CPU para tareas básicas.

## Proveedores externos

- uso opcional;
- no deben ser el único camino;
- deben producir salidas estructuradas cuando sea posible;
- sus resultados deben almacenarse como artefactos trazables.

## Reducción gradual de dependencia

1. empezar con reglas y ranking;
2. añadir embeddings;
3. registrar feedback;
4. entrenar modelos locales por caso de uso;
5. reservar proveedores externos para cobertura, comparación o generación opcional.

## Pendientes

- framework concreto de ML;
- esquema final de features;
- formato exacto del registry.

