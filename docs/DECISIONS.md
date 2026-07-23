# Decisions - Creator Intelligence Studio

## Registro de decisiones confirmadas

| Fecha | Contexto | Decision | Consecuencias | Alternativas descartadas |
|---|---|---|---|---|
| 2026-07-22 | Plataforma base del producto | El MVP se centrara en Windows con NVIDIA CUDA como plataforma principal. | La arquitectura y el rendimiento se optimizan para CUDA primero. | AMD, ROCm, DirectML, Vulkan y macOS fuera del MVP. |
| 2026-07-22 | Base de desarrollo | Python 3.11 sera la version inicial del proyecto. | Se alinea el entorno virtual y la compatibilidad de dependencias a 3.11.x. | Migrar inmediatamente a otra version sin necesidad. |
| 2026-07-22 | Procesamiento | El procesamiento local sera la prioridad siempre que sea viable. | Se reduce dependencia de servicios externos y se conservan datos localmente. | Hacer del cloud el camino principal. |
| 2026-07-22 | Proveedores | Los servicios externos de IA seran opcionales y reemplazables. | El nucleo debe funcionar sin saldo de API. | Acoplar el producto a un unico proveedor. |
| 2026-07-22 | Script & Voice Studio | Script & Voice Studio sera opcional. | El analisis, los proyectos y las metricas no dependen de la generacion de guiones. | Hacer la generacion de guiones obligatoria. |
| 2026-07-22 | Flujo creativo | La generacion de guiones no forma parte obligatoria del flujo de analisis. | El modulo de analisis puede operar sin texto generado. | Mezclar analisis y escritura como un unico flujo inseparable. |
| 2026-07-22 | Datos | Se mantendra separacion estricta entre datos, personalizacion y modelos por creador. | Menor riesgo de contaminacion entre perfiles y mejor privacidad. | Unificar datos de varios creadores en un solo perfil global. |
| 2026-07-22 | Plataforma inicial | YouTube sera la primera plataforma objetivo. | La primera integracion oficial se priorizara para YouTube. | Empezar por una lista amplia de plataformas a la vez. |
| 2026-07-22 | Seguridad | Las APIs oficiales y la seguridad de las cuentas tienen prioridad. | No se disenaran evasiones de CAPTCHA ni fingerprinting. | Automatizaciones encubiertas o evasivas. |
| 2026-07-22 | Resiliencia | La aplicacion debe abrir aunque CUDA no este disponible. | Habra diagnostico y funciones basicas sin GPU, con deshabilitacion o degradacion de tareas pesadas. | Bloquear por completo la apertura sin GPU. |
| 2026-07-22 | Creator Voice | Cuando Creator Voice este activo, un texto generativo no se considerara final sin revision o personalizacion. | El flujo debe incluir revision humana o adaptacion explicita. | Marcar como final cualquier salida de proveedor externo. |
| 2026-07-22 | Persistencia inicial | SQLite sera el almacenamiento estructurado inicial del MVP. | Los datos de creadores, proyectos y videos quedan en una base local simple y portable para desarrollo. | Adoptar una base externa o una solucion mas compleja antes de tiempo. |
| 2026-07-22 | Registro de videos | El registro inicial conserva la ruta absoluta normalizada del archivo y no copia ni procesa el video. | El sistema puede verificar disponibilidad posterior sin mover el archivo original. | Copiar el archivo, generar proxies o abstraer la ruta de forma prematura. |
| 2026-07-22 | Registro de metadatos | No se calcula hash completo durante el registro inicial. | Se mantiene el flujo liviano y se evita leer archivos grandes innecesariamente. | Hacer fingerprint completo en esta mision. |
| 2026-07-22 | Portabilidad futura | Las rutas portables y la biblioteca administrada quedan para una fase futura. | La primera version usa rutas absolutas normalizadas para desarrollo controlado. | Forzar una abstraccion portable prematura. |
| 2026-07-22 | Interfaz de escritorio | PySide6 sera la base de la GUI del MVP y vivira en `presentation/desktop`. | La presentacion queda separada de CLI, dominio e infraestructura. | Integrar la interfaz dentro de la logica de aplicacion o depender de otra biblioteca grafica. |
| 2026-07-22 | Inspeccion tecnica | `ffprobe` sera la herramienta requerida para la inspeccion tecnica local; `ffmpeg` se usara para miniatura inicial y audio normalizado. | El video original no se modifica y la fase tecnica puede persistir un resumen real y un audio reutilizable. | Acoplar la fase tecnica a un pipeline de IA o exigir `ffmpeg` para todo el flujo. |
| 2026-07-22 | Cache tecnico | Las inspecciones, miniaturas y audio preparado viviran en `cache/videos/<video-id>/...` y seguiran ignoradas por Git. | Los artefactos derivados se reutilizan y no contaminan el repositorio. | Escribir miniaturas, inspecciones o audio junto al video original. |
| 2026-07-22 | Preparacion de audio | `ffmpeg` tambien se usara para preparar una pista de audio normalizada reutilizable en WAV PCM16 mono 16 kHz. | El flujo audiovisual puede reutilizar audio tecnico sin tocar el video original y sin transcripcion aun. | Extraer audio con herramientas no encapsuladas o introducir IA en esta fase. |
| 2026-07-22 | Transcripcion local | `faster-whisper` + `CTranslate2` sera el backend local principal de transcripcion. | Se obtiene CUDA con fallback CPU, timestamps por segmento y cache local de modelos. | Resolver la transcripcion con API externa o con un backend no optimizado para Windows/CUDA. |
| 2026-07-22 | Analisis acustico | La primera fase de inteligencia acustica sera determinista, local y tecnica, sin inferir emociones como hechos. | Se priorizan reglas reproducibles, ventanas temporales, pausas, energia y eventos candidatos explicitos. | Clasificadores emocionales o modelos generativos en esta etapa. |
| 2026-07-22 | Analisis visual | La primera fase de analisis visual sera tecnica, local y reproducible, centrada en cortes, escenas, keyframes y metricas de movimiento y luminancia. | Se evita interpretacion semantica y se conservan evidencias y cache en rutas locales controladas. | Reconocimiento de personas, OCR, deteccion de objetos o narrativa semantica. |
| 2026-07-22 | Analisis multimodal | La primera capa multimodal unifica transcripcion, analisis acustico y analisis visual en ventanas sincronizadas con evidencia tecnica. | Se obtienen candidatos heuristics y scores transparentes sin convertirlos en interpretacion narrativa. | Seleccion definitiva de clips, prediccion de viralidad o LLM para etiquetado semantico. |
| 2026-07-22 | Clip ranking | El ranking inicial de clips sera determinista, reproducible y editable por humanos, separado del score multimodal original. | Se conservan historial, tags, rating, notas, ajustes de bordes y colecciones sin reemplazar la evidencia tecnica. | Machine learning entrenado, prediccion de viralidad o edicion automatica. |
| 2026-07-23 | Evaluacion operativa | La evaluacion end-to-end debe ejecutar el pipeline real sobre escenarios de demo controlados para auditar tiempos, cache, assertions y recuperacion. | Se reutilizan servicios existentes, se registran artefactos administrados y se separa la ejecucion tecnica de la calidad subjetiva. | Nuevos algoritmos, nuevos modelos o uso de contenido privado en escenarios demo. |
| 2026-07-23 | Personalization data | La preparacion de datos por creador sera local, reproducible y aislada por creador, construida a partir de feedback humano y features derivadas. | Se obtienen snapshots versionados, splits deterministas, quality reports y readiness sin entrenar modelos. | Mezclar creadores, inferir labels desde scores automaticos o arrancar entrenamiento en esta fase. |
| 2026-07-23 | UX de workflow | La primera experiencia integrada debe mostrar la accion recomendada por video, tareas persistidas, onboarding reabrible y preferencias iniciales sin exponer IDs internos. | La GUI orienta Home, Videos, Workflow y Task Center alrededor del estado real del pipeline. | Forzar al usuario a navegar por servicios tecnicos o depender solo de CLI. |
| 2026-07-23 | Persistencia de interfaz | La seleccion de creador, proyecto, pagina, preferencias y tareas de fondo se persistiran de forma local y reversible. | La reapertura mantiene contexto operativo sin guardar secretos ni mover datos automaticamente. | Reiniciar siempre desde cero o mezclar contexto sin persistencia. |

## Transcription Decision

Se adopto `faster-whisper` + `CTranslate2` como backend local principal.

Motivos:

- CUDA util en RTX 2080;
- fallback CPU simple;
- timestamps por segmento;
- integracion limpia con WAV normalizado;
- caché de modelos y resultados local.

Los runtimes NVIDIA se instalan como paquetes `nvidia-*` dentro de `.venv`; no se requiere CUDA Toolkit completo para esta primera integracion.

## Pendientes

- formato fisico final de persistencia para artefactos grandes;
- motor concreto de almacenamiento local para binarios futuros;
- esquema final de entrenamiento local;
- formato exacto del model registry.
- refinamiento futuro de eventos acusticos cuando exista una segunda fase especializada.
- refinamiento futuro de candidatos multimodales cuando exista una segunda fase de clips o edicion.
- refinamiento futuro de datos de personalizacion cuando exista una fase explicita de entrenamiento por creador.
- estrategia futura de personalizacion mas avanzada por creador.
