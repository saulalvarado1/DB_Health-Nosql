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
