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
- Orquesta jobs, cache, permisos y progresos.
- Traduce entradas de UI en acciones del dominio.

### Dominio

- Entidades, reglas y politicas.
- Calculos de negocio.
- Contratos de repositorios y proveedores.
- Separacion de datos de creador, proyecto, video, inspeccion tecnica y audio preparado.

### Infraestructura

- Persistencia local.
- Lectura y escritura de archivos.
- Integracion con GPU/CUDA.
- Integraciones oficiales con plataformas.
- Proveedores externos opcionales.
- Registro, metricas y telemetria local.
- Encapsulacion de `ffprobe` y `ffmpeg` para inspeccion tecnica y preparacion de audio.

## Modulos

- `Creator Management`
- `Project Management`
- `Media Ingestion`
- `Technical Inspection`
- `Audio Preparation`
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
5. Si `ffmpeg` esta disponible, se genera una miniatura tecnica inicial en cache local.
6. Si `ffmpeg` esta disponible y existe una inspeccion vigente, se puede preparar un audio normalizado reutilizable en cache local.
7. El cache se reutiliza si tamano y fecha de modificacion siguen vigentes.
8. El resultado pasa a `stale` cuando el archivo cambia despues de la inspeccion o preparacion.
9. La UI solo consume resultados publicados por la capa de aplicacion.

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
- preparacion tecnica local de audio;
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
- cache por huella y configuracion.

### Tipos de persistencia

- SQLite para metadatos estructurados;
- archivos binarios para video, audio y proxies;
- archivos JSON para resultados normalizados;
- cache local para inspecciones, audio y miniaturas;
- bitacoras para auditoria.

### Cache tecnica

- `cache/videos/<video-id>/inspection/`
- `cache/videos/<video-id>/thumbnails/`
- `cache/videos/<video-id>/audio/`

El video original no se copia ni se modifica.

## Proveedores

- Proveedores internos: reglas, ranking, embeddings, cache y evaluadores.
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
- fallo de cache desactualizada;
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

## Preparacion de audio

- la capa de aplicacion coordina `prepare_audio`, `verify_prepared_audio` y la limpieza de cache;
- la infraestructura encapsula la invocacion segura de `ffmpeg` y la validacion del WAV generado;
- la capa de dominio define la seleccion de stream de audio y la configuracion de normalizacion;
- la salida normalizada inicial es WAV PCM signed 16-bit little-endian, mono, 16 kHz;
- el video original nunca se modifica.

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
