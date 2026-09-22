# Catálogo de métricas V1

Fecha: 22 de septiembre de 2026

El monitor obtiene indicadores con cuentas de solo lectura. MongoDB se consulta
mediante `ping` y `serverStatus`; Redis mediante `PING` e `INFO`. Ningún conector
crea, modifica o elimina datos en la instancia monitorizada.

## MongoDB

| Código | Nombre visible | Unidad | Definición |
|---|---|---:|---|
| `availability` | Disponibilidad | boolean | `1` cuando `ping` y `serverStatus` responden. Una conexión fallida se guarda como una muestra fallida. |
| `connections_active` | Conexiones activas | conexiones | Conexiones que están ejecutando operaciones en ese instante. |
| `connections_available` | Conexiones disponibles | conexiones | Conexiones adicionales que MongoDB informa que puede aceptar. |
| `connections_current` | Conexiones actuales | conexiones | Conexiones abiertas reportadas por `connections.current`. Incluye las conexiones usadas por el propio monitoreo durante la consulta. |
| `connections_usage_percent` | Uso de conexiones | % | `current / (current + available) × 100`. Devuelve `0` si MongoDB no informa capacidad. |
| `documents_read_total` | Documentos devueltos | documentos | Documentos devueltos acumulados desde el último inicio. |
| `documents_written_total` | Documentos escritos | documentos | Suma acumulada de documentos insertados, actualizados y eliminados. |
| `global_lock_active_clients` | Clientes activos | clientes | Clientes activos reportados por el estado del bloqueo global. |
| `global_lock_queue_total` | Operaciones en espera | operaciones | Operaciones que esperan adquirir un bloqueo en ese instante. |
| `memory_resident_mb` | Memoria residente | MB | Memoria residente del proceso, reportada en `mem.resident`. |
| `network_bytes_in` | Red recibida | bytes | Bytes recibidos acumulados desde el último inicio del proceso. |
| `network_bytes_out` | Red enviada | bytes | Bytes enviados acumulados desde el último inicio del proceso. |
| `network_requests_total` | Solicitudes de red | solicitudes | Solicitudes de red acumuladas desde el último inicio. |
| `open_cursors` | Cursores abiertos | cursores | Cursores abiertos en ese instante. |
| `operations_total` | Operaciones acumuladas | operaciones | Suma de `insert`, `query`, `update`, `delete`, `getmore` y `command` desde el último inicio. |
| `query_scanned_documents_total` | Documentos examinados | documentos | Documentos examinados acumulados por el ejecutor de consultas. |
| `query_scanned_keys_total` | Claves de índice examinadas | claves | Entradas de índice examinadas acumuladas por el ejecutor de consultas. |
| `uptime_seconds` | Tiempo activo | segundos | Segundos transcurridos desde el último inicio de MongoDB. |
| `wiredtiger_cache_dirty_percent` | Caché sucia WiredTiger | % | Bytes modificados pendientes en caché sobre el máximo configurado. |
| `wiredtiger_cache_usage_percent` | Uso de caché WiredTiger | % | Bytes presentes en caché sobre el máximo configurado. Devuelve `0` si el motor no expone esa capacidad. |

## Redis

