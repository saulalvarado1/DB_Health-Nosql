# Traspaso de contexto a Antigravity — DB Health Monitor

Fecha de corte: 22 de septiembre de 2026  
Rama verificada: `main`  
Commit de referencia: `e777a4c` (`Automatiza pruebas E2E aisladas de la V1`)

## Propósito

Este documento permite continuar el proyecto en Google Antigravity sin importar
la conversación completa que originó el trabajo. Resume el alcance, la
arquitectura, las decisiones, la evidencia y el próximo objetivo. No contiene
contraseñas, tokens, URI reales ni contenido de archivos `.env`.

Antigravity debe trabajar con el repositorio como fuente primaria y no asumir
que este documento reemplaza la inspección del código.

## Orden de lectura y fuentes de verdad

Antes de proponer o modificar código:

1. Leer `AGENTS.md`.
2. Comprobar `git status`, `git log -5 --oneline` y el commit actual.
3. Inspeccionar el código y las pruebas relacionados con la tarea.
4. Leer este documento.
5. Consultar, según corresponda:
   - `docs/metric-catalog.md`;
   - `docs/data-model.md`;
   - `docs/non-functional-requirements.md`;
   - `docs/backend-v1-audit.md`;
   - `docs/frontend-v1-audit.md`;
   - `docs/e2e-audit.md`;
   - `docs/deployment-audit.md`.

Si existe una contradicción, prevalecen el código y las pruebas del commit
actual. Después prevalecen este documento y las auditorías más recientes.

`docs/backend-v1-audit.md` conserva un hallazgo histórico que indicaba que el
E2E del frontend estaba pendiente. Ese punto ya fue resuelto posteriormente y
su evidencia vigente se encuentra en `docs/e2e-audit.md`.

## Estado resumido

La V1 es funcional y está validada localmente. El backend, el frontend, el
worker, PostgreSQL, MongoDB y Redis completaron pruebas unitarias, de
integración y un recorrido E2E con navegador real. La composición de producción
también arrancó correctamente en Docker.

El proyecto todavía no debe declararse preparado para producción. El próximo
bloque consiste en desplegar un entorno `staging` real, verificar HTTPS,
secretos, copias de seguridad, observabilidad y capacidad.

Al generar este documento, `main` estaba sincronizada con `origin/main` y no
había cambios locales pendientes. Este dato debe volver a comprobarse al
iniciar una sesión nueva.

## Alcance funcional de V1

DB Health Monitor es una plataforma web multiusuario que monitoriza solamente:

- MongoDB;
- Redis.

PostgreSQL es el almacén interno de la plataforma para usuarios, instancias,
programaciones, muestras, valores, evaluaciones, umbrales y alertas. PostgreSQL
no es un motor monitorizado en V1.

Quedan fuera del alcance de V1, salvo autorización explícita:

- monitoreo de motores SQL;
- Cassandra o Neo4j;
- reparación automática;
- predicción mediante IA;
- cambios automáticos en datos del cliente;
- conversión del monolito modular en microservicios.

## Arquitectura vigente

El backend es un monolito modular FastAPI. Sus límites deben conservarse:

```text
rutas HTTP
    ↓
servicios / casos de uso
    ↓
repositorios PostgreSQL o conectores por motor
```

- `backend/app/api`: dependencias, presentadores, rutas y esquemas HTTP.
- `backend/app/services`: autenticación, registro, monitoreo, historial,
  diagnóstico, puntuación, umbrales y alertas.
- `backend/app/domain`: comandos, errores, modelos de dominio y puertos.
- `backend/app/infrastructure/repositories`: acceso SQLAlchemy a PostgreSQL.
- `backend/app/infrastructure/connectors`: comunicación de solo lectura con
  MongoDB y Redis.
- `backend/app/workers`: proceso periódico independiente de la API.
- `backend/migrations`: evolución del esquema mediante Alembic.

El frontend es React con TypeScript:

- `frontend/src/api`: contratos y cliente HTTP único;
- `frontend/src/auth`: sesión y autenticación;
- `frontend/src/services`: composición de lecturas;
- `frontend/src/pages`: coordinación de casos de uso visibles;
- `frontend/src/components`: presentación reutilizable;
- `frontend/src/core`: entorno, errores, formato y token de sesión;
- `frontend/src/hooks`: actualización periódica controlada.

