# Audio Preparation

## Objetivo

Preparar una pista de audio tecnica, normalizada y reutilizable a partir de un video ya registrado e inspeccionado. Esta fase no realiza transcripcion, diarizacion, analisis de voz ni analisis acustico inteligente.

## Formato normalizado

La salida inicial es:

- WAV;
- PCM signed 16-bit little-endian;
- mono;
- 16,000 Hz;
- sin compresion.

La frecuencia de muestreo esta explicitamente configurada para poder cambiarse en una fase futura.

## Flujo

1. Verificar que el video exista.
2. Verificar que exista una inspeccion tecnica completada y vigente.
3. Enumerar streams con metadatos de `ffprobe` ya normalizados.
4. Seleccionar un stream de audio con la politica documentada.
5. Ejecutar `ffmpeg` de forma segura para producir el WAV normalizado.
6. Validar el WAV generado.
7. Persistir metadatos y registrar la ruta relativa dentro de `cache/`.

## Politica de seleccion de stream

Orden inicial:

1. idioma preferido configurado, si existe;
2. stream marcado como default;
3. mayor numero de canales;
4. mayor sample rate;
5. primer stream valido.

La seleccion se guarda para trazabilidad.

## Cache

Ruta base:

`cache/videos/<video-id>/audio/`

Artefactos:

- `normalized_v1.wav`;
- `metadata.json`.

Reglas:

- nunca escribir junto al video original;
- nunca modificar el video original;
- usar nombres deterministas por video y version de cache;
- limpiar archivos parciales si falla la extraccion;
- reutilizar resultados si siguen vigentes;
- permitir `force=True`.

## Estados

- `not_prepared`
- `queued`
- `extracting`
- `completed`
- `failed`
- `file_missing`
- `no_audio_stream`
- `tool_unavailable`
- `stale`

## Vigencia

Un audio preparado pasa a `stale` cuando cambia cualquiera de estos elementos:

- tamano del video original;
- fecha de modificacion del video original;
- inspeccion tecnica de origen;
- configuracion de normalizacion;
- version de cache.

## CLI

Comandos actuales:

```bat
python -m creator_intelligence_studio audio prepare --video-id <video_id>
python -m creator_intelligence_studio audio prepare --video-id <video_id> --force
python -m creator_intelligence_studio audio show --video-id <video_id>
python -m creator_intelligence_studio audio verify --video-id <video_id>
python -m creator_intelligence_studio audio clear-cache --video-id <video_id>
```

## GUI

La pantalla Videos muestra el estado del audio preparado, el stream seleccionado, la ruta de cache y las acciones de preparar, regenerar, verificar y limpiar cache.

## Errores

- `file_missing` si el video original ya no existe;
- `no_audio_stream` si no hay streams de audio utilizables;
- `tool_unavailable` si `ffmpeg` no esta disponible;
- `stale` si la informacion persistida ya no coincide con la fuente.

## Seguridad

- usar `subprocess` solo desde infraestructura;
- pasar argumentos como lista;
- no usar `shell=True`;
- limitar salida y tiempo de ejecucion;
- capturar `stdout` y `stderr`;
- no escribir ni modificar el video original.

## Relation to Transcription

La transcripcion local consume directamente el WAV normalizado preparado en esta fase.
Mantener esta salida estable es requisito para el backend CUDA de `faster-whisper`.

## Relation to Acoustic Analysis

El analisis acustico local consume el mismo WAV normalizado y la transcripcion cuando existe.
Las dos fases comparten la misma politica de vigencia: si cambia el audio preparado, la configuracion o el fingerprint de entrada, el resultado puede quedar `stale`.
