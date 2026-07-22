# Multimodal Intelligence - Creator Intelligence Studio

## Objetivo

Combinar señales de audio, voz, video, texto y contexto narrativo para generar observaciones útiles, métricas reproducibles e inferencias justificadas.

## Señales observables

- audio bruto;
- energía y silencios;
- cambios de volumen;
- ritmo del habla;
- fotogramas;
- cambios visuales;
- texto en pantalla;
- transcripción;
- timestamps;
- cortes;
- escenas;
- pistas de interacción con el contenido.

## Inferencias

Las inferencias son conclusiones probables derivadas de señales observables, no hechos absolutos.

Ejemplos:

- posible cambio de tema;
- posible énfasis narrativo;
- posible hook;
- posible caída de retención;
- posible transición de escena;
- posible intensidad emocional aparente.

## Audio

- detección de silencios;
- detección de picos;
- ritmo;
- energía;
- eventos acústicos;
- separación de segmentos relevantes.

## Voz

- cadencia;
- velocidad;
- intensidad;
- continuidad;
- pausas;
- variación dentro del segmento.

## Video

- escenas;
- movimiento;
- cambios de plano;
- presencia de texto en pantalla;
- fotogramas clave;
- contexto visual.

## Texto

- transcripción;
- subtítulos;
- texto sobreimpreso;
- títulos;
- miniaturas;
- labels de plataforma cuando existan.

## Narrativa

- estructura;
- intro;
- desarrollo;
- payoff;
- cierres;
- recurrencia de temas;
- hooks y cold opens.

## Fusión multimodal

La fusión debe combinar señales con pesos según:

- calidad de entrada;
- confianza del extractor;
- disponibilidad de tiempo alineado;
- relevancia para el caso de uso;
- contexto del creador.

## Timestamps

Toda inferencia útil para edición o revisión debe poder referenciar:

- inicio;
- fin;
- duración;
- segmento;
- escena;
- evidencia de soporte.

## Niveles de confianza

- `low`: señal débil o ambigua;
- `medium`: señal razonable, requiere revisión;
- `high`: señal consistente con varias fuentes;
- `verified`: solo cuando la evidencia observable es muy clara y el sistema puede justificarla.

## Regla de observabilidad

El sistema debe diferenciar:

- hecho observable;
- métrica calculada;
- inferencia;
- interpretación probable;
- recomendación.

No debe afirmar emociones, intenciones o causas como hechos cuando solo sean inferencias.

