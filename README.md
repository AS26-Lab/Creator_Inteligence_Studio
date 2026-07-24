# Creator Intelligence Studio

Creator Intelligence Studio es una aplicacion de escritorio para Windows orientada al analisis inteligente de contenido audiovisual para creadores.

## Estado actual

El proyecto ya dispone de:

- base ejecutable con Python 3.11;
- catalogo de creadores, proyectos y videos locales;
- GUI con PySide6;
- diagnostico del entorno;
- persistencia SQLite;
- inspeccion tecnica local de videos con `ffprobe`;
- miniatura tecnica inicial en cache local con `ffmpeg` cuando esta disponible;
- preparacion tecnica de audio normalizado a WAV PCM16 mono 16 kHz cuando `ffmpeg` esta disponible.

Todavia no existen:

- analisis audiovisual semantico con IA generativa;
- PyTorch;
- CUDA Toolkit;
- modelos descargados;
- conectores reales;
- Script & Voice Studio como flujo obligatorio.

## Plataforma principal

- Windows
- Python 3.11
- NVIDIA CUDA como plataforma principal futura
- procesamiento local como prioridad

AMD, ROCm, DirectML, Vulkan y macOS quedan fuera del MVP.

## Requisitos actuales

- Windows 11 recomendado para uso final, aunque este entorno de desarrollo esta en Windows 10 Pro 22H2.
- Python 3.11.9 dentro de `.venv`
- PySide6 instalado en el entorno virtual
- Git instalado
- `ffprobe` requerido para la inspeccion tecnica
- `ffmpeg` requerido para miniaturas tecnicas iniciales y para la preparacion tecnica de audio

La localizacion de herramientas multimedia puede configurarse mas adelante con `ffmpeg_path`, `ffprobe_path` o `ffmpeg_bin_directory`, o mediante las variables `CIS_FFMPEG_PATH`, `CIS_FFPROBE_PATH` y `CIS_FFMPEG_BIN_DIRECTORY`.

## Arranque de la GUI

```bat
scripts\run_gui.bat
```

O directamente:

```bat
python -m creator_intelligence_studio --gui
```

## Estado funcional actual

La aplicacion ya permite:

- crear creadores;
- listar y consultar creadores;
- archivar creadores;
- crear proyectos pertenecientes a un creador;
- listar y consultar proyectos;
- archivar proyectos;
- registrar videos locales como metadatos;
- listar y consultar videos registrados;
- verificar si un archivo sigue disponible;
- inspeccionar tecnicamente un video registrado;
- preparar un audio normalizado reutilizable a partir de un video inspeccionado;
- analizar acusticamente el audio preparado con metrica tecnica local;
- analizar tecnicamente la estructura visual del video con cortes, escenas, keyframes, movimiento, brillo, contraste y eventos candidatos;
- guardar un resumen tecnico real de `ffprobe`;
- generar una miniatura tecnica inicial en cache local cuando `ffmpeg` esta disponible;
- construir una linea temporal multimodal con candidatos tecnicos sincronizados;
- rankear candidatos de clip con revision humana, feedback e historial local;
- renderizar localmente clips aprobados o colecciones con FFmpeg, con salida verificada y historial persistente;
- generar, editar, importar y exportar subtitulos locales basados en transcripciones existentes;
- preparar datasets de personalizacion por creador a partir del feedback humano;
- abrir una interfaz de escritorio funcional con navegacion, inspector y diagnostico del sistema;
- persistir toda la informacion en SQLite local.

## Flujo de producto y UX

La GUI incluye un flujo guiado para operar sin conocer IDs internos ni comandos CLI:

- Home con creador activo, proyecto activo, tareas y atajos;
- selector persistente de creador y proyecto;
- importacion y preparacion de video;
- vista unificada de workflow por video con siguiente accion recomendada;
- task center global para tareas de fondo;
- onboarding corto reabrible;
- preferencias iniciales de datos, modelos, exportaciones y transcripcion;
- vista tecnica de system health con detalles expandibles.

La accion recomendada depende del estado real del video y no ejecuta tareas costosas automaticamente sin confirmacion.

