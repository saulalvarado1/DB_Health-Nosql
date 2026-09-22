# DB Health Monitor

Plataforma multiusuario para monitorear la salud de instancias MongoDB y Redis.

- [`backend`](backend/README.md): API FastAPI, worker de monitoreo y persistencia PostgreSQL.
- [`frontend`](frontend/README.md): aplicación React/TypeScript.
- [`docs`](docs): modelo de datos, requisitos no funcionales y auditoría de V1.
- [`catálogo de métricas`](docs/metric-catalog.md): definición y alcance de cada indicador.

## Despliegue reproducible

La composición de producción ejecuta PostgreSQL, una migración Alembic de una
sola vez, la API, el worker y el frontend/proxy. Solo el frontend publica un
puerto; la API y PostgreSQL permanecen dentro de redes privadas de Docker.

```powershell
.\deploy\generate-env.ps1
docker compose --env-file .env.deploy up --build --detach --wait
docker compose --env-file .env.deploy ps --all
```

La aplicación queda en `http://127.0.0.1:8080`. El archivo `.env.deploy` contiene
secretos aleatorios, está ignorado por Git y no debe compartirse. Para detener
los procesos sin borrar el volumen de PostgreSQL:

```powershell
docker compose --env-file .env.deploy down
```

En una VM pública se debe anteponer HTTPS mediante el balanceador o proxy del
proveedor. Se puede mantener `APP_BIND_ADDRESS=127.0.0.1` si ese proxy se ejecuta
en la misma máquina; solo debe usarse `0.0.0.0` cuando la red y el firewall del
proveedor protejan explícitamente el puerto publicado.

La evidencia, los controles y las diferencias entre la prueba local y una nube
real están en [`docs/deployment-audit.md`](docs/deployment-audit.md).

## Prueba E2E aislada

La prueba de extremo a extremo crea un proyecto Docker temporal con PostgreSQL,
API, worker, frontend, Redis y MongoDB reales. Ejecuta el recorrido desde un
navegador y elimina al terminar únicamente los contenedores, redes, volumen y
secretos temporales de ese proyecto:

```powershell
.\deploy\run-e2e.ps1
```

El recorrido valida registro, nuevo inicio de sesión, recolección automática y
manual, 27 métricas Redis, 20 métricas MongoDB, umbrales, apertura,
reconocimiento y resolución de alertas, pausa, reactivación y eliminación. No
usa ni modifica las bases locales del desarrollador. La auditoría completa está
en [`docs/e2e-audit.md`](docs/e2e-audit.md).
