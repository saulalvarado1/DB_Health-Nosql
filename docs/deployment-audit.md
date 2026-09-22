# Auditoría de despliegue reproducible — DB Health Monitor

Fecha: 22 de septiembre de 2026

Alcance: imágenes de producción, composición local completa y preparación para
un posterior despliegue en nube. No acredita todavía un proveedor cloud real.

## Resultado

El sistema completo puede construirse y arrancar desde un repositorio limpio
con Docker Compose. PostgreSQL inicia primero, una tarea separada aplica todas
las migraciones, y solo entonces arrancan la API y el worker. El frontend espera
que la API esté saludable y actúa como único punto de entrada HTTP.

Las funciones de la aplicación no cambian al contenerizarla: autenticación,
aislamiento por usuario, cifrado de URI, recolección manual y automática,
historial, diagnósticos, umbrales y alertas siguen en las mismas capas. Cambia la
forma de ejecutar los procesos y de entregarles configuración.

## Artefactos incorporados

| Archivo | Función |
|---|---|
| `backend/Dockerfile` | Construye un wheel y ejecuta API, worker o migraciones como UID `10001`. |
| `frontend/Dockerfile` | Compila React y sirve los archivos con Nginx sin privilegios como UID `101`. |
| `frontend/nginx.conf` | Proxy del mismo origen, SPA fallback, healthcheck y cabeceras de seguridad. |
| `compose.yaml` | Orquesta PostgreSQL, migración, API, worker y frontend con dependencias y healthchecks. |
| `.env.deploy.example` | Documenta únicamente nombres y valores de ejemplo, sin secretos utilizables. |
| `deploy/generate-env.ps1` | Genera secretos aleatorios sin imprimirlos y se niega a reemplazar un archivo existente. |
| `compose.e2e.yaml` | Añade Redis y MongoDB aislados con cuentas de monitoreo de privilegio mínimo. |
| `deploy/run-e2e.ps1` | Orquesta el navegador y los siete servicios temporales, y garantiza su limpieza. |
| `.dockerignore` | Evita enviar secretos, dependencias locales, pruebas y cachés al contexto de construcción. |

## Arquitectura comprobada

```text
Navegador / balanceador HTTPS
             |
     frontend Nginx :8080
        |          |
   React estático  /api/*
                    |
              FastAPI :8000
                    |
            PostgreSQL privado

worker ----------- PostgreSQL
  |
  +---- conexiones salientes a MongoDB y Redis monitorizados
```

Solo `frontend` publica un puerto. FastAPI, el worker y PostgreSQL no tienen
enlaces de puerto al host. Las redes `edge` y `backend` separan el proxy de la
persistencia; el frontend no pertenece a la red de PostgreSQL.

## Controles de seguridad

- No se incorporan `.env`, entornos virtuales, `node_modules`, pruebas ni cachés
  en las imágenes.
- Backend y frontend se ejecutan sin root, con sistema de archivos raíz de solo
  lectura, `no-new-privileges` y capacidades Linux eliminadas.
- La API no se publica directamente; las solicitudes llegan por `/api/` desde
  el proxy del mismo origen.
- Nginx entrega CSP restrictiva, HSTS, `nosniff`, anti-framing, política de
  referencia y política de permisos.
- Los secretos requeridos no tienen valores por defecto. La configuración real
  se mantiene en `.env.deploy`, ignorado por Git.
- Las migraciones son una tarea de una sola ejecución y la API no arranca si
  esa tarea falla.
- Los healthchecks distinguen proceso vivo, API preparada y frontend accesible.

Los secretos en variables de entorno son adecuados para la prueba local. En
nube deben proceder del gestor de secretos del proveedor, con rotación y acceso
por identidad de servicio. No deben copiarse a la imagen ni a archivos del
repositorio.

## Evidencia ejecutada

Se creó un nombre de proyecto Docker aleatorio, se comprobó que no tuviera
contenedores, redes ni volúmenes previos, y se generó un entorno temporal con
secretos aleatorios. Al finalizar se eliminaron únicamente los recursos de ese
proyecto y el archivo temporal.

Resultado observado:

```text
Construcción backend                 correcta
Construcción frontend                correcta (0 vulnerabilidades en npm ci)
Servicios Compose                    5
PostgreSQL                            healthy
Migración                             exited (0)
API                                   healthy
Worker                                healthy
Frontend                              healthy
GET /                                 200
GET /healthz                          200
GET /api/v1/health                    ok
GET /api/v1/health/ready              ready
Migración actual                      20260922_0005 (head)
UID de API                            10001
UID de frontend                       101
Enlaces de puertos de API             {}
Cabeceras de seguridad                presentes
E2E navegador + siete servicios       1 passed
Recursos E2E después de finalizar     eliminados
```

La imagen frontend se construyó con Node `22.22.2`, versión compatible con los
requisitos del árbol de dependencias. Las imágenes base están fijadas por
versión; un proceso de actualización posterior deberá reconstruir y volver a
ejecutar esta auditoría.

## Uso

```powershell
.\deploy\generate-env.ps1
docker compose --env-file .env.deploy up --build --detach --wait
docker compose --env-file .env.deploy ps --all
```

Detener sin eliminar los datos:

```powershell
docker compose --env-file .env.deploy down
```

Antes de una actualización se debe respaldar PostgreSQL. Eliminar el volumen de
Compose destruye los usuarios, configuraciones, historial y alertas; no forma
parte del procedimiento normal de apagado.

## Qué cambia al desplegar en nube

Las funciones del producto se conservan, pero deben configurarse estos bordes:

1. HTTPS y dominio mediante balanceador o proxy con certificado válido.
2. Secretos administrados para PostgreSQL, JWT y cifrado de credenciales.
3. Volumen persistente o PostgreSQL administrado con copias y restauración
   probada.
4. Reglas de salida y listas de acceso para alcanzar MongoDB/Redis remotos con
   TLS y usuarios de solo lectura.
5. Centralización de logs y alertas operativas para API, worker y base interna.
6. Registro privado de imágenes y reconstrucción controlada ante parches.

Si se usa una sola VM, `compose.yaml` puede ejecutarse casi sin cambios detrás
del proxy de la máquina. Si se usa un servicio de contenedores administrado, los
cinco roles se traducen a tareas/servicios equivalentes y PostgreSQL debería
pasar preferentemente a un servicio administrado; el código funcional no cambia.

## Pendientes antes de producción

| Prioridad | Pendiente | Evidencia necesaria |
|---|---|---|
| Alta | Ensayo en el proveedor elegido | HTTPS real, secretos administrados, persistencia y restauración verificadas. |
| Media | Capacidad | k6 o Locust con p95, throughput y tasa de error en infraestructura objetivo. |
| Media | Observabilidad | Métricas, trazas/correlación y alertas operativas sin datos sensibles. |
| Media | Estrategia de actualización | Backup, migración, rollback y reconstrucción de imágenes documentados. |

## Dictamen

RNF-DES-01 queda `VALIDADO` para despliegue reproducible local. El sistema ya
tiene una ruta segura y repetible hacia la nube, pero aún no debe declararse
listo para producción hasta ejecutar el ensayo cloud, carga, respaldo y
observabilidad indicados. El E2E local del flujo completo ya quedó validado.