No colocar lógica de negocio en las rutas FastAPI ni acceso directo a la API en
componentes visuales. El motor de salud consume métricas normalizadas y no debe
depender de clientes MongoDB o Redis.

## Flujo de monitoreo

```text
conector
  → recolección
  → normalización
  → reglas de salud
  → puntuación
  → alertas
  → historial
```

El intervalo predeterminado es de 30 segundos y permanece configurable. Cada
recolección crea una muestra histórica nueva; las muestras no se sobrescriben.

PostgreSQL reserva programaciones mediante `FOR UPDATE SKIP LOCKED`. Dos workers
no deben procesar la misma programación mientras la reserva sea vigente. Otro
worker puede recuperar una reserva vencida.

## Funciones terminadas

- Registro de cuenta e inicio de sesión con JWT.
- Hash seguro de contraseñas de usuarios.
- Aislamiento de recursos por propietario.
- Registro, listado, edición, pausa, reactivación y eliminación de instancias.
- Cifrado de las URI de conexión antes de persistirlas.
- Recolección manual y automática mediante worker independiente.
- Historial de muestras y tendencia de salud.
- Catálogo completo de métricas con estado, fundamento y explicación.
- Perfiles y reglas de umbrales personalizables por instancia.
- Puntuación de salud.
- Alertas `open`, `acknowledged` y `resolved`.
- Dashboard, inventario, detalle, umbrales y alertas en el frontend.
- Actualización periódica del detalle sin solicitudes superpuestas y suspendida
  cuando la pestaña no es visible.
- Despliegue local reproducible mediante Docker Compose.
- Flujo E2E aislado mediante Playwright y servicios Docker reales.

## Métricas y evaluación

Cada recolección correcta conserva:

- 27 métricas para Redis;
- 20 métricas para MongoDB.

El significado y las unidades se mantienen en `docs/metric-catalog.md`.

No todas las métricas afectan automáticamente la puntuación. Los umbrales
predeterminados se limitan a disponibilidad en ambos motores y uso de memoria
en Redis. Las demás métricas pueden ofrecer diagnósticos conservadores o quedar
como informativas. Esto evita alertas falsas con contadores acumulados o valores
cuyo rango saludable depende de la instalación.

Los conectores realizan únicamente operaciones administrativas de lectura:

- MongoDB: `ping` y `serverStatus`;
- Redis: `PING` e `INFO`.

Las cuentas de monitoreo no deben permitir insertar, modificar ni eliminar
datos del motor observado.

## Seguridad que no debe degradarse

- No almacenar ni registrar credenciales en texto plano.
- No devolver URI de conexión desde la API.
- Cifrar los secretos de conexiones monitorizadas.
- Exigir autenticación y pertenencia en todas las operaciones de datos.
- Responder `404` frente a recursos de otro usuario para no revelar su
  existencia.
- Usar usuarios MongoDB y Redis de privilegio mínimo y solo lectura.
- No confirmar `.env`, `.env.deploy`, contraseñas, tokens, volúmenes, cachés,
  entornos virtuales, `node_modules` ni metadatos generados.
- No imprimir secretos en pruebas, errores o logs.
- Mantener CORS con lista explícita; no usar `*` con credenciales.
- Mantener imágenes de producción sin root y sin incluir fuentes sensibles o
  dependencias de desarrollo innecesarias.

El frontend conserva el JWT en `sessionStorage`. Este riesgo está documentado;
una migración futura a cookie `HttpOnly`, `Secure` y `SameSite` exige diseñar
también protección CSRF y no debe hacerse parcialmente.

## Evidencia validada

Última línea base documentada:

```text
Backend normal                 45 passed, 3 skipped, 2 warnings
Integración de servicios       3 passed, 45 deselected, 2 warnings
Frontend                       7 archivos, 21 pruebas aprobadas
ESLint                         sin errores ni advertencias
Build TypeScript/Vite          correcto
npm audit --omit=dev           0 vulnerabilidades
Ruff                           All checks passed
E2E Microsoft Edge            1 passed
Redis                          27 métricas
MongoDB                        20 métricas
```

Las dos advertencias conocidas proceden de deprecaciones de dependencias del
cliente de pruebas de FastAPI/Starlette. No representan fallos funcionales.

El E2E utiliza siete servicios aislados: PostgreSQL, migración, API, worker,
frontend, Redis y MongoDB. Comprueba registro y nuevo login, ambos motores,
recolección automática y manual, catálogos, umbrales, apertura, reconocimiento
y resolución de alerta, pausa, reactivación y eliminación. Al finalizar elimina
solo sus contenedores, redes, volumen y secretos temporales.

