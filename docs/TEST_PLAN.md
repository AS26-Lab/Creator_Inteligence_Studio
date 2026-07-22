# Test Plan - Creator Intelligence Studio

## Objetivo

Validar que la base del sistema sea estable, trazable y segura antes de ampliar capacidades.

## Tipos de prueba

### Unitarias

- reglas de dominio;
- cálculo de métricas;
- validación de estados;
- selección de caché;
- costos;
- personalización por creador.

### Integración

- jobs con almacenamiento local;
- artefactos y manifiestos;
- conectores simulados;
- pipeline de análisis;
- registry de modelos.

### Almacenamiento

- rutas;
- permisos;
- escritura y lectura;
- recuperación tras reinicio;
- versionado de artefactos.

### Jobs

- cola;
- progreso;
- cancelación;
- reintento;
- reanudación;
- consistencia de estado.

### Caché

- hit;
- miss;
- invalidación;
- reutilización;
- coherencia por hash y versión.

### GPU

- detección de CUDA;
- ejecución acelerada;
- uso de memoria;
- degradación controlada.

### Sin CUDA

- apertura de la aplicación;
- diagnóstico visible;
- funciones básicas;
- bloqueo de tareas pesadas cuando corresponda.

### Datasets y modelos

- versiones;
- compatibilidad;
- evaluación;
- reproducibilidad;
- comparativa con baseline.

### UI

- navegación;
- estados vacíos;
- progreso;
- errores;
- separación de Script & Voice Studio.

### Conectores

- autenticación;
- límites;
- errores;
- sincronización;
- aislamiento por proveedor.

### Seguridad

- credenciales;
- permisos;
- auditoría;
- confirmaciones;
- acciones humanas obligatorias.

### Costos

- estimación previa;
- hard limits;
- presupuesto;
- caché;
- reutilización.

## Criterios mínimos

- las pruebas críticas deben ejecutarse en CI o local antes de dar una versión por estable;
- los fallos de GPU no deben romper la apertura de la aplicación;
- los datos de un creador no deben contaminar otro perfil.

