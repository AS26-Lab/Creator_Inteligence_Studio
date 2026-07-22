# Data Model - Creator Intelligence Studio

## Principios

- Cada creador tiene aislamiento logico.
- Cada proyecto pertenece a un creador.
- Cada video y cada artefacto derivado son rastreables.
- Cada analisis debe conservar version, origen y configuracion.
- Los datos calculados deben diferenciarse de los observables.

## Identificadores

- Identificadores internos: UUID recomendado.
- Los objetos persistidos deben tener `id` estable.
- Los artefactos y modelos deben incluir `version`.
- Las relaciones deben ser explicitas y no implicitas.

## Esquema implementado

### `schema_migrations`

- `version` entero.
- `name` texto.
- `applied_at` UTC.

### `creators`

- `id` UUID string.
- `display_name`.
- `slug` unico.
- `description` opcional.
- `created_at` UTC.
- `updated_at` UTC.
- `status` con valores `active` o `archived`.

### `projects`

- `id` UUID string.
- `creator_id` FK a `creators.id`.
- `name`.
- `description` opcional.
- `project_type` con valores `long_form`, `short_form`, `mixed`, `research`.
- `status` con valores `active`, `completed`, `archived`.
- `created_at` UTC.
- `updated_at` UTC.

### `video_assets`

- `id` UUID string.
- `project_id` FK a `projects.id`.
- `title`.
- `source_path` absoluta normalizada.
- `original_filename`.
- `extension`.
- `file_size_bytes`.
- `file_modified_at` UTC opcional.
- `source_type` con valores `local_file`, `platform_import`, `manual_reference`.
- `processing_status` con valores `registered`, `queued`, `processing`, `completed`, `failed`, `cancelled`.
- `registered_at` UTC.
- `updated_at` UTC.
- `notes` opcional.
- `file_available` booleano calculado o actualizado.

### `video_inspections`

- `id` UUID string.
- `video_asset_id` FK unica a `video_assets.id`.
- `inspection_status` con valores `not_inspected`, `queued`, `inspecting`, `completed`, `failed`, `file_missing`, `tool_unavailable`, `stale`.
- `inspected_at` UTC.
- `source_file_size_bytes`.
- `source_file_modified_at` UTC.
- `duration_seconds`.
- `format_name`.
- `format_long_name`.
- `overall_bitrate`.
- `stream_count`.
- `video_stream_count`.
- `audio_stream_count`.
- `subtitle_stream_count`.
- `width`.
- `height`.
- `display_aspect_ratio`.
- `pixel_aspect_ratio`.
- `frame_rate_numerator` y `frame_rate_denominator`.
- `average_frame_rate_numerator` y `average_frame_rate_denominator`.
- `video_codec`.
- `video_codec_profile`.
- `pixel_format`.
- `video_bitrate`.
- `audio_codec`.
- `audio_sample_rate`.
- `audio_channels`.
- `audio_channel_layout`.
- `audio_bitrate`.
- `rotation_degrees`.
- `metadata_json` con el JSON normalizado de `ffprobe`.
- `ffprobe_version` y `ffprobe_path`.
- `ffmpeg_version` y `ffmpeg_path`.
- `thumbnail_relative_path`.
- `error_code` y `error_message`.
- `created_at` y `updated_at` UTC.

### `prepared_audio_assets`

- `id` UUID string.
- `video_asset_id` FK unica a `video_assets.id`.
- `source_inspection_id` FK a `video_inspections.id`.
- `status` con valores `not_prepared`, `queued`, `extracting`, `completed`, `failed`, `file_missing`, `no_audio_stream`, `tool_unavailable`, `stale`.
- `relative_cache_path` relativo a `cache/`.
- `metadata_relative_path` relativo a `cache/`.
- `format_name`.
- `codec_name`.
- `sample_rate_hz`.
- `channels`.
- `channel_layout`.
- `bit_depth`.
- `duration_seconds`.
- `file_size_bytes`.
- `source_file_size_bytes`.
- `source_file_modified_at` UTC.
- `selected_stream_index`.
- `selected_stream_codec_name`.
- `selected_stream_channels`.
- `selected_stream_channel_layout`.
- `selected_stream_sample_rate_hz`.
- `selected_stream_language`.
- `selected_stream_is_default`.
- `extraction_started_at` UTC.
- `extraction_completed_at` UTC.
- `ffmpeg_version`.
- `cache_version`.
- `normalization_sample_rate_hz`.
- `normalization_channels`.
- `warning_code` y `warning_message`.
- `error_code` y `error_message`.
- `created_at` y `updated_at` UTC.

