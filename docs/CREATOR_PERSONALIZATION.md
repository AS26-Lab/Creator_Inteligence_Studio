# Creator Personalization - Creator Intelligence Studio

## Objetivo

Separar la inteligencia general del producto de la personalización específica de cada creador.

## Perfil por creador

Cada creador debe tener un perfil con:

- preferencias;
- tono habitual;
- vocabulario frecuente;
- ritmo;
- temas recurrentes;
- benchmarks personales;
- historial de feedback;
- reglas de privacidad;
- configuración de conectores y costos.

## Aislamiento

- los datos de un creador no deben mezclarse con los de otro;
- los modelos personalizados deben quedar vinculados al creador;
- los embeddings y ejemplos deben respetar el aislamiento lógico;
- la configuración debe poder exportarse o migrarse sin contaminar otros perfiles.

## Aprendizaje

El aprendizaje por creador puede apoyarse en:

- reglas explícitas;
- ejemplos aprobados;
- ejemplos rechazados;
- métricas de rendimiento;
- feedback corregido por el usuario;
- preferencias persistentes.

## Preferencias

- vocabulario;
- formalidad;
- humor;
- cadencia;
- longitud;
- densidad de información;
- estilo de hooks;
- tipo de cierre;
- nivel de riesgo creativo aceptable.

## Benchmarks personales

Los benchmarks deben comparar al creador contra su propio historial, no contra una media abstracta del sistema.

Ejemplos:

- retención relativa;
- tasa de aprobación de hooks;
- consistencia de tono;
- rendimiento de miniaturas;
- compatibilidad con estilo histórico.

## Feedback

- corrección manual;
- aprobación;
- rechazo;
- anotaciones;
- reescrituras del usuario;
- etiquetas de calidad.

## Privacidad

- la personalización debe quedar local cuando sea posible;
- el sistema debe permitir controlar qué se comparte con proveedores externos;
- las referencias del creador deben tratarse como datos sensibles de producto.

## Portabilidad

- exportar perfil;
- exportar benchmarks;
- exportar feedback;
- exportar configuración;
- reimportar sin perder versiones.

## Prevención de sobreajuste

- no copiar muletillas sin contexto;
- no caricaturizar al creador;
- no repetir expresiones de forma mecánica;
- no confundir frecuencia con identidad estilística;
- usar diversidad de ejemplos autenticados.

