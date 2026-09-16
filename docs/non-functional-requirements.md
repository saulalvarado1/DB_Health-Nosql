# Matriz de requisitos no funcionales — DB Health Monitor

Este documento transforma los atributos de calidad del proyecto en criterios verificables. No sustituye los requisitos funcionales: indica **cómo de bien** debe operar el sistema, cómo se comprueba y qué evidencia queda en el repositorio.

> Los objetivos numéricos marcados como **propuestos** deberán ser aprobados por el equipo y el docente antes de considerarse compromisos de producción. Los informes de Visión y Factibilidad del repositorio aún son plantillas y no fijan valores medibles oficiales.

## Estado de la evidencia

| Estado | Significado |
|---|---|
| `VALIDADO` | Existe una prueba automatizada o una verificación repetible que ya pasó. |
| `PARCIAL` | La base técnica existe, pero falta una prueba del escenario completo. |
| `PENDIENTE` | Debe definirse o implementarse la prueba. |

## Matriz

| ID | Atributo | Criterio de aceptación | Método y evidencia | Estado actual |
|---|---|---|---|---|
| RNF-SEC-01 | Configuración segura | La aplicación no inicia sin `DATABASE_URL`, `JWT_SECRET_KEY` y `CREDENTIALS_ENCRYPTION_KEY`. No hay valores secretos por defecto en código. | `backend/tests/test_config.py` comprueba la ausencia de cada variable. | `VALIDADO` |
| RNF-SEC-02 | Confidencialidad | Las URI y contraseñas de bases monitorizadas se cifran en el almacén interno y no aparecen en respuestas ni logs. | `test_security.py`, `test_monitoring_worker.py` y `test_tenant_isolation_integration.py` comprueban cifrado real en PostgreSQL, respuestas sin URI y logs sin contraseñas. | `VALIDADO` |
| RNF-SEC-03 | Autenticación y autorización | Toda ruta de datos exige JWT válido; un usuario no puede leer, modificar, recolectar ni eliminar instancias de otro usuario. | `test_security.py` valida los tokens y `test_tenant_isolation_integration.py` verifica con dos usuarios y PostgreSQL real que las rutas ajenas devuelven `404`. | `VALIDADO` |
| RNF-DAT-01 | Integridad | Los datos históricos no se sobrescriben; métricas, reglas, perfiles y alertas mantienen sus claves foráneas y restricciones. | Migraciones Alembic, modelo 3FN y pruebas de validación de esquemas y umbrales. | `PARCIAL` |
| RNF-DIS-01 | Disponibilidad | `GET /health` informa que el proceso vive sin depender de PostgreSQL. `GET /health/ready` devuelve `503` si PostgreSQL no responde. | `backend/tests/test_health_routes.py`. | `VALIDADO` |
| RNF-CON-01 | Concurrencia | Dos workers no procesan la misma programación durante una reserva vigente; tras vencer la reserva, otro worker puede retomarla. | `test_worker_concurrency_integration.py` mantiene un bloqueo real entre dos conexiones PostgreSQL, verifica `SKIP LOCKED`, evita duplicados y recupera reservas vencidas. | `VALIDADO` |
| RNF-RES-01 | Tolerancia a fallos | Si falla una recolección, se registra un resultado seguro, la programación se libera y el siguiente ciclo puede continuar. | `backend/tests/test_monitoring_worker.py` y prueba manual con Redis inaccesible. | `VALIDADO` |
| RNF-PER-01 | Rendimiento | **Propuesto:** con 50 usuarios concurrentes, `GET /health` y consultas de listado deben mantener p95 menor o igual a 300 ms en el entorno objetivo. | Escenario reproducible con k6 o Locust; publicar el reporte de ejecución sin secretos. | `PENDIENTE` |
| RNF-OBS-01 | Observabilidad | API y worker generan logs de nivel configurable, sin secretos, y exponen health/readiness para supervisión. | Revisión de configuración, pruebas de no filtrado y verificación manual de endpoints. | `PARCIAL` |
| RNF-MAN-01 | Mantenibilidad | El código mantiene las capas rutas → servicios → repositorios/conectores y supera pruebas y linter. | `pytest` y `ruff check backend` desde el directorio `backend`. | `VALIDADO` |
| RNF-DES-01 | Desplegabilidad | El sistema se puede iniciar con contenedores, migrar la base automáticamente y recibir configuración únicamente mediante variables de entorno. | `Dockerfile`, composición de servicios, health checks y prueba de arranque limpio. | `PENDIENTE` |
| RNF-COM-01 | Compatibilidad | La API publica contrato OpenAPI y el frontend futuro funciona en navegadores definidos por el equipo. | `/docs`, pruebas de contrato y, al crear React, pruebas E2E en navegadores acordados. | `PARCIAL` |

## Línea base actual

El 16 de septiembre de 2026, la suite normal del backend produjo:

```text
32 passed, 2 skipped, 2 warnings
```

Las pruebas aisladas contra `db_health_monitor_test` produjeron:

```text
2 passed, 32 deselected, 2 warnings
```

Las dos advertencias son deprecaciones de dependencias usadas por el cliente de pruebas de FastAPI/Starlette. No son fallos de los requisitos ni deben resolverse instalando paquetes al azar; se atenderán al actualizar de manera compatible las dependencias de desarrollo.

Los dos casos omitidos en la suite normal requieren `TEST_DATABASE_URL`; su ejecución separada acredita aislamiento entre usuarios y concurrencia real entre conexiones PostgreSQL. Esta línea base todavía no demuestra rendimiento, despliegue en nube ni recolecciones exitosas contra servicios Redis y MongoDB reales.

## Evidencia por cada entrega

Cada requisito marcado como `VALIDADO` debe poder señalar una prueba, un comando o un reporte. El formato recomendado para una evidencia es:

```text
ID: RNF-XXX-00
Entorno: local | Docker | nube de pruebas
Comando o caso: ...
Resultado esperado: ...
Resultado obtenido: ...
Fecha y responsable: ...
Enlace al commit, reporte o captura: ...
```

No se incluirán tokens JWT, contraseñas, URI de producción ni contenido del archivo `.env` como evidencia.

## Próximo bloque de validación

El siguiente incremento se enfocará en el ciclo completo de monitoreo, en este orden:

1. Recolección exitosa contra una instancia Redis de pruebas con credenciales de solo lectura.
2. Recolección exitosa contra una instancia MongoDB de pruebas con credenciales de solo lectura.
3. Ciclo completo métrica → evaluación → alerta → resolución con servicios reales de prueba.
4. Contenedores reproducibles, prueba de carga y evidencia del entorno desplegado.

El frontend y las pruebas E2E se incorporarán después de cerrar estas validaciones del backend.