## Relaciones

```mermaid
erDiagram
    CREATOR ||--o{ PROJECT : owns
    PROJECT ||--o{ VIDEO_ASSET : contains
    VIDEO_ASSET ||--o{ VIDEO_INSPECTION : has
    VIDEO_ASSET ||--o{ PREPARED_AUDIO_ASSET : has
    VIDEO_INSPECTION ||--o{ PREPARED_AUDIO_ASSET : source
```

## Estado y vigencia

- `video_assets.processing_status` describe el flujo de registro.
- `video_inspections.inspection_status` describe el resultado tecnico persistido.
- `prepared_audio_assets.status` describe la preparacion tecnica de audio.
- Un resultado puede ser `stale` si el archivo cambia despues de inspeccion o preparacion.
- `file_missing` indica que el archivo ya no esta disponible.
- `tool_unavailable` indica que `ffprobe` o `ffmpeg` no estaban disponibles para completar la fase.
- `no_audio_stream` indica que no se encontro un stream de audio utilizable.

## Artefactos

Los artefactos minimos contemplados son:

- original;
- hash futuro;
- proxy;
- audio;
- inspeccion tecnica;
- miniatura tecnica;
- segmentos;
- escenas;
- fotogramas clave;
- eventos acusticos;
- analisis;
- recomendaciones;
- feedback;
- historial;
- costos;
- tiempos.

## Migracion v3

- agrega `prepared_audio_assets`;
- conserva la compatibilidad con `creators`, `projects`, `video_assets` y `video_inspections`;
- no modifica IDs existentes;
- mantiene indices utiles por `video_asset_id`, `source_inspection_id` y `status`.

## Pendientes

- formato fisico final de persistencia para artefactos grandes;
- estrategia final de rutas portables;
- versionado adicional de inspeccion, audio y miniaturas.

## Migration v4: Transcription

La migracion v4 agrega:

- `transcriptions`
- `transcription_segments`

Campos principales:

- `video_asset_id`
- `prepared_audio_asset_id`
- `status`
- `engine`
- `model_name`
- `device`
- `compute_type`
- `requested_language`
- `detected_language`
- `full_text`
- `duration_seconds`
- `processing_time_seconds`
- `real_time_factor`
- `segment_count`
- `source_audio_fingerprint`
- `configuration_fingerprint`

`transcription_segments` conserva `segment_index` con orden estable y FK hacia `transcriptions`.

## Migration v5: Acoustic analysis

La migracion v5 agrega:

- `acoustic_analyses`
- `acoustic_timeline_windows`
- `acoustic_events`

Campos principales:

- `video_asset_id`
- `prepared_audio_asset_id`
- `transcription_id`
- `status`
- `analyzer_version`
- `configuration_fingerprint`
- `source_audio_fingerprint`
- `duration_seconds`
- `speech_duration_seconds`
- `silence_duration_seconds`
- `speech_ratio`
- `silence_ratio`
- `words_per_minute`
- `voiced_words_per_minute`
- `average_energy`
- `peak_energy`
- `dynamic_range`
- `pause_count`
- `average_pause_seconds`
- `longest_pause_seconds`
- `short_pause_count`
- `medium_pause_count`
- `long_pause_count`
- `low_activity_segment_count`
- `abrupt_change_count`
- `event_candidate_count`

`acoustic_timeline_windows` conserva `window_index` con orden estable y FK hacia `acoustic_analyses`.
`acoustic_events` conserva `event_index` con orden estable y FK hacia `acoustic_analyses`.

La vigencia se define por fingerprints de entrada, configuracion, version del analizador y cambios en el audio preparado.
