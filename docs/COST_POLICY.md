# Cost Policy - Creator Intelligence Studio

## Modos operativos

### Modo local

- usa recursos locales;
- no requiere saldo de API;
- es la base del núcleo funcional.

### Modo híbrido

- combina local y proveedores externos;
- usa externos solo cuando aporten valor claro;
- mantiene caché y trazabilidad.

### Modo premium

- habilita proveedores pagados o más costosos;
- requiere estimación previa;
- exige confirmación cuando el costo supere umbrales.

## Presupuestos

- presupuesto por proyecto;
- presupuesto por creador;
- presupuesto por tarea;
- presupuesto diario o mensual cuando el usuario lo configure.

## Estimaciones

- estimar antes de ejecutar procesos pagados;
- mostrar unidad de costo;
- mostrar costo esperado y costo máximo;
- explicar el impacto de saltarse el paso.

## Hard limits

- cortes duros de gasto;
- cortes duros de tokens o uso equivalente;
- cortes duros por proyecto;
- cortes duros por proveedor.

## Telemetría

- tiempo por tarea;
- consumo estimado;
- consumo real cuando esté disponible;
- reutilización de caché;
- ratio de resultados reutilizados;
- costo evitado por caché.

## Caché

- reutilizar resultados si la entrada no cambió;
- evitar reprocesar sin necesidad;
- versionar artefactos intermedios;
- invalidar si cambia el pipeline o el modelo.

## Confirmaciones

- pedir confirmación antes de procesos pagados;
- pedir confirmación antes de aumentar umbrales;
- pedir confirmación si el costo estimado excede el presupuesto.

## Núcleo sin saldo

El núcleo del producto debe funcionar sin saldo de API:

- gestión de creadores;
- proyectos;
- ingestión;
- almacenamiento;
- diagnóstico;
- jobs locales;
- análisis local básico.

Los proveedores externos deben ser opcionales y no una dependencia obligatoria del funcionamiento esencial.

