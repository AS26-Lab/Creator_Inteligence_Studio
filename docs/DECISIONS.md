# Decisions - Creator Intelligence Studio

## Registro de decisiones confirmadas

| Fecha | Contexto | Decisión | Consecuencias | Alternativas descartadas |
|---|---|---|---|---|
| 2026-07-22 | Plataforma base del producto | El MVP se centrará en Windows con NVIDIA CUDA como plataforma principal. | La arquitectura y el rendimiento se optimizan para CUDA primero. | AMD, ROCm, DirectML, Vulkan y macOS fuera del MVP. |
| 2026-07-22 | Base de desarrollo | Python 3.11 será la versión inicial del proyecto. | Se alinea el entorno virtual y la compatibilidad de dependencias a 3.11.x. | Migrar inmediatamente a otra versión sin necesidad. |
| 2026-07-22 | Procesamiento | El procesamiento local será la prioridad siempre que sea viable. | Se reduce dependencia de servicios externos y se conservan datos localmente. | Hacer del cloud el camino principal. |
| 2026-07-22 | Proveedores | Los servicios externos de IA serán opcionales y reemplazables. | El núcleo debe funcionar sin saldo de API. | Acoplar el producto a un único proveedor. |
| 2026-07-22 | Script & Voice Studio | Script & Voice Studio será opcional. | El análisis, los proyectos y las métricas no dependen de la generación de guiones. | Hacer la generación de guiones obligatoria. |
| 2026-07-22 | Flujo creativo | La generación de guiones no forma parte obligatoria del flujo de análisis. | El módulo de análisis puede operar sin texto generado. | Mezclar análisis y escritura como un único flujo inseparable. |
| 2026-07-22 | Datos | Se mantendrá separación estricta entre datos, personalización y modelos por creador. | Menor riesgo de contaminación entre perfiles y mejor privacidad. | Unificar datos de varios creadores en un solo perfil global. |
| 2026-07-22 | Plataforma inicial | YouTube será la primera plataforma objetivo. | La primera integración oficial se priorizará para YouTube. | Empezar por una lista amplia de plataformas a la vez. |
| 2026-07-22 | Seguridad | Las APIs oficiales y la seguridad de las cuentas tienen prioridad. | No se diseñarán evasiones de CAPTCHA ni fingerprinting. | Automatizaciones encubiertas o evasivas. |
| 2026-07-22 | Resiliencia | La aplicación debe abrir aunque CUDA no esté disponible. | Habrá diagnóstico y funciones básicas sin GPU, con deshabilitación o degradación de tareas pesadas. | Bloquear por completo la apertura sin GPU. |
| 2026-07-22 | Creator Voice | Cuando Creator Voice esté activo, un texto generativo no se considerará final sin revisión o personalización. | El flujo debe incluir revisión humana o adaptación explícita. | Marcar como final cualquier salida de proveedor externo. |

## Pendientes

- formato físico de persistencia;
- motor concreto de almacenamiento local;
- framework final de UI;
- esquema final de entrenamiento local;
- formato exacto del model registry.

