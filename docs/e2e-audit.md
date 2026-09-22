# Auditoría E2E V1 — DB Health Monitor

Fecha: 22 de septiembre de 2026

## Objetivo y resultado

Se automatizó el flujo crítico completo de V1 en Microsoft Edge mediante
Playwright. La ejecución final produjo `1 passed` y utilizó siete servicios
aislados: PostgreSQL, migración, API, worker, frontend, Redis y MongoDB.

## Recorrido comprobado

1. Registrar una cuenta con datos sintéticos y volver a iniciar sesión.
2. Registrar Redis con intervalo de 10 segundos y esperar una ejecución real
   del worker.
3. Comprobar historial, recolección manual y las 27 métricas Redis.
4. Reducir temporalmente el umbral de memoria para abrir una alerta crítica,
   reconocerla, restaurar el umbral y comprobar su resolución.
5. Registrar MongoDB, esperar el worker y comprobar sus 20 métricas.
6. Pausar y reactivar Redis.
7. Eliminar ambas instancias y verificar el inventario vacío.

## Aislamiento y seguridad

- Cada ejecución usa un nombre de proyecto Docker aleatorio y un volumen
  PostgreSQL nuevo; no utiliza la base de desarrollo ni contenedores existentes.
- Las contraseñas se generan criptográficamente y se guardan en un directorio
  temporal ignorado por Git. No se imprimen ni se escriben en el repositorio.
- Redis deshabilita el usuario predeterminado. Su cuenta `monitor` solo puede
  ejecutar `PING` e `INFO`.
- MongoDB recibe una cuenta `monitor` con el rol `clusterMonitor`; la cuenta root
  se usa únicamente para crearla dentro del entorno efímero.
- Redis y MongoDB no publican puertos al host y solo son alcanzables por la red
  privada del backend.
- Playwright no guarda trazas ni videos. Solo toma una captura ante fallo, y los
  artefactos están ignorados por Git.
- El bloque `finally` elimina únicamente el proyecto temporal exacto, su volumen,
  sus redes y los archivos generados, incluso cuando falla una aserción.

## Defecto detectado y corregido

La primera ejecución válida recorrió todas las funciones hasta intentar borrar
una instancia Redis que ya tenía una alerta resuelta. Aunque la clave foránea de
PostgreSQL declaraba `ON DELETE CASCADE`, SQLAlchemy intentaba asignar `NULL` al
campo obligatorio de la alerta y la API devolvía error.

La relación `MonitoredDatabase.alerts` ahora usa `passive_deletes=True`, por lo
que PostgreSQL ejecuta la cascada definida. La prueba de aislamiento también
comprueba que el propietario puede eliminar una instancia con alerta y que no
quedan filas huérfanas. Después de la corrección, el E2E completo pasó.

## Ejecución reproducible

Desde la raíz del repositorio:

```powershell
.\deploy\run-e2e.ps1
```

El script requiere las dependencias instaladas previamente con `npm install` en
`frontend`. Prefiere Edge o Chrome ya instalados; si ninguno existe, instala
Chromium mediante Playwright. `-SkipBrowserInstall` solo debe usarse cuando el
navegador requerido ya esté disponible.

## Alcance pendiente

Esta evidencia valida el flujo funcional completo en un navegador local y en
contenedores aislados. No sustituye el ensayo en la nube con HTTPS, gestor de
secretos, recuperación de copias, observabilidad y carga, ni la matriz final de
navegadores que acuerde el equipo.
