# Account Safety - Creator Intelligence Studio

## Políticas

- la seguridad de las cuentas es prioritaria sobre la automatización;
- solo se usarán vías oficiales o manuales asistidas;
- no se diseñará evasión de CAPTCHA;
- no se ocultará automatización;
- no se falsificarán fingerprints;
- no se buscará evadir restricciones de plataforma.

## Consentimiento

- el usuario debe autorizar explícitamente el acceso a una cuenta;
- la aplicación debe mostrar qué permisos usa;
- la revocación debe ser posible;
- el usuario debe saber qué se sincroniza y cuándo.

## Credenciales

- deben almacenarse de forma segura;
- no deben exponerse en logs ni en UI;
- deben poder rotarse;
- deben poder revocarse;
- deben aislarse por proveedor.

## Rate limits

- respetar límites de plataforma;
- usar colas y backoff;
- evitar ráfagas innecesarias;
- registrar cuota consumida cuando aplique.

## Prohibiciones

- evasión de CAPTCHA;
- evasión de detección;
- fingerprint spoofing;
- automatización encubierta;
- acceso no autorizado;
- scraping que viole términos o seguridad.

## Automatización permitida

- sincronización explícita;
- importación manual;
- importación asistida;
- ejecución de tareas autorizadas;
- procesamiento local fuera de la plataforma.

## Acciones humanas obligatorias

- autorizar conexión;
- aprobar permisos;
- aprobar publicación cuando el flujo lo requiera;
- revisar salidas generativas cuando Creator Voice esté activo;
- resolver bloqueos de seguridad.

## Auditoría

- registrar quién autorizó;
- registrar cuándo se ejecutó;
- registrar qué proveedor participó;
- registrar errores y revocaciones;
- preservar historial de acceso relevante.