La guia detallada del flujo esta en [`docs/PRODUCT_UX_WORKFLOW.md`](docs/PRODUCT_UX_WORKFLOW.md).
La primera version de render local esta documentada en [`docs/CLIP_RENDERING.md`](docs/CLIP_RENDERING.md).
La primera version de subtitulos locales esta documentada en [`docs/SUBTITLES.md`](docs/SUBTITLES.md).
La base de analitica manual multiplataforma esta documentada en [`docs/ANALYTICS_DATA_FOUNDATION.md`](docs/ANALYTICS_DATA_FOUNDATION.md).

## Base local

La base estructurada inicial se guarda en:

`data/creator_intelligence_studio.db`

El archivo esta ignorado por Git. No debe subirse al repositorio.

Advertencia: en esta primera version el registro conserva la ruta absoluta normalizada del archivo local. Eso es funcional para desarrollo, pero no es una estrategia portable final.

La inspeccion tecnica escribe artefactos derivados en `cache/videos/<video-id>/inspection/`, `cache/videos/<video-id>/thumbnails/` y `cache/videos/<video-id>/audio/`. Ese cache permanece local y no debe subirse.

## Activar `.venv`

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En `cmd.exe`:

```bat
.\.venv\Scripts\activate.bat
```

## Ejecutar la aplicacion

```bat
scripts\run_app.bat
```

O directamente:

```bat
python -m creator_intelligence_studio
```

## Ejecutar el diagnostico en JSON

```bat
python -m creator_intelligence_studio --diagnostic-json
```

## Comandos de creadores

```bat
python -m creator_intelligence_studio creator create --name "Heybermu"
python -m creator_intelligence_studio creator list
python -m creator_intelligence_studio creator show <creator_id_or_slug>
python -m creator_intelligence_studio creator archive <creator_id_or_slug>
```

## Comandos de proyectos

```bat
python -m creator_intelligence_studio project create --creator <creator_id_or_slug> --name "Video principal" --type long_form
python -m creator_intelligence_studio project list --creator <creator_id_or_slug>
python -m creator_intelligence_studio project show <project_id>
python -m creator_intelligence_studio project archive <project_id>
```

## Comandos de videos

```bat
python -m creator_intelligence_studio video register --project <project_id> --file "C:\ruta\video.mp4" --title "Titulo provisional"
python -m creator_intelligence_studio video list --project <project_id>
python -m creator_intelligence_studio video show <video_id>
python -m creator_intelligence_studio video verify <video_id>
```

## Comandos de medios

```bat
python -m creator_intelligence_studio media tools
python -m creator_intelligence_studio media tools --json
python -m creator_intelligence_studio media inspect --video-id <video_id>
python -m creator_intelligence_studio media inspect --video-id <video_id> --force
python -m creator_intelligence_studio media show --video-id <video_id>
python -m creator_intelligence_studio media show --video-id <video_id> --json
```

## Comandos de audio

```bat
python -m creator_intelligence_studio audio prepare --video-id <video_id>
python -m creator_intelligence_studio audio prepare --video-id <video_id> --force
python -m creator_intelligence_studio audio show --video-id <video_id>
python -m creator_intelligence_studio audio verify --video-id <video_id>
python -m creator_intelligence_studio audio clear-cache --video-id <video_id>
```

## Comandos de transcripcion

```bat
python -m creator_intelligence_studio transcription backend
python -m creator_intelligence_studio transcription backend --json
python -m creator_intelligence_studio transcription models
python -m creator_intelligence_studio transcription model-status --model small
python -m creator_intelligence_studio transcription download-model --model small
python -m creator_intelligence_studio transcription verify-model --model small
python -m creator_intelligence_studio transcription transcribe --video-id <video_id>
python -m creator_intelligence_studio transcription transcribe --video-id <video_id> --profile fast
python -m creator_intelligence_studio transcription transcribe --video-id <video_id> --profile quality
python -m creator_intelligence_studio transcription transcribe --video-id <video_id> --device cpu
python -m creator_intelligence_studio transcription show --video-id <video_id>
python -m creator_intelligence_studio transcription segments --video-id <video_id>
python -m creator_intelligence_studio transcription export --video-id <video_id> --format txt
python -m creator_intelligence_studio transcription export --video-id <video_id> --format srt
python -m creator_intelligence_studio transcription export --video-id <video_id> --format json
python -m creator_intelligence_studio transcription delete --video-id <video_id>
```

