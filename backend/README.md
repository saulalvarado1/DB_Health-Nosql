# Backend — DB Health Monitor

API y worker de monitoreo para MongoDB y Redis. PostgreSQL es el almacén
interno de usuarios, configuración, historial, evaluaciones y alertas.

## Preparación local

Desde `backend`, crea el entorno virtual, instala las dependencias y crea un
archivo `.env` a partir de `.env.example`. No confirmes ese archivo: contiene
secretos propios de tu entorno.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest
```

## Procesos locales

En una terminal inicia la API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `http://127.0.0.1:8000/docs`.

En otra terminal inicia el worker. Es un proceso independiente de la API:

```powershell
.\.venv\Scripts\python.exe -m app.workers.monitoring
```

El worker busca programaciones vencidas cada `MONITORING_WORKER_POLL_SECONDS`
segundos. PostgreSQL reserva cada programación temporalmente, de modo que se
pueden ejecutar varias réplicas del worker sin que dos de ellas procesen la
misma tarea. Si un proceso se detiene, la reserva vence y otro worker puede
retomarla.

## Variables del worker

| Variable | Valor por defecto | Uso |
|---|---:|---|
| `MONITORING_WORKER_POLL_SECONDS` | 5 | Espera entre ciclos del worker. |
| `MONITORING_LEASE_SECONDS` | 90 | Tiempo máximo de una reserva de programación. |
| `MONITORING_WORKER_BATCH_SIZE` | 25 | Máximo de instancias tomadas por ciclo. |

Los valores de producción se definirán mediante variables de entorno del
servicio de despliegue, no dentro del código ni del repositorio.

## Alertas

Cada evaluación abre o actualiza una alerta por condición activa. Cuando la
condición desaparece, la alerta se conserva como `resolved`; el usuario puede
reconocer una alerta activa con `POST /api/v1/alerts/{alert_id}/acknowledge`.

El historial de una instancia se consulta con
`GET /api/v1/databases/{database_id}/history?limit=50`. Cada muestra devuelve
sus valores atómicos, resultado de salud y un mensaje seguro cuando la
conexión falló.

La instancia se configura con `PATCH /api/v1/databases/{database_id}` (nombre,
intervalo o estado) y se elimina con `DELETE /api/v1/databases/{database_id}`.

## Umbrales

Consulta las reglas asignadas con `GET /api/v1/databases/{database_id}/thresholds`.
Actualiza una regla con `PUT /api/v1/databases/{database_id}/thresholds/{metric_code}`.
La primera personalización clona el perfil predeterminado para que el cambio no
afecte a otras instancias del mismo usuario y motor.

## Pruebas de integración aisladas

Las pruebas de aislamiento entre usuarios y concurrencia de workers usan
exclusivamente la base `db_health_monitor_test`. No inician el worker ni se
conectan a Redis o MongoDB:
las URI empleadas son ficticias. Antes de ejecutarlas, migra solo esa base desde
PowerShell en `backend`:

```powershell
$testPassword = Read-Host "Contraseña de db_health_test_app" -AsSecureString
$testPasswordText = [System.Net.NetworkCredential]::new('', $testPassword).Password
$encodedTestPassword = [uri]::EscapeDataString($testPasswordText)
$env:TEST_DATABASE_URL = "postgresql+psycopg://db_health_test_app:$encodedTestPassword@localhost:5432/db_health_monitor_test"
Remove-Variable testPasswordText, encodedTestPassword

if ($env:TEST_DATABASE_URL -notmatch '/db_health_monitor_test(?:\?.*)?$') {
    throw 'TEST_DATABASE_URL no apunta a db_health_monitor_test.'
}

$previousDatabaseUrl = $env:DATABASE_URL
$env:DATABASE_URL = $env:TEST_DATABASE_URL
.\.venv\Scripts\python.exe -m alembic upgrade head
if ($null -eq $previousDatabaseUrl) {
    Remove-Item Env:DATABASE_URL
} else {
    $env:DATABASE_URL = $previousDatabaseUrl
}
Remove-Variable previousDatabaseUrl

.\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:TEST_DATABASE_URL
Remove-Variable testPassword
```

El caso crea dos usuarios temporales. El segundo recibe `404` al intentar ver,
editar, eliminar, recolectar, consultar historial o umbrales, y reconocer una
alerta de la instancia del primero. Además, comprueba en PostgreSQL que la URI
queda cifrada. Al terminar, borra únicamente los usuarios temporales cuyo correo
empieza por `integration-`.

El caso de concurrencia abre dos sesiones independientes. Mientras el primer
worker conserva un bloqueo real, el segundo debe reclamar otra programación con
`FOR UPDATE SKIP LOCKED`. También comprueba que una reserva vigente no se duplica
y que otro worker puede recuperarla después de su vencimiento.
