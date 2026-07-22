# Visual Analysis

La primera fase de analisis visual de Creator Intelligence Studio es tecnica, local y reproducible. No infiere narrativa, personas, emociones ni OCR.

## Objetivo

Detectar y persistir estructura visual observable:

- cortes;
- agrupacion inicial de escenas;
- keyframes representativos;
- brillo y contraste relativos;
- movimiento aproximado;
- cambios de color;
- segmentos estaticos;
- posibles frames negros;
- posibles congelamientos;
- eventos tecnicos candidatos.

## Muestreo

- frames internos: muestreo ligero entre 1 y 4 FPS;
- refinamiento local alrededor de cortes candidatos;
- keyframes por escena;
- limites de seguridad para videos largos;
- nunca se extraen todos los frames por defecto.

## Etiquetas tecnicas

Las etiquetas de actividad son tecnicas:

- `static`
- `low_motion`
- `moderate_motion`
- `high_motion`
- `dark`
- `normal_exposure`
- `bright`
- `possible_black_frame`
- `possible_freeze`
- `transition_candidate`
- `unknown`

## Eventos candidatos

Los eventos no son certezas. Se guardan como candidatos con evidencia tecnica:

- `hard_cut`
- `gradual_transition`
- `flash_candidate`
- `black_frame_candidate`
- `freeze_candidate`
- `abrupt_motion_change`
- `abrupt_brightness_change`

## Keyframes

Los keyframes se escriben en cache controlada por la aplicacion:

`cache/videos/<video-id>/visual/keyframes/`

La ruta persiste de forma relativa y no modifica el video original.

## Stale

El analisis visual se considera stale si cambia:

- el archivo fuente;
- la inspeccion tecnica de origen;
- el fingerprint de configuracion;
- la version del analizador;
- la presencia o integridad de keyframes en cache.

## Exportaciones

- `JSON`
- `CSV` de linea temporal
- `CSV` de escenas
- `TXT` tecnico opcional

## GUI y CLI

La UI expone una vista de analisis visual desde Videos y una pagina dedicada.
La CLI expone comandos para analizar, mostrar, listar timeline, listar escenas, listar eventos, exportar y eliminar.

## Privacidad

- todo el analisis es local;
- no se suben videos ni keyframes;
- la documentacion no debe incluir contenido privado;
- el video original nunca se modifica.

## Relacion con la capa multimodal

- Las escenas, cortes, keyframes y eventos visuales sirven como fuente temporal para la capa multimodal.
- La capa multimodal no cambia el analisis visual: solo lo alinea y lo puntua junto con otras fuentes.
- Cuando no hay analisis visual vigente, la capa multimodal funciona con cobertura parcial y reduce la confianza.