| Código | Nombre visible | Unidad | Definición |
|---|---|---:|---|
| `availability` | Disponibilidad | boolean | `1` cuando `PING` e `INFO` responden. Una conexión fallida se guarda como una muestra fallida. |
| `blocked_clients` | Clientes bloqueados | clientes | Clientes esperando una operación bloqueante. |
| `connected_clients` | Clientes conectados | clientes | Clientes conectados en ese instante, incluida la conexión temporal del monitor. |
| `connected_replicas` | Réplicas conectadas | réplicas | Réplicas conectadas cuando el nodo actúa como primario; cero es normal en un nodo independiente. |
| `evicted_keys` | Claves expulsadas | claves | Claves expulsadas acumuladas por la política de memoria desde el último inicio. |
| `expired_keys` | Claves expiradas | claves | Claves expiradas acumuladas desde el último inicio. |
| `expiring_keys_total` | Claves con expiración | claves | Suma actual de claves con TTL en todas las bases lógicas. |
| `instantaneous_input_kbps` | Entrada de red | KB/s | Tráfico entrante instantáneo informado por Redis. |
| `instantaneous_output_kbps` | Salida de red | KB/s | Tráfico saliente instantáneo informado por Redis. |
| `keys_total` | Claves almacenadas | claves | Suma actual de claves en todas las bases lógicas. |
| `keyspace_hit_rate_percent` | Aciertos de caché | % | `keyspace_hits / (keyspace_hits + keyspace_misses) × 100`. Devuelve `0` cuando todavía no hubo búsquedas. |
| `keyspace_hits_total` | Aciertos acumulados | claves | Búsquedas de claves encontradas desde el último inicio. |
| `keyspace_misses_total` | Fallos acumulados | claves | Búsquedas de claves no encontradas desde el último inicio. |
| `latest_fork_microseconds` | Duración del último fork | µs | Tiempo empleado por la última operación `fork`, usada por persistencia y replicación. |
| `loading` | Carga de datos | estado | Indica si Redis está cargando el conjunto de datos. |
| `memory_fragmentation_ratio` | Fragmentación de memoria | razón | Relación que Redis informa entre memoria residente y memoria asignada. Debe analizarse según el asignador y la carga. |
| `memory_usage_percent` | Uso de memoria | % | `used_memory / maxmemory × 100`. Devuelve `0` cuando `maxmemory` no está configurado. |
| `network_input_bytes_total` | Red recibida | bytes | Bytes recibidos acumulados desde el último inicio. |
| `network_output_bytes_total` | Red enviada | bytes | Bytes enviados acumulados desde el último inicio. |
| `operations_per_second` | Operaciones por segundo | op/s | Rendimiento instantáneo informado por Redis. |
| `persistence_last_save_success` | Último guardado | estado | Indica si el último guardado RDB en segundo plano terminó correctamente. |
| `pubsub_channels` | Canales Pub/Sub | canales | Canales Pub/Sub con suscriptores activos. |
| `rejected_connections` | Conexiones rechazadas | conexiones | Conexiones rechazadas acumuladas por alcanzar `maxclients`. |
| `total_commands_processed` | Comandos procesados | operaciones | Comandos procesados acumulados desde el último inicio. |
| `total_connections_received` | Conexiones recibidas | conexiones | Conexiones aceptadas acumuladas desde el último inicio. |
| `uptime_seconds` | Tiempo activo | segundos | Segundos transcurridos desde el último inicio de Redis. |
| `used_memory_bytes` | Memoria usada | bytes | Memoria total asignada por Redis mediante su asignador. |

## Métricas, umbrales y puntuación

Cada valor mostrado incluye uno de estos diagnósticos:

- **Saludable:** el valor cumple el umbral configurado o una condición segura
  que puede comprobarse directamente.
- **Advertencia:** existe presión, una variación anómala o una condición que
  debería revisarse.
- **Crítica:** la condición orientativa es severa o se alcanzó un umbral
  crítico configurado.
- **Informativa:** el valor aislado depende de la capacidad y la carga del
  entorno, por lo que no sería responsable calificarlo como bueno o malo.

La interfaz identifica además la base del diagnóstico: `threshold` para un
umbral del usuario, `heuristic` para una regla orientativa documentada e
`informational` cuando hace falta contexto. Los contadores de expulsiones y
conexiones rechazadas se comparan con la muestra anterior; así se informa sobre
eventos nuevos en vez de juzgar incorrectamente el total acumulado.

Una métrica observada no equivale necesariamente a una condición de alerta. La
V1 mantiene reglas predeterminadas solamente para:

- disponibilidad de MongoDB;
- disponibilidad de Redis;
- porcentaje de uso de memoria de Redis.

Los contadores acumulados siempre crecen hasta que el servicio se reinicia y no
deben compararse con un umbral fijo. Otros indicadores, como fragmentación,
aciertos de caché o uso de conexiones, necesitan una línea base del entorno
antes de definir valores de advertencia y criticidad. Por ello se muestran y se
guardan para diagnóstico, pero no modifican por sí solos el puntaje de salud.

En una siguiente evolución se pueden calcular tasas y cambios entre muestras,
por ejemplo bytes por segundo, expulsiones por minuto y reinicios detectados.
Esas métricas derivadas son más adecuadas para alertas que los acumulados crudos.
