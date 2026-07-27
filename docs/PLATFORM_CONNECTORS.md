# Platform Connectors - Creator Intelligence Studio

## Principios

- usar APIs oficiales cuando existan;
- priorizar seguridad de cuentas;
- evitar evasión de restricciones;
- aislar cada proveedor;
- permitir importaciones asistidas cuando la API no cubra un caso;
- registrar límites, errores y estado de sincronización.

## Orden de prioridad

1. YouTube.
2. Instagram.
3. TikTok Read-Only Integration.

## Consolidacion multi-plataforma

La capa comun de consolidacion coordina conexiones, salud, capacidades, disponibilidad de datos,
sincronizacion, reportes y privacidad sin mezclar semanticas ni reemplazar conectores nativos.

Ver [`docs/MULTI_PLATFORM_INTEGRATION_CONSOLIDATION.md`](MULTI_PLATFORM_INTEGRATION_CONSOLIDATION.md).

## YouTube primero

YouTube será la primera plataforma objetivo para:

- conectores oficiales;
- sincronización de metadatos;
- importación asistida;
- lectura de rendimiento cuando sea posible;
- trazabilidad de contenido.

## Instagram

- integración solo por vías oficiales compatibles;
- manejo cuidadoso de permisos y alcance;
- sincronización limitada a lo que la API permita.

## TikTok

- integracion oficial en modo solo lectura;
- depender solo de Login Kit y Display API oficiales;
- mantener importacion manual para metricas no cubiertas;
- no asumir cobertura total ni equivalencia con analytics privados.

## APIs oficiales

- autenticación explícita;
- permisos mínimos necesarios;
- refresh de credenciales controlado;
- separación por proveedor.

## Importaciones

- importación manual;
- importación asistida;
- carga de exportaciones oficiales;
- ingestión de archivos locales.

## Sincronización

- pull explícito;
- colas de sincronización;
- resolución de conflictos;
- reintentos limitados;
- caché por proveedor.

## Límites

- rate limits;
- cuotas;
- ventanas de reintento;
- presupuestos de costo;
- límites duros definidos por el usuario o la política.

## Errores

- credenciales inválidas;
- permisos insuficientes;
- cuota agotada;
- respuesta inconsistente;
- cambios de API;
- fallo de red;
- contenido no accesible.

## Credenciales

- almacenarlas de forma segura;
- no imprimir secretos en logs;
- permitir revocación;
- soportar rotación;
- aislar credenciales por proveedor y por creador cuando aplique.

## Aislamiento por proveedor

- cada conector debe tener su propio contrato;
- cada proveedor debe fallar de forma independiente;
- un error en un proveedor no debe corromper los demás;
- los datos importados deben registrar su origen.