El caché de modelos vive en `models/transcription/faster-whisper/`.
Las exportaciones controladas se escriben en `cache/transcriptions/` salvo que el usuario indique otra ruta.

## Comandos de subtitulos

```bat
python -m creator_intelligence_studio subtitles generate-video --video-id <video_id>
python -m creator_intelligence_studio subtitles generate-clip --candidate-id <candidate_id>
python -m creator_intelligence_studio subtitles show --track-id <track_id>
python -m creator_intelligence_studio subtitles list-video --video-id <video_id>
python -m creator_intelligence_studio subtitles list-clip --candidate-id <candidate_id>
python -m creator_intelligence_studio subtitles validate --track-id <track_id>
python -m creator_intelligence_studio subtitles update-text --cue-id <cue_id> --text "..."
python -m creator_intelligence_studio subtitles update-time --cue-id <cue_id> --start 1.2 --end 4.5
python -m creator_intelligence_studio subtitles split --cue-id <cue_id> --position 24
python -m creator_intelligence_studio subtitles merge --first-cue-id <first_cue_id> --second-cue-id <second_cue_id>
python -m creator_intelligence_studio subtitles import --video-id <video_id> --file "C:\ruta\subtitles.srt"
python -m creator_intelligence_studio subtitles export --track-id <track_id> --format srt
python -m creator_intelligence_studio subtitles history --track-id <track_id>
python -m creator_intelligence_studio render subtitles capabilities --json
python -m creator_intelligence_studio render subtitles styles --json
python -m creator_intelligence_studio render sidecar --job-id <job_id> --track-id <track_id> --format srt
python -m creator_intelligence_studio render burn-in --candidate-id <candidate_id> --track-id <track_id>
```

Subtitle deliveries remain local and verifiable. Sidecar keeps the MP4 unchanged and adds a subtitle file plus manifest; burn-in creates a new MP4 with embedded subtitles. See [`docs/SUBTITLE_DELIVERIES.md`](docs/SUBTITLE_DELIVERIES.md).

Los subtitulos locales son una capa editorial separada de la transcripcion. Los cambios sobre subtitulos no reescriben la transcripcion original.

## Comandos de analisis acustico

```bat
python -m creator_intelligence_studio acoustic analyze --video-id <video_id>
python -m creator_intelligence_studio acoustic analyze --video-id <video_id> --force
python -m creator_intelligence_studio acoustic show --video-id <video_id>
python -m creator_intelligence_studio acoustic timeline --video-id <video_id>
python -m creator_intelligence_studio acoustic events --video-id <video_id>
python -m creator_intelligence_studio acoustic export --video-id <video_id> --format json
python -m creator_intelligence_studio acoustic export --video-id <video_id> --format csv
python -m creator_intelligence_studio acoustic delete --video-id <video_id>
```

Los resultados acusticos se guardan en SQLite y las exportaciones controladas se escriben en `cache/acoustics/` salvo que el usuario indique otra ruta.

## Comandos de analisis visual

```bat
python -m creator_intelligence_studio visual analyze --video-id <video_id>
python -m creator_intelligence_studio visual analyze --video-id <video_id> --force
python -m creator_intelligence_studio visual show --video-id <video_id>
python -m creator_intelligence_studio visual timeline --video-id <video_id>
python -m creator_intelligence_studio visual scenes --video-id <video_id>
python -m creator_intelligence_studio visual events --video-id <video_id>
python -m creator_intelligence_studio visual export --video-id <video_id> --format json
python -m creator_intelligence_studio visual export --video-id <video_id> --format timeline-csv
python -m creator_intelligence_studio visual export --video-id <video_id> --format scenes-csv
python -m creator_intelligence_studio visual delete --video-id <video_id>
```

Los resultados visuales se guardan en SQLite y los keyframes tecnicos se escriben en `cache/videos/<video-id>/visual/` sin tocar el video original.

## Comandos de analisis multimodal

