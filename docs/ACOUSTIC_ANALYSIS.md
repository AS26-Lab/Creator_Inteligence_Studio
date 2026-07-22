# Acoustic Analysis

## Objetivo

La primera fase de inteligencia acustica local genera una linea temporal tecnica a partir del audio preparado y, cuando existe, de los segmentos de transcripcion.
La salida es determinista, local y reutilizable.

No interpreta emociones como hechos.
No identifica personas.
No realiza diarizacion.

## Entradas

- WAV preparado en `WAV PCM16 mono 16 kHz`.
- Transcripcion local previa cuando existe.
- Metadatos de vigencia del audio preparado.
- Fingerprints de configuracion.

## Ventanas temporales

- frames internos: 20 a 30 ms;
- ventanas agregadas: 1 s;
- resumen de ritmo: 5 s a 10 s.

Las ventanas se usan para voz/silencio, energia, ritmo y eventos candidatos.

## Voz y silencio

La politica combina:

- energia RMS relativa al archivo;
- piso de ruido estimado;
- suavizado temporal;
- solape con ventanas de transcripcion cuando existe.

El clasificador usa etiquetas tecnicas:

- `silence`
- `low_activity`
- `speech_low`
- `speech_normal`
- `speech_high`
- `non_speech_activity`
- `unknown`

## Pausas

Se registran pausas por ventana y una suma global.
Umbrales recomendados:

- micro: menor de 0.25 s;
- corta: 0.25 a 0.75 s;
- media: 0.75 a 2.0 s;
- larga: mayor de 2.0 s.

Se guardan cantidad, promedio, mediana, maxima y ubicacion temporal.

## Ritmo

Se calcula:

- palabras por minuto globales;
- palabras por minuto durante voz;
- palabras por ventana;
- variacion aproximada de ritmo;
- cambios bruscos de ritmo.

La velocidad no se interpreta como intensidad emocional.

## Energia

Metricas principales:

- RMS;
- pico;
- energia normalizada;
- rango dinamico aproximado;
- percentiles;
- cambio entre ventanas.

Las metricas son relativas al archivo, no fisicas absolutas.

## Eventos candidatos

Solo se guardan candidatos tecnicos:

- `laughter_candidate`
- `transient_peak`
- `sustained_non_speech`
- `long_silence`
- `abrupt_energy_change`

Cada evento lleva evidencia tecnica y confianza limitada.

## Stale

Un analisis queda stale cuando cambia:

- audio preparado;
- fingerprint del audio;
- transcripcion asociada;
- configuracion;
- version del analizador;
- version de cache.

## Persistencia

Migracion v5:

- `acoustic_analyses`
- `acoustic_timeline_windows`
- `acoustic_events`

Se guarda de forma estructurada:

- resumen global;
- ventanas;
- eventos candidatos;
- fingerprints;
- warning/error resumidos.

## CLI

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

## GUI

La vista de analisis acustico muestra:

- estado;
- duracion de voz y silencio;
- speech ratio;
- palabras por minuto;
- pausas;
- energia;
- rango dinamico;
- eventos candidatos;
- linea temporal simple;
- exportaciones;
- reanalisis;
- eliminacion.

## Privacidad

- Todo el analisis es local.
- No se sube audio ni texto.
- No se registran transcripciones completas en logs.
- No se guardan inferencias emocionales.

## Limitaciones

- No hay clasificador emocional.
- No hay diarizacion.
- No hay identificacion de personas.
- No hay ranking narrativo.
- Los eventos son candidatos heuristics, no certezas.

## Relacion con la capa multimodal

- Las ventanas, pausas y eventos acusticos sirven como una de las fuentes de la alineacion multimodal.
- La capa multimodal conserva la evidencia acustica y la combina con transcripcion y vision sin reinterpretarla.
- Si la capa acustica falta, la multimodal sigue operando con cobertura parcial y lo reporta como warning.
