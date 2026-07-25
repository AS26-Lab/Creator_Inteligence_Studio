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
- Mantiene estado de interfaz, workflow guiado, preferencias y tareas persistidas.

### Aplicacion

- Coordina casos de uso.
- Valida comandos.
- Orquesta jobs, cache, permisos y progresos.
- Traduce entradas de UI en acciones del dominio.
- Expone el pipeline status agregado por video, el task center y la persistencia de UI.

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
- `Clip Render Store`
- `Analysis Pipeline`
- `Workflow Shell`
- `Subtitle Editing`
- `Insight Engine`
- `Acoustic Analysis`
- `Visual Analysis`
- `Multimodal Analysis`
- `Clip Ranking`
- `Clip Rendering`
- `Personalization Data`
- `Creator Memory`
- `Creative Packaging`
- `YouTube Read-Only Integration`
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
12. Los clips aprobados pueden renderizarse localmente sin modificar el archivo fuente; la verificacion de salida guarda metadatos tecnicos y el Task Center conserva el historial.
13. Los subtitulos se generan a partir de la transcripcion vigente o de un clip aprobado; la edicion de subtitulos no reescribe la transcripcion original y la exportacion se verifica antes de considerarse valida.
14. La integracion de YouTube en modo solo lectura autentica con OAuth de escritorio, sincroniza canales y contenidos remotos sin escrituras, conserva snapshots historicos y alimenta Analytics y Thumbnail Lab con referencias y metricas oficiales.

## Workflow shell de escritorio

- `application/services/video_pipeline_service.py` agrega el estado publico de cada video sin duplicar la logica de los servicios base.
- `presentation/desktop/ui_state.py` persiste la seleccion activa, la pagina actual, preferencias iniciales y tareas de fondo.
- `presentation/desktop/views/workflow_view.py` presenta la accion recomendada, el progreso y las etapas del pipeline.
- `presentation/desktop/views/task_center_view.py` expone tareas persistidas e interrupciones visibles al usuario.
- `presentation/desktop/views/clip_ranking_view.py` expone el flujo de render local y de colecciones sobre candidatos aprobados.
- `presentation/desktop/views/subtitle_editor_view.py` expone generacion, edicion, importacion y exportacion de subtitulos.
- `presentation/desktop/views/clip_ranking_view.py` y `presentation/desktop/views/task_center_view.py` tambien exponen entregas de subtitulos sidecar o burn-in como tareas persistidas.
- `application/services/clip_rendering_service.py` coordina jobs de render, entregas de subtitulos, manifests y verificacion de salida.
- `infrastructure/clip_rendering/subtitle_rendering.py` centraliza estilos, escape ASS y hashes de configuracion de subtitulos.
- `presentation/desktop/views/thumbnail_lab_view.py` expone titulo, miniatura, referencia, concepto, prompt y review.
- `presentation/desktop/views/youtube_integration_view.py` expone conexion, canales, sincronizacion, videos remotos, enlaces, metricas, historial, cuota y privacidad.
- `application/services/creative_packaging_service.py` coordina el analisis creativo de packaging y las exportaciones asociadas.
- `infrastructure/creative_packaging/` centraliza heuristicas deterministas para titulos, miniaturas, pares, conceptos, prompts y referencias.
- `application/services/youtube_integration_service.py` coordina OAuth de escritorio, importacion de canal, sincronizacion incremental, metricas y enlaces locales.
- `infrastructure/youtube/` centraliza el cliente OAuth, el almacenamiento seguro de credenciales, los clientes oficiales de YouTube y la gestion de cuota y reintentos.
- `presentation/desktop/views/onboarding_view.py` ofrece una guia breve reabrible.
- `presentation/desktop/views/preferences_dialog.py` permite configurar rutas y preferencias de UX sin mover datos automaticamente.

## Jobs

- ingesta;
- extraccion de audio;
- transcripcion;
- segmentacion;
- analisis acustico;
- analisis visual;
- analisis de voz;
- subtitulos;
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
- `cache/subtitles/<video-id>/`

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

## Creator memory layer

- `domain/creator_memory`: entidades, errores, repositorios, value objects, tipos de memoria, evidencia y perfil sin dependencia de GUI, SQLite, APIs, LLMs o ML.
- `application/services/creator_profile_service.py`: lectura y actualizacion del perfil creativo del creador.
- `application/services/creator_memory_service.py`: traits, ejemplos, vocabulario, reglas de estilo, limites, snapshots, retrieval y feedback.
- `infrastructure/creator_memory`: construccion de perfil, vinculacion de evidencia, deteccion de contradicciones, indexacion, retrieval y snapshots.
- `infrastructure/persistence/sqlite_creator_memory_repository.py`: persistencia local de perfiles, traits, ejemplos, vocabulario, reglas, limites, snapshots y feedback.
- La capa conserva observaciones, evidencia positiva y contradictoria, y no convierte una muestra aislada en regla definitiva.
- La memoria del creador se mantiene separada de analytics, experiments y learning records.

## Creator language layer