```bat
python -m creator_intelligence_studio multimodal analyze --video-id <video_id>
python -m creator_intelligence_studio multimodal analyze --video-id <video_id> --force
python -m creator_intelligence_studio multimodal show --video-id <video_id>
python -m creator_intelligence_studio multimodal timeline --video-id <video_id>
python -m creator_intelligence_studio multimodal candidates --video-id <video_id>
python -m creator_intelligence_studio multimodal candidate --candidate-id <candidate_id>
python -m creator_intelligence_studio multimodal export --video-id <video_id> --format json
python -m creator_intelligence_studio multimodal export --video-id <video_id> --format timeline-csv
python -m creator_intelligence_studio multimodal export --video-id <video_id> --format candidates-csv
python -m creator_intelligence_studio multimodal export --video-id <video_id> --format txt
python -m creator_intelligence_studio multimodal delete --video-id <video_id>
```

La capa multimodal une transcripcion, actividad acustica y analisis visual en ventanas sincronizadas. Sus artefactos viven en `cache/multimodal/<video-id>/` y no se suben al repositorio.

## Comandos de ranking de clips

```bat
python -m creator_intelligence_studio clips rank --video-id <video_id>
python -m creator_intelligence_studio clips rank --video-id <video_id> --profile balanced
python -m creator_intelligence_studio clips rank --video-id <video_id> --profile speech-focused
python -m creator_intelligence_studio clips rank --video-id <video_id> --profile visual-focused
python -m creator_intelligence_studio clips rank --video-id <video_id> --profile high-energy
python -m creator_intelligence_studio clips rank --video-id <video_id> --profile story-beats
python -m creator_intelligence_studio clips show --video-id <video_id>
python -m creator_intelligence_studio clips list --video-id <video_id>
python -m creator_intelligence_studio clips candidate --candidate-id <candidate_id>
python -m creator_intelligence_studio clips approve --candidate-id <candidate_id>
python -m creator_intelligence_studio clips reject --candidate-id <candidate_id>
python -m creator_intelligence_studio clips shortlist --candidate-id <candidate_id>
python -m creator_intelligence_studio clips needs-review --candidate-id <candidate_id>
python -m creator_intelligence_studio clips rate --candidate-id <candidate_id> --rating 4
python -m creator_intelligence_studio clips note --candidate-id <candidate_id> --text "..."
python -m creator_intelligence_studio clips tags --candidate-id <candidate_id> --tags hook,highlight
python -m creator_intelligence_studio clips adjust --candidate-id <candidate_id> --start 12.4 --end 38.7
python -m creator_intelligence_studio clips history --candidate-id <candidate_id>
python -m creator_intelligence_studio clips export --video-id <video_id> --format json
python -m creator_intelligence_studio clips export --video-id <video_id> --format csv
python -m creator_intelligence_studio clips export --video-id <video_id> --format edl
python -m creator_intelligence_studio clips delete --video-id <video_id>
```

Los planes de clips se escriben en `cache/clips/<video-id>/exports/` salvo que el usuario elija otra ruta.

## Comandos de datos de personalizacion

```bat
python -m creator_intelligence_studio personalization build --creator-id <creator_id>
python -m creator_intelligence_studio personalization build --creator-id <creator_id> --project-id <project_id>
python -m creator_intelligence_studio personalization show --snapshot-id <snapshot_id>
python -m creator_intelligence_studio personalization latest --creator-id <creator_id>
python -m creator_intelligence_studio personalization list --creator-id <creator_id>
python -m creator_intelligence_studio personalization examples --snapshot-id <snapshot_id>
python -m creator_intelligence_studio personalization quality --snapshot-id <snapshot_id>
python -m creator_intelligence_studio personalization readiness --creator-id <creator_id>
python -m creator_intelligence_studio personalization compare --snapshot-a <snapshot_id> --snapshot-b <snapshot_id>
python -m creator_intelligence_studio personalization archive --snapshot-id <snapshot_id>
python -m creator_intelligence_studio personalization export --snapshot-id <snapshot_id> --format json
python -m creator_intelligence_studio personalization export --snapshot-id <snapshot_id> --format csv
python -m creator_intelligence_studio personalization export --snapshot-id <snapshot_id> --format jsonl
```

