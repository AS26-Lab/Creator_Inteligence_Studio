# Transcription

## Resumen

Creator Intelligence Studio ya integra una transcripcion local con `faster-whisper` + `CTranslate2`.
La ruta principal usa CUDA con `int8_float16` y la ruta de respaldo usa CPU con `int8`.
Los segmentos de transcripcion tambien pueden alimentar analisis acustico local cuando esta fase existe.

## Dependencias

- `faster-whisper==1.2.1`
- `ctranslate2==4.8.1`
- `nvidia-cublas-cu12==12.9.2.10` en Windows
- `nvidia-cuda-runtime-cu12==12.9.79` en Windows
- `nvidia-cuda-nvrtc-cu12==12.9.86` en Windows
- `nvidia-cudnn-cu12==9.25.0.15` en Windows

## Runtimes NVIDIA

El backend local localiza DLL instaladas por paquetes `nvidia-*` dentro de `.venv`:

- `nvidia/cuda_runtime/bin`
- `nvidia/cublas/bin`
- `nvidia/cuda_nvrtc/bin`
- `nvidia/cudnn/bin`

La carga se hace con `os.add_dll_directory()` solo para el proceso actual. No se modifica el PATH global.

## Modelos y perfiles

Modelos soportados inicialmente:

- `base` -> perfil `fast`
- `small` -> perfil `balanced`
- `medium` -> perfil `quality`

Configuracion segura por defecto:

- `profile=balanced`
- `model_name=small`
- `device=auto`
- `compute_type=auto`
- `language=auto`
- `beam_size=5`
- `vad_filter=false`
- `word_timestamps=false`

### Estados del modelo

El gestor de modelos distingue:

- `not_installed`
- `downloading`
- `installed`
- `incomplete`
- `corrupt`
- `incompatible`
- `error`

La ruta por defecto es `models/transcription/faster-whisper/<model-name>/`.
La descarga ocurre solo cuando el usuario lo solicita de forma explicita o cuando lanza una transcripcion desde la CLI o la capa de aplicacion.
Si el modelo ya existe, se reutiliza sin duplicar descargas.

## CUDA

Reglas de seleccion:

1. intentar CUDA;
2. verificar DLL oficiales instaladas por `nvidia-*`;
3. verificar `ctranslate2.get_cuda_device_count()`;
4. verificar `int8_float16`;
5. usar `int8_float16` si esta disponible.

Si CUDA falla o no esta disponible, el motor cae a CPU con `int8`.

## Persistencia

Migracion v4:

- `transcriptions`
- `transcription_segments`

Se guarda de forma estructurada:

- estado;
- motor;
- modelo;
- dispositivo;
- compute type;
- idioma;
- texto completo;
- tiempos;
- fingerprints;
- warning/error resumidos;
- segmentos ordenados por `segment_index`.

Conviene guardar en JSON solo lo que es derivado o muy variable.
En esta version, la transcripcion persistida se guarda de forma estructurada y las exportaciones se generan al vuelo.

## Stale

Una transcripcion queda stale cuando cambia:

- el audio preparado;
- el fingerprint del audio;
- el modelo;
- el motor;
- el compute type;
- el idioma solicitado;
- la configuracion;
- la version de cache.

## CLI

Comandos nuevos:

- `transcription backend`
- `transcription models`
- `transcription model-status --model <name>`
- `transcription download-model --model <name>`
- `transcription verify-model --model <name>`
- `transcription transcribe --video-id <id>`
- `transcription show --video-id <id>`
- `transcription segments --video-id <id>`
- `transcription export --video-id <id> --format txt|srt|json`
- `transcription delete --video-id <id>`

`transcription transcribe` descarga el modelo en demanda si no esta disponible y luego reutiliza la caché local.

## GUI

La interfaz de escritorio expone una vista de transcripcion y un resumen en el inspector de videos.
La transcripcion corre en segundo plano y soporta progreso aproximado y cancelacion cooperativa.

## Exportaciones

- `TXT`: texto completo UTF-8
- `SRT`: segmentos con timestamps y numeracion desde 1
- `JSON`: metadatos, segmentos y tiempos

Las exportaciones se escriben en una ruta controlada por la aplicacion o en una ruta elegida por el usuario.

## Privacidad

- Todo el procesamiento es local.
- No se sube audio ni texto.
- No se registran transcripciones completas en logs.
- No se suben modelos, bases, audios, videos ni caches.

## Limitaciones actuales

- No hay diarizacion.
- No hay identificacion de hablantes.
- No hay embeddings.
- No hay word timestamps por defecto.
- No hay backend externo.
- No se intentan inferir emociones como hechos dentro de la transcripcion ni del analisis acustico.

## Relacion con la capa multimodal y de subtitulos

- La transcripcion alimenta la alineacion multimodal como fuente temporal primaria de texto.
- La capa multimodal no modifica la transcripcion, solo la consume cuando existe y esta vigente.
- Si la transcripcion falta, la linea multimodal puede operar con cobertura parcial y bajar `confidence`.
- La capa de subtitulos consume la transcripcion existente, pero no la reescribe.
- Un subtitulo editado es una representacion editorial distinta, con su propio historial, validacion y exportacion.
- Los tracks de clip pueden conservar tiempos absolutos como metadata y exportar tiempo relativo.