- `domain/creator_language`: entidades, errores, repositorios, value objects y tipos de analisis linguisticos y narrativos sin dependencia de GUI, SQLite, APIs, LLMs, ML ni embeddings externos.
- `application/services/creator_language_service.py`: corpus, analisis, perfil narrativo, candidatos para Creator Memory, retrieval local y exportaciones.
- `infrastructure/creator_language`: tokenizacion determinista, segmentacion de frases, analisis de vocabulario, muletillas, estructura narrativa y pausas.
- `infrastructure/persistence/sqlite_creator_language_repository.py`: persistencia local de corpora, fuentes, corridas, metricas, patrones, evidencia, candidatos y snapshots.
- La capa trabaja solo con fuentes locales seleccionadas y no escribe de forma silenciosa en Creator Memory.
- La salida de la capa sirve como base candidata para revision humana y versionado posterior.

## Transcription Layer

La transcripcion local se divide en:

- `domain/transcription`: entidades, errores, repositorios, reglas y value objects.
- `application/services/transcription_service.py`: orquestacion, estados, persistencia y exportaciones.
- `infrastructure/transcription`: loader de DLL NVIDIA, manager de modelos, adaptador `faster-whisper` y exportador.

La capa de dominio no importa `faster_whisper`, `ctranslate2`, Qt ni SQLite.

## Subtitle layer

- `domain/subtitles`: entidades, errores, repositorios, value objects y reglas editoriales.
- `application/services/subtitle_service.py`: orquestacion, generacion, edicion, importacion, exportacion, historial y stale.
- `infrastructure/subtitles`: segmentacion, normalizacion, validacion de tiempos, importadores y exportadores.
- La capa consume transcripciones existentes y no altera el motor de transcripcion.
- Los tracks de clip preservan tiempos absolutos como metadata y exportan tiempo relativo cuando corresponde.

## Presentacion de escritorio

- `presentation/desktop` concentra la interfaz de escritorio con PySide6.
- La navegacion, las vistas y los dialogos dependen de `WorkspaceViewModel`.
- Los widgets no acceden a SQLite directamente.
- La logica de negocio permanece en `domain/`, `application/` e `infrastructure/`.
- La GUI expone un panel lateral contextual y una barra superior con seleccion de creador y proyecto.
- El flujo principal se organiza alrededor de Home, Videos, Workflow, Task Center y Onboarding.

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

## Personalization Models

- `domain/personalization_models`: entidades, errores, repositorios, value objects y reglas del baseline local.
- `application/services/personalization_training_service.py`: validacion del snapshot, entrenamiento, evaluacion, activacion y scoring separado.
- `infrastructure/personalization_models`: pipeline de features, entrenamiento de regresion logistica, evaluacion, comparadores, explicaciones y artefactos.
- `infrastructure/persistence/sqlite_personalization_model_repository.py`: persistencia local del registro de modelos, metricas, predicciones y comparaciones.
- Los artefactos se cargan solo desde el almacen local administrado por la aplicacion.
- joblib se usa solo para artefactos locales de confianza.

### Evaluacion operativa

- `domain/operational_evaluation`: entidades, errores, repositorios, value objects y reglas de escenarios reproducibles.
- `application/services/operational_evaluation_service.py`: orquestacion de escenarios, tiempos, assertions, cache, reportes, retry, cancelacion y limpieza.
- `infrastructure/operational_evaluation`: generacion de assets demo, temporizador de etapas, muestreo de recursos, motor de assertions, builder de reportes y orquestador.
- `infrastructure/persistence/sqlite_operational_evaluation_repository.py`: persistencia local de runs, stages, metricas, assertions y artefactos.

### Analytics foundation

- `domain/analytics`: entidades, errores, repositorios, services y value objects sin dependencia de GUI, SQLite, CSV o Excel.
- `application/services/analytics_import_service.py`: importacion, normalizacion, deduplicacion, persistencia y reportes.
- `application/services/analytics_query_service.py`: consultas y exportacion normalizada.
- `infrastructure/analytics`: CSV, XLSX, deteccion de schema, field mapping, validacion, normalizacion y reportes.
- `infrastructure/persistence/sqlite_analytics_repository.py`: persistencia SQLite de plataformas, canales, publicaciones, metricas, snapshots, imports y mappings.

### Creator language

- corpus por creador con fuentes locales seleccionadas;
- metricas de lenguaje, vocabulario, frases, narrativa, ritmo y pausas;
- comparacion por plataforma y tipo de contenido cuando la muestra lo permite;
- candidates revisables para Creator Memory;
- profile history y snapshots versionados;
- Task Center para analisis, snapshot y exportacion.

## Experiments and Verifiable Learning

- `domain/experiments`: entidades, errores, repositorios, value objects y tipos de decision/aprendizaje sin dependencia de GUI, SQLite, CSV, Excel, APIs o LLM.
- `application/services/experiment_service.py`: registro de recomendaciones, decisiones, ejecucion, evaluacion, learning y reportes reproducibles.
- `infrastructure/experiments`: calculo de confianza, deteccion de contradicciones, evaluacion, matching de outcomes y builder de reportes.
- `infrastructure/persistence/sqlite_experiment_repository.py`: persistencia SQLite de experimentos, assignments, evaluaciones, aprendizajes y reportes.
- `presentation/desktop/views/experiments_view.py` y `presentation/desktop/views/learning_memory_view.py`: interfaz operativa para la fase.
