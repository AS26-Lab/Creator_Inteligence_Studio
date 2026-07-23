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
- `Acoustic Analysis`
- `Visual Analysis`
- `Multimodal Analysis`
- `Clip Ranking`
- `Personalization Data`
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
7. Si existe transcripcion local, puede alimentar fases posteriores como analisis acustico.
8. El analisis acustico puede alimentar una linea temporal multimodal junto con la transcripcion y el analisis visual.
9. El cache se reutiliza si tamano, fecha de modificacion y fingerprints siguen vigentes.
10. El resultado pasa a `stale` cuando el archivo cambia despues de la inspeccion, preparacion, transcripcion, analisis acustico, analisis visual o analisis multimodal.
11. La UI solo consume resultados publicados por la capa de aplicacion.

## Jobs

- ingesta;
- extraccion de audio;
- transcripcion;
- segmentacion;
- analisis acustico;
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
- `cache/acoustics/<video-id>/`

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

## Acoustic analysis layer

- `domain/acoustic_analysis`: entidades, errores, repositorios, value objects y reglas deterministas.
- `application/services/acoustic_analysis_service.py`: orquestacion, estado, persistencia, exportaciones y stale.
- `infrastructure/acoustic_analysis`: lectura WAV, analisis de frames, detector heuristico de voz/silencio, metricas y eventos.
- La capa no interpreta emociones como hechos.
- La salida guarda ventanas temporales, eventos candidatos y metricas globales reutilizables.

## Visual analysis layer

- `domain/visual_analysis`: entidades, errores, repositorios, value objects y reglas tecnicas.
- `application/services/visual_analysis_service.py`: orquestacion, estado, persistencia, exportaciones, keyframes y stale.
- `infrastructure/visual_analysis`: muestreo de frames, metricas, deteccion de cortes, escenas, eventos y extraccion de keyframes con `ffmpeg`.
- La capa evita interpretacion semantica y usa etiquetas tecnicas como `static`, `low_motion`, `possible_black_frame` o `transition_candidate`.
- Los keyframes se almacenan en `cache/videos/<video-id>/visual/` y se ignoran por Git.

## Multimodal analysis layer

- `domain/multimodal_analysis`: entidades, errores, repositorios, value objects y reglas para alineacion temporal, scoring y candidatos tecnicos.
- `application/services/multimodal_analysis_service.py`: orquestacion, cobertura parcial, persistencia, exportaciones y stale.
- `infrastructure/multimodal_analysis`: alineacion de ventanas, normalizacion robusta, scoring, evidencia y fusion de candidatos.
- La capa consume transcripcion, analisis acustico y analisis visual sin acoplar la UI a sus estructuras internas.
- El resultado distingue entre señal observada, metrica derivada, candidato heuristico e interpretacion futura.

## Clip ranking layer

- `domain/clip_ranking`: entidades, errores, repositorios, value objects y reglas de revision humana.
- `application/services/clip_ranking_service.py`: orquestacion, ranking determinista, feedback humano, colecciones, exportaciones y stale.
- `infrastructure/clip_ranking`: scoring basado en reglas, resolucion de solapamientos, diversidad, explicaciones y planificacion de exportacion.
- La capa consume candidatos multimodales ya calculados y no reinterpreta la evidencia base.
- La revision humana se conserva como historial; el ranking es separable del score multimodal original.
- Las exportaciones de plan de clips son locales y no renderizan video.

## Personalization data layer

- `domain/personalization_data`: entidades, errores, repositorios, value objects y reglas para snapshots reproducibles por creador.
- `application/services/personalization_dataset_service.py`: orquestacion de labels, features, quality, readiness, comparacion, archivado y exportaciones.
- `infrastructure/personalization_data`: extraccion de features, construccion de labels, analisis de calidad, estrategia de splits, snapshots, readiness y exportacion.
- La capa recibe feedback humano, candidatos de clip y features derivadas sin entrenar modelos.
- Cada snapshot es inmutable una vez completado y mantiene aislamiento por creador.
- Las exportaciones por defecto omiten texto completo y notas privadas.

## Transcription Layer

La transcripcion local se divide en:

- `domain/transcription`: entidades, errores, repositorios, reglas y value objects.
- `application/services/transcription_service.py`: orquestacion, estados, persistencia y exportaciones.
- `infrastructure/transcription`: loader de DLL NVIDIA, manager de modelos, adaptador `faster-whisper` y exportador.

La capa de dominio no importa `faster_whisper`, `ctranslate2`, Qt ni SQLite.

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
