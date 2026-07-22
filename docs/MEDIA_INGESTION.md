# Media Ingestion

## Objetivo

Esta fase agrega inspeccion tecnica local de videos registrados sin realizar analisis inteligente, transcripcion ni procesamiento pesado.

## Herramientas requeridas

- `ffprobe` para extraer metadatos tecnicos reales.
- `ffmpeg` para generar una miniatura tecnica inicial cuando exista.

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

El caché es local, reutilizable e ignorado por Git.

## Vigencia

Una inspeccion pasa a `stale` cuando el tamaño o la fecha de modificacion del archivo cambian despues de la inspeccion.

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
- limitar el tamaño de salida;
- no modificar el video original;
- no escribir miniaturas junto al archivo original.

## Estado del MVP

Todavia no existe analisis audiovisual con IA. Esta fase solo prepara la base tecnica para inspecciones y artefactos derivados.
