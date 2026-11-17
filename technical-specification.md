# 📚 Especificación Técnica de Clases, Métodos y Propiedades

Documentación técnica detallada de la arquitectura orientada a objetos del sistema **DB Health Monitor (v1.0)**, cubriendo los módulos de dominio, servicios de aplicación, adaptadores de infraestructura y repositorios.

---

## 1. Módulo de Servicios de Aplicación (`app.services`)

### `AuthenticationService`
Servicio encargado del ciclo de vida de usuarios, registro y verificación de credenciales con hashing criptográfico.

* **Propiedades / Atributos:**
  * `_session: Session`: Sesión activa de SQLAlchemy para transaccionalidad ACID.
  * `_users: UserRepository`: Instancia del repositorio de persistencia de usuarios.
* **Métodos:**
  * `register(command: RegisterUserCommand) -> User`:
    * *Descripción:* Valida unicidad de correo, aplica hash con Argon2id, persiste la entidad `User` y genera los perfiles de umbrales por defecto en una transacción atómica.
    * *Parámetros:* `command.email` (str normalizado), `command.password` (str plano min 12 caracteres).
    * *Retorno:* Objeto `User` persistido.
    * *Excepciones:* `ResourceConflictError` si el correo ya existe.
  * `authenticate(email: str, password: str) -> User`:
    * *Descripción:* Recupera usuario por correo normalizado y verifica el hash de la contraseña en tiempo constante para evitar ataques de temporización.
    * *Retorno:* Entidad `User` autenticada.
    * *Excepciones:* `AuthenticationError` si las credenciales son inválidas o el usuario está inactivo.

---

### `HealthScoreEngine` (`HealthEvaluator`)
Motor determinista encargado del cálculo del puntaje de salud (0 a 100) y asignación de severidades (`HEALTHY`, `WARNING`, `CRITICAL`).

* **Propiedades / Atributos:**
  * `BASE_SCORE: int = 100`: Puntuación base inicial para toda instancia.
  * `PENALTY_WARNING: int = 20`: Puntos descontados por cada métrica en umbral de advertencia.
  * `PENALTY_CRITICAL: int = 50`: Puntos descontados por cada métrica en umbral crítico.
* **Métodos:**
  * `evaluate(metrics: dict[str, float], rules: list[ThresholdRule]) -> HealthAssessmentResult`:
    * *Descripción:* Evalúa las métricas normalizadas contra las reglas de umbral activas. Aplica el circuito de corte (Circuit Breaker) si la disponibilidad es 0.
    * *Parámetros:*
      * `metrics`: Diccionario clave-valor con telemetría normalizada.
      * `rules`: Lista de entidades `ThresholdRule` asociadas a la base de datos.
    * *Retorno:* `HealthAssessmentResult` con `score` (0-100), `status` (Enum), `penalties` (list) y `summary` explicativo.

---

### `DatabasesService`
Servicio para la gestión y orquestación del ciclo de vida de bases de datos monitoreadas.

* **Propiedades / Atributos:**
  * `_session: Session`: Conexión a la base de datos PostgreSQL.
  * `_repo: MonitoredDatabaseRepository`: Repositorio de base de datos.
  * `_encryptor: Fernet`: Cifrador simétrico AES-128 para credenciales.
* **Métodos:**
  * `create(owner_id: UUID, command: CreateDatabaseCommand) -> MonitoredDatabase`:
    * *Descripción:* Cifra la cadena de conexión con AES-128 Fernet, valida la conexión inmediata y crea la programación en 3FN.
  * `test_connection(command: TestConnectionCommand) -> ConnectionTestResult`:
    * *Descripción:* Invoca el conector respectivo (`MongoDBConnector` o `RedisConnector`) sin persistir datos para verificar conectividad remota.

---

## 2. Módulo de Infraestructura y Conectores (`app.infrastructure.connectors`)

### `MongoDBConnector`
Adaptador agentless de solo lectura para clústeres y réplicas de MongoDB.

* **Propiedades:**
  * `_connection_string: str`: URI de conexión descifrada en memoria.
  * `_timeout_ms: int = 5000`: Timeout para evitar bloqueos del worker.
* **Métodos:**
  * `collect_metrics() -> dict[str, float]`:
    * *Descripción:* Ejecuta el comando nativo `db.command('serverStatus')`.
    * *Métricas extraídas:* `connections.current`, `mem.resident`, `opcounters.query`, `opcounters.insert`, `network.bytesIn`, `uptime`.
  * `ping() -> bool`:
    * *Descripción:* Ejecuta comando nativo `db.command('ping')` para comprobar disponibilidad inmediata.

---

### `RedisConnector`
Adaptador agentless de solo lectura para instancias y nodos de Redis.

* **Propiedades:**
  * `_connection_string: str`: URI Redis (soporta standalone y TLS `rediss://`).
  * `_client: redis.Redis`: Cliente optimizado con pool de conexiones.
* **Métodos:**
  * `collect_metrics() -> dict[str, float]`:
    * *Descripción:* Ejecuta el comando nativo de bajo impacto `INFO` y `INFO commandstats`.
    * *Métricas extraídas:* `used_memory`, `maxmemory`, `connected_clients`, `instantaneous_ops_per_sec`, `hit_rate_percent`, `uptime_in_seconds`.
  * `ping() -> bool`:
    * *Descripción:* Ejecuta `client.ping()` retornando `True` si responde `PONG`.

---

## 3. Módulo de Repositorios de Persistencia (`app.infrastructure.repositories`)

### `MonitoredDatabaseRepository`
* **Métodos:**
  * `get_by_id_and_owner(db_id: UUID, owner_id: UUID) -> MonitoredDatabase | None`
  * `list_by_owner(owner_id: UUID) -> list[MonitoredDatabase]`
  * `add(entity: MonitoredDatabase) -> None`
  * `delete(entity: MonitoredDatabase) -> None`

### `MetricSampleRepository`
* **Métodos:**
  * `record_sample(db_id: UUID, samples: list[MetricSampleValue]) -> UUID`
  * `get_latest_sample(db_id: UUID) -> MetricSample | None`
  * `get_time_series(db_id: UUID, from_time: datetime, to_time: datetime) -> list[MetricSample]`

---

## 4. Módulo de Despacho y Alertas (`app.services.alerting`)

### `TelegramAlertDispatcher`
* **Propiedades:**
  * `_bot_token: str`: Token de autenticación de Telegram Bot.
  * `_chat_id: str`: Canal o chat destino para notificaciones push.
* **Métodos:**
  * `dispatch_alert(alert: Alert) -> bool`:
    * *Descripción:* Formatea el incidente en Markdown, incluye el nombre de la BD, motor, puntaje de salud actual, umbral violado y marca de tiempo.
    * *Retorno:* `True` si la API de Telegram retornó código HTTP 200.
