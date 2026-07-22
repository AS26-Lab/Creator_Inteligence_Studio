# Data Model - Creator Intelligence Studio

## Principios

- Cada creador tiene aislamiento lógico.
- Cada proyecto pertenece a un creador.
- Cada video y cada artefacto derivado son rastreables.
- Cada análisis debe conservar versión, origen y configuración.
- Los datos calculados deben diferenciarse de los observables.

## Identificadores

- Identificadores internos: UUID recomendado.
- Los objetos persistidos deben tener `id` estable.
- Los artefactos y modelos deben incluir `version`.
- Las relaciones deben ser explícitas y no implícitas.

## Entidades principales

### Creator

- identidad del creador;
- preferencias;
- perfil lingüístico;
- benchmarks personales;
- configuración de privacidad;
- rutas y espacio de trabajo.

### Project

- pertenece a un creador;
- agrupa videos, jobs, análisis y feedback;
- define configuración de procesamiento.

### MediaAsset

- video original;
- proxy;
- audio extraído;
- fotogramas;
- miniaturas;
- exportaciones.

### Video

- referencia al archivo original;
- hash;
- duración;
- formato;
- estado de importación;
- vínculo con proyecto.

### Job

- tipo;
- estado;
- prioridad;
- progreso;
- errores;
- timestamps;
- resultados intermedios.

### Analysis

- tipo de análisis;
- fuente;
- versión del pipeline;
- métricas;
- inferencias;
- timestamps;
- confianza.

### Artifact

- transcripción;
- segmentos;
- escenas;
- embeddings;
- eventos;
- recomendaciones;
- reportes;
- salidas del proveedor.

### Model

- nombre;
- versión;
- backend;
- métricas;
- compatibilidad;
- estado;
- ubicación.

### Feedback

- aprobaciones;
- rechazos;
- correcciones;
- comentarios;
- señal de entrenamiento;
- vínculo con resultado o modelo.

### ConnectorAccount

- proveedor;
- ámbito;
- credenciales;
- estado;
- permisos;
- sincronización.

### CostRecord

- tarea;
- proveedor;
- unidad de costo;
- presupuesto;
- consumo;
- decisión de ejecución;
- timestamps.

## Relaciones

```mermaid
erDiagram
    CREATOR ||--o{ PROJECT : owns
    PROJECT ||--o{ VIDEO : contains
    VIDEO ||--o{ JOB : triggers
    JOB ||--o{ ANALYSIS : produces
    ANALYSIS ||--o{ ARTIFACT : emits
    CREATOR ||--o{ FEEDBACK : submits
    PROJECT ||--o{ FEEDBACK : collects
    CREATOR ||--o{ MODEL : personalizes
    PROJECT ||--o{ COST_RECORD : tracks
    CONNECTOR_ACCOUNT ||--o{ JOB : enables
```

## Estados

### Job

- `queued`
- `running`
- `paused`
- `cancelled`
- `failed`
- `completed`

### Analysis

- `draft`
- `partial`
- `final`
- `stale`
- `superseded`

### Model

- `registered`
- `candidate`
- `validated`
- `deprecated`
- `blocked`

## Versionado

- Cada pipeline debe registrar su versión.
- Cada modelo debe registrar su versión.
- Cada resultado debe recordar con qué versión fue generado.
- Las revisiones del usuario crean nueva evidencia sin borrar la anterior.

## Artefactos

Los artefactos mínimos contemplados son:

- original;
- hash;
- proxy;
- audio;
- transcripción;
- segmentos;
- escenas;
- fotogramas clave;
- eventos acústicos;
- características visuales;
- embeddings;
- análisis;
- recomendaciones;
- feedback;
- historial;
- costos;
- tiempos.

## Persistencia recomendada

- metadatos estructurados;
- archivos para binarios pesados;
- índice local para búsqueda;
- manifiestos por proyecto y modelo.

## Pendientes

- formato físico exacto de persistencia;
- motor concreto de almacenamiento;
- estrategia final de migraciones.

