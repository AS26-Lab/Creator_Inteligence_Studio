# Product Spec - Creator Intelligence Studio

## Visión

Creator Intelligence Studio será una aplicación de escritorio para Windows que ayude a creadores de contenido a entender, mejorar y planificar sus videos mediante análisis audiovisual, aprendizaje personalizado y herramientas creativas opcionales.

El producto prioriza procesamiento local, almacenamiento local, arquitectura modular y proveedores externos de IA opcionales y reemplazables.

## Problema

Los creadores suelen tener fragmentadas sus herramientas:

- un sistema para transcribir;
- otro para analizar rendimiento;
- otro para revisar clips;
- otro para escribir guiones;
- otro para guardar feedback;
- otro para conectar plataformas.

Eso dificulta:

- mantener el contexto del creador;
- reutilizar artefactos;
- comparar versiones;
- aprender de correcciones;
- operar sin depender siempre de servicios externos.

## Usuarios

- Creador individual.
- Equipo pequeño de creación.
- Editor o asistente de contenido.
- Analista de contenido.
- Usuario avanzado que quiere automatizar parte de su flujo.

## Propuesta de valor

- Unifica análisis, personalización y gestión de artefactos en un solo entorno.
- Mantiene separación estricta entre datos de cada creador.
- Permite trabajar sin depender del módulo generativo.
- Prioriza procesamiento local cuando sea viable.
- Conserva trazabilidad de resultados, costos, tiempos y feedback.

## Módulos

1. Administración de creadores.
2. Administración de proyectos.
3. Registro e importación de videos.
4. Almacenamiento y caché de artefactos.
5. Transcripción.
6. Análisis de audio y voz.
7. Análisis visual y de escenas.
8. Análisis narrativo.
9. Recomendaciones de edición con timestamps.
10. Ranking de clips.
11. Análisis de títulos y miniaturas.
12. Análisis de audiencia y rendimiento.
13. Aprendizaje personalizado por creador.
14. Conectores oficiales con plataformas.
15. Costos, límites y control de proveedores externos.
16. Script & Voice Studio opcional.

## Alcance MVP

### Incluido

- Windows como plataforma principal.
- Python 3.11 como base de desarrollo.
- Arquitectura modular con separación entre UI, dominio e infraestructura.
- Procesamiento local como primera opción.
- CUDA como ruta principal de GPU.
- Almacenamiento local de proyectos, artefactos y metadatos.
- Observabilidad básica: logs, trazabilidad y estado de jobs.
- Soporte para abrir la aplicación aunque CUDA no esté disponible.
- Preparación para conectores oficiales, empezando por YouTube en fases posteriores.
- Separación de personalización por creador desde el diseño.

### Fuera de alcance

- AMD, ROCm, DirectML, Vulkan y macOS.
- Entrenar modelos fundacionales desde cero.
- Descargar modelos por defecto en esta etapa.
- Automatizaciones que evadan restricciones de plataformas.
- Evasión de CAPTCHA o fingerprinting.
- Dependencia obligatoria de Script & Voice Studio.
- Integración completa con todas las plataformas desde el inicio.

## Funciones esenciales frente a opcionales

### Esenciales

- abrir y gestionar proyectos;
- registrar videos y artefactos;
- procesar jobs;
- persistir resultados;
- mostrar diagnósticos;
- operar con fallback limitado sin GPU;
- respetar límites y costos;
- separar datos por creador.

### Opcionales

- generación de guiones;
- adaptación a voz del creador;
- análisis externo híbrido;
- conectores adicionales;
- modelos avanzados entrenados con feedback;
- recomendaciones creativas más sofisticadas.

## Criterios de éxito

- el sistema arranca y muestra estado del entorno incluso sin CUDA;
- los datos de cada creador no se mezclan;
- los artefactos se pueden reutilizar por huella o configuración;
- los jobs son cancelables y trazables;
- el sistema puede operar en modo local sin saldo de API;
- las recomendaciones distinguen hecho, métrica, inferencia e interpretación.