## Comandos de verificación

Ejecutar desde la raíz, salvo indicación distinta.

### Backend normal

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
Set-Location ..
```

### Integración con PostgreSQL, Redis y MongoDB reales aislados

```powershell
.\backend\scripts\run_real_services_integration.ps1
```

### Frontend

```powershell
Set-Location frontend
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd audit --omit=dev
Set-Location ..
```

### E2E completo

```powershell
.\deploy\run-e2e.ps1
```

No ejecutar integración o E2E contra bases de desarrollo o producción. Los
scripts ya crean entornos temporales con nombres y puertos aislados.

## Ejecución local de producción

```powershell
.\deploy\generate-env.ps1
docker compose --env-file .env.deploy up --build --detach --wait
docker compose --env-file .env.deploy ps --all
```

La aplicación se sirve en `http://127.0.0.1:8080`. Solo el frontend publica un
puerto; API, worker y PostgreSQL permanecen en redes privadas de Docker.

Detener sin borrar el volumen:

```powershell
docker compose --env-file .env.deploy down
```

No ejecutar `down --volumes` como procedimiento normal porque destruiría la
persistencia interna.

## Estado del despliegue cloud

Se compararon Railway, Render y una VM con Docker Compose. La recomendación
actual para el entorno académico `staging` es Railway por su despliegue desde
GitHub, red privada, PostgreSQL administrado, HTTPS y costo basado en uso.

Esta elección aún no se ha materializado en recursos cloud ni en archivos de
configuración específicos del proveedor. La última interacción visual llegó a
la pantalla de selección de repositorios de Railway; no se creó el proyecto ni
se desplegó ningún servicio.

La arquitectura objetivo propuesta es:

```text
Internet
   |
   | HTTPS
   v
frontend público
   |
   | /api por red privada
   v
API privada --------> PostgreSQL administrado privado
                          ^
worker privado -----------+
   |
   +----> MongoDB monitorizado mediante TLS
   +----> Redis monitorizado mediante TLS
```

MongoDB y Redis son objetivos monitorizados, no dependencias internas del
producto. Sus URI se registran desde la aplicación y deben pertenecer a cuentas
de solo lectura.

### Próxima secuencia propuesta en Railway

1. Crear un proyecto vacío llamado `db-health-monitor-staging`.
2. Autorizar a Railway únicamente para el repositorio del proyecto.
3. Agregar PostgreSQL administrado.
4. Crear servicios separados `api`, `worker` y `frontend` desde el mismo
   monorepo.
5. Configurar `/backend` como raíz de API y worker, y `/frontend` para el
   frontend.
6. Ejecutar `python -m alembic upgrade head` como paso previo del despliegue de
   la API.
7. Mantener API, worker y PostgreSQL sin dominio público.
8. Adaptar el proxy Nginx para alcanzar la API por DNS privado del proveedor.
9. Publicar solamente el frontend y verificar HTTPS.
10. Ejecutar E2E contra `staging` sin guardar secretos ni artefactos sensibles.

Antes de implementar esta secuencia, volver a verificar la documentación
actual del proveedor. No desplegar directamente a producción.

### Variables requeridas en cloud

Configurar sus valores en el gestor de secretos, nunca en Git:

- `DATABASE_URL`;
- `JWT_SECRET_KEY`;
- `CREDENTIALS_ENCRYPTION_KEY`;
- `CORS_ALLOWED_ORIGINS`;
- `LOG_LEVEL`;
- `MONITORING_WORKER_POLL_SECONDS`;
- `MONITORING_LEASE_SECONDS`;
- `MONITORING_WORKER_BATCH_SIZE`;
- `VITE_API_BASE_URL`, solo si la topología final no mantiene `/api/v1` en el
  mismo origen.

La clave `CREDENTIALS_ENCRYPTION_KEY` debe conservarse y respaldarse de forma
segura. Perderla impide descifrar las URI ya almacenadas.

Cloudflare es opcional. Railway ya puede proporcionar HTTPS y un dominio
temporal. Cloudflare se evaluará después para dominio propio, DNS, CDN, WAF y
protección DDoS; no debe bloquear el primer ensayo cloud.

## Trabajo pendiente priorizado

### Alta prioridad: cerrar V1 desplegada

