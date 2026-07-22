# System Architecture - Creator Intelligence Studio

## Capas

```mermaid
flowchart TD
    UI[Presentacion / UI] --> APP[Capa de aplicacion]
    APP --> DOM[Dominio]
    APP --> INF[Infraestructura]
    INF --> STO[Almacenamiento local]
    INF --> GPU[GPU / CUDA]
    INF --> EXT[Proveedores externos]
    APP --> JOBS[Jobs y orquestacion]
```

### Presentacion

- Pantallas, navegacion y estado visual.
- No contiene logica de negocio pesada.
- Consume casos de uso expuestos por la capa de aplicacion.

### Aplicacion

- Coordina casos de uso.
- Valida comandos.
- Orquesta jobs, caché, permisos y progresos.
- Traduce entradas de UI en acciones del dominio.

### Dominio

- Entidades, reglas y politicas.
- Cálculos de negocio.
- Contratos de repositorios y proveedores.
- Separacion de datos de creador, proyecto, video e inspeccion tecnica.

### Infraestructura

- Persistencia local.
- Lectura y escritura de archivos.
- Integracion con GPU/CUDA.
- Integraciones oficiales con plataformas.
- Proveedores externos opcionales.
- Registro, metricas y telemetria local.
- Encapsulacion de `ffprobe` y `ffmpeg` para inspeccion tecnica.

## Modulos

- `Creator Management`
- `Project Management`
- `Media Ingestion`
- `Technical Inspection`
- `Artifact Store`
- `Job Orchestrator`
- `Analysis Pipeline`
- `Insight Engine`
- `Model Registry`
- `Connector Layer`
- `Cost Control`
- `Diagnostics`

## Flujo de datos

1. El usuario registra o importa un video.
2. El sistema guarda metadatos de registro y la ruta absoluta normalizada.
3. Se inspecciona tecnicamente el archivo con `ffprobe` cuando esta disponible.
4. Se guarda un resumen tecnico normalizado y el JSON completo limitado de `ffprobe`.
5. Si `ffmpeg` esta disponible, se genera una miniatura tecnica inicial en caché local.
6. El caché se reutiliza si tamaño y fecha de modificacion siguen vigentes.
7. El resultado pasa a `stale` cuando el archivo cambia despues de la inspeccion.
8. La UI solo consume resultados publicados por la capa de aplicacion.

## Jobs

- ingesta;
- extraccion de audio;
- transcripcion;
- segmentacion;
- analisis visual;
- analisis de voz;
- generacion de insights;
- ranking de clips;
- sincronizacion con plataformas;
- inspeccion tecnica local de medios;
- entrenamiento o evaluacion local cuando aplique.

### Reglas para jobs

- cancelables;
- reintentables con control;
- idempotentes cuando sea posible;
- persistentes;
- observables;
- desacoplados de la UI.

## Almacenamiento

### Local primero

- ruta base configurable;
- separacion por creador y proyecto;
- artefactos derivados versionados;
- metadatos estructurados;
- caché por huella y configuracion.

### Tipos de persistencia

- SQLite para metadatos estructurados;
- archivos binarios para video, audio y proxies;
- archivos JSON para resultados normalizados;
- caché local para inspecciones y miniaturas;
- bitacoras para auditoria.

### Caché tecnica

- `cache/videos/<video-id>/inspection/`
- `cache/videos/<video-id>/thumbnails/`

El video original no se copia ni se modifica.

## Proveedores

- Proveedores internos: reglas, ranking, embeddings, caché y evaluadores.
- Proveedores locales de GPU: CUDA.
- Proveedores externos: opcionales y reemplazables.
- Proveedores multimedia locales: `ffprobe` y `ffmpeg`.

La arquitectura no debe acoplar toda la logica a un proveedor concreto.

## CUDA

- CUDA es la ruta principal de aceleracion en el MVP.
- Si CUDA esta disponible, se prioriza para inferencia y trabajos pesados.
- Si CUDA no esta disponible, la aplicacion debe abrir y ofrecer diagnostico y funciones basicas.
- Las tareas pesadas pueden quedar deshabilitadas o degradadas.

## Fallos

### Clases de fallo

- fallo de GPU;
- fallo de IO;
- fallo de red;
- fallo de proveedor externo;
- fallo de datos invalidos;
- fallo de cancelacion;
- fallo de caché desactualizada;
- fallo de herramienta multimedia;
- fallo de archivo faltante.

### Estrategia

- mensajes claros;
- reintentos limitados;
- degradacion segura;
- preservacion del estado parcial;
- registro de causa raiz;
- no ocultar fallos como exito.

## Observabilidad

- logs estructurados;
- progreso por fase;
- trazabilidad de jobs;
- metricas de tiempo y costo;
- diagnostico de GPU y fallback;
- diagnostico de herramientas multimedia.

## Evolucion futura

- soportar mas backends de inferencia;
- ampliar conectores oficiales;
- agregar modelos especializados;
- incorporar entrenamiento incremental;
- mejorar orquestacion distribuida si fuera necesario.

## Presentacion de escritorio

- `presentation/desktop` concentra la interfaz de escritorio con PySide6.
- La navegacion, las vistas y los dialogos dependen de `WorkspaceViewModel`.
- Los widgets no acceden a SQLite directamente.
- La logica de negocio permanece en `domain/`, `application/` e `infrastructure/`.
- La GUI expone un panel lateral contextual y una barra superior con seleccion de creador y proyecto.

## Sistema visual

- fondo principal: azul marino muy oscuro;
- paneles: azul grisaceo oscuro;
- superficies secundarias: grafito frio;
- acento principal: azul electrico o cian;
- acento de machine learning: violeta;
- exito: teal;
- advertencias: ambar;
- errores: rojo;
- texto principal: blanco suave;
- texto secundario: gris azulado claro.

Reglas:

- bordes redondeados moderados;
- separadores finos;
- sombras sutiles;
- tablas profesionales;
- sin lujo visual;
- sin neon excesivo;
- sin imagenes decorativas.
