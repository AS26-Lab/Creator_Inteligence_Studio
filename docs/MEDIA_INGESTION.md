# Media Ingestion

## Objetivo

Esta fase agrega inspeccion tecnica local de videos registrados sin realizar analisis inteligente, transcripcion ni procesamiento pesado.

La siguiente fase agrega preparacion tecnica de audio reutilizable a partir de un video ya inspeccionado. Esa salida es un artefacto local y no modifica el original.

## Herramientas requeridas

- `ffprobe` para extraer metadatos tecnicos reales.
- `ffmpeg` para generar una miniatura tecnica inicial y para preparar audio normalizado cuando corresponda.

## Deteccion

La aplicacion detecta herramientas por esta jerarquia:

1. Configuracion explicita de la aplicacion:
   - `ffmpeg_path`
   - `ffprobe_path`
   - `ffmpeg_bin_directory`
2. Variables de entorno especificas del producto:
   - `CIS_FFMPEG_PATH`
   - `CIS_FFPROBE_PATH`
   - `CIS_FFMPEG_BIN_DIRECTORY`
3. `PATH` del proceso.
4. Carpeta portable controlada por la aplicacion: `tools/ffmpeg/bin`.
5. Ubicaciones comunes de Windows como fallback documentado, incluida `C:\Tools\ffmpeg\bin`.

En todos los casos se valida la version real con `-version`.

No se modifica el `PATH` automaticamente.

## Datos extraidos

- formato;
- duracion;
- bitrate;
- streams;
- codec de video y audio;
- resolucion;
- aspect ratio;
- frame rate;
- canales;
- frecuencia de muestreo;
- rotacion;
- JSON normalizado de `ffprobe`.

## Estados

- `not_inspected`
- `queued`
- `inspecting`
- `completed`
- `failed`
- `file_missing`
- `tool_unavailable`
- `stale`

## Cache

Ruta base:

`cache/videos/<video-id>/`

Subrutas:

- `inspection/`
- `thumbnails/`
- `audio/`

El cache es local, reutilizable e ignorado por Git.

## Vigencia

Una inspeccion pasa a `stale` cuando el tamano o la fecha de modificacion del archivo cambian despues de la inspeccion.

## Errores

- archivo faltante;
- herramienta no disponible;
- timeout de `ffprobe`;
- salida invalida de `ffprobe`;
- fallo de miniatura con `ffmpeg`.

Si `ffprobe` no esta disponible, la inspeccion tecnica devuelve `tool_unavailable`.

## Reglas de seguridad

- usar listas de argumentos;
- no usar `shell=True`;
- capturar `stdout` y `stderr`;
- limitar el tamano de salida;
- no modificar el video original;
- no escribir miniaturas ni audio junto al archivo original.

## Preparacion de audio

- requiere una inspeccion tecnica completada y vigente antes de extraer;
- selecciona un stream de audio con una politica explicita;
- genera WAV PCM signed 16-bit little-endian, mono, 16 kHz;
- valida el WAV generado con la biblioteca estandar;
- guarda metadatos en `cache/videos/<video-id>/audio/metadata.json`;
- considera `stale` si cambia el video original, la inspeccion de origen o la configuracion de normalizacion;
- devuelve `tool_unavailable` si `ffmpeg` no esta disponible;
- no copia, mueve ni modifica el video original.

## Estado del MVP

Todavia no existe analisis audiovisual con IA. Esta fase solo prepara la base tecnica para inspecciones y artefactos derivados.

La siguiente fase de analisis visual reutiliza la inspeccion tecnica y los artefactos derivados en `cache/videos/<video-id>/visual/` sin modificar el video original.