1. Desplegar `staging` en el proveedor elegido.
2. Validar migraciones, health, readiness, API, worker y frontend.
3. Conectar objetivos MongoDB y Redis accesibles desde cloud mediante TLS y
   usuarios de solo lectura.
4. Ejecutar el recorrido E2E contra HTTPS.
5. Probar copia y restauración de PostgreSQL.
6. Actualizar las auditorías con evidencia cloud sin secretos.

### Prioridad media: preparación operativa

1. Ejecutar k6 o Locust en la infraestructura objetivo y documentar p95,
   throughput y tasa de error.
2. Añadir métricas, correlación de logs y alertas operativas de API y worker sin
   exponer datos sensibles.
3. Documentar actualización, migración, rollback y reconstrucción de imágenes.
4. Acordar y validar la matriz final de navegadores.
5. Considerar un endpoint agregado para el último estado de todas las
   instancias; actualmente el dashboard limita su concurrencia a cuatro
   solicitudes.

### Baja prioridad: deuda conocida

1. Actualizar de forma compatible las dependencias que producen dos
   advertencias de deprecación.
2. Formatear en un cambio separado los archivos históricos que no cumplen
   todavía `ruff format --check`.
3. Evaluar cookies seguras y CSRF como un cambio de seguridad completo, no como
   modificación aislada.

## Decisiones que deben preservarse

- Mantener monolito modular.
- Mantener API y worker como procesos separados construidos desde la misma
  imagen backend.
- Mantener PostgreSQL como almacén interno.
- Mantener muestras históricas inmutables.
- Mantener intervalo configurable con 30 segundos por defecto.
- No convertir automáticamente todos los diagnósticos en umbrales o alertas.
- No exponer la API públicamente si el proxy del frontend puede alcanzarla por
  red privada.
- No introducir Cloudflare antes de comprobar el despliegue básico.
- No repetir funciones ya validadas sin evidencia de un defecto.

## Historial reciente relevante

```text
e777a4c Automatiza pruebas E2E aisladas de la V1
8c57400 Amplía métricas y prepara despliegue reproducible
4345947 Implementa frontend de monitoreo V1
c461347 Valida servicios reales y configura CORS
c7cd365 Pruebas de concurrencia entre workers
9a03041 Pruebas de usuarios en base de datos de otro usuario
5f853f3 Comprobaciones de seguridad
82c2ebd Monitoreo y Alertas
```

## Procedimiento recomendado para un agente nuevo

1. No modificar archivos al comenzar.
2. Leer las fuentes indicadas y resumir el estado real.
3. Confirmar si el usuario solicita explicación, diagnóstico o implementación.
4. Para implementar, inspeccionar primero los archivos afectados y conservar
   cambios no relacionados del usuario.
5. Añadir o actualizar pruebas enfocadas.
6. Ejecutar pruebas y linters proporcionales al riesgo.
7. Revisar `git diff`, `git diff --check` y `git status`.
8. No hacer commit, push, despliegue o crear recursos de pago sin autorización
   explícita.
9. Explicar el resultado y los riesgos pendientes con evidencia.

## Prompt inicial sugerido para Antigravity

```text
Lee primero AGENTS.md, docs/antigravity-handoff.md y las auditorías que este
documento referencia. Usa el código y las pruebas del commit actual como fuente
de verdad.

DB Health Monitor V1 es una plataforma multiusuario que monitoriza únicamente
MongoDB y Redis. PostgreSQL es almacenamiento interno. Conserva el monolito
modular, el cifrado de URI, el aislamiento por usuario y las cuentas de
monitoreo de solo lectura. No expongas ni solicites secretos en el chat.

Antes de hacer cambios, ejecuta git status y git log -5 --oneline, resume el
estado actual y señala cualquier diferencia respecto del commit de referencia
e777a4c. No repitas funciones o pruebas ya terminadas.

El siguiente objetivo previsto es preparar y validar un entorno staging en
Railway con frontend público, API y worker privados, PostgreSQL administrado,
migraciones Alembic y secretos gestionados. Presenta primero el plan exacto y
separa las acciones locales reversibles de cualquier acción cloud con costo o
efecto externo.
```

## Nota final de seguridad

La conversación original incluyó capturas de interfaces y comandos de prueba.
No debe copiarse íntegramente a otro sistema porque podría contener encabezados
de autorización, identificadores, correos o secretos temporales. Este documento
y las auditorías constituyen el traspaso saneado.