Los datasets de personalizacion son locales, versionados e inmutables una vez completados. Se construyen a partir de feedback humano, candidatos de clip y features reproducibles por creador. Por defecto no incluyen texto completo ni notas privadas en las exportaciones de ML.

## Ejecutar pruebas

```bat
scripts\run_tests.bat
```

O directamente:

```bat
python -m unittest discover -s tests -p "test_*.py"
```

## Estructura principal

- `docs/`: documentacion maestra y diagnosticos.
- `src/creator_intelligence_studio/`: paquete principal del proyecto.
- `tests/`: pruebas unitarias.
- `config/`: configuracion por defecto.
- `scripts/`: scripts de arranque y pruebas en Windows.
- `data/`, `logs/`, `models/`, `artifacts/`, `cache/`: carpetas operativas locales.
- `data/creator_intelligence_studio.db`: base SQLite local estructurada.
- `cache/videos/<video-id>/inspection/`: resultados tecnicos de `ffprobe`.
- `cache/videos/<video-id>/thumbnails/`: miniaturas tecnicas.
- `cache/videos/<video-id>/audio/`: audio normalizado reutilizable.
- `cache/videos/<video-id>/visual/`: keyframes y artefactos de analisis visual.
- `cache/multimodal/<video-id>/`: linea temporal multimodal y exportaciones controladas.
- `cache/clips/<video-id>/exports/`: planes de clip y exportaciones controladas.
- `cache/subtitles/<video-id>/`: tracks, exportaciones y revisiones controladas.
- `cache/personalization/<creator-id>/`: snapshots de dataset, reportes y exportaciones controladas.

## Script & Voice Studio

Script & Voice Studio es un modulo opcional. No es necesario para analizar videos, revisar metricas, administrar proyectos ni usar el nucleo del sistema. No participa en el flujo base de videos o audio.

## Advertencia sobre CUDA y PyTorch

CUDA Toolkit y PyTorch todavia no estan instalados en este repositorio. La aplicacion actual solo realiza diagnostico basico, catalogo, inspeccion tecnica local con herramientas externas si existen, preparacion tecnica de audio cuando `ffmpeg` esta disponible, preparacion de rutas, logging e interfaz.

`ffprobe` es la herramienta requerida para la inspeccion tecnica. `ffmpeg` se usa para miniaturas tecnicas y para extraer audio normalizado. El video original nunca se copia ni se modifica.
Los subtitulos locales se construyen desde la transcripcion existente y no sustituyen al motor de transcripcion.

## Seguridad y repositorio

No subas videos, modelos, datos privados, credenciales ni la base SQLite al repositorio. Los archivos sensibles deben permanecer fuera del control de versiones.

## Borrado manual de una base de desarrollo

Si necesitas reiniciar los datos de desarrollo, borra manualmente `data/creator_intelligence_studio.db` solo cuando estes seguro de que no necesitas conservar la informacion. No hay borrado automatico en la aplicacion.

## Baseline de modelos personalizados

La primera version de modelos personalizados por creador ya queda soportada localmente con:

- regresion logistica interpretable;
- baselines comparativos locales;
- artefactos versionados por creador y por training run;
- activacion y retiro explicitos;
- scoring separado del ranking de clips;
- seguridad local de carga de artefactos;
- aislamiento de datos por creador.

No predice viralidad y no mezcla datos entre creadores.

## Evaluacion operativa end-to-end

La capa `evaluation` ejecuta escenarios de demo controlados sobre el pipeline real para auditar tiempos, cache, assertions, recuperacion y artefactos. No agrega modelos ni cambia las formulas existentes.

Comandos principales:

```bash
python -m creator_intelligence_studio evaluation scenarios
python -m creator_intelligence_studio evaluation run --scenario smoke_pipeline
python -m creator_intelligence_studio evaluation show --run-id <run_id>
python -m creator_intelligence_studio evaluation export --run-id <run_id> --format json
```

Los artefactos de evaluacion se guardan en rutas gestionadas por la aplicacion, como `temp/evaluations/`, y no deben subirse al repositorio.

Una evaluacion end-to-end pasada demuestra coherencia tecnica, no calidad comercial ni capacidad predictiva universal.
