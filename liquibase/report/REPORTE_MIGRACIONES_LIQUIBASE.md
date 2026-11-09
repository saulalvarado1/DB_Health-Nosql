# Informe Técnico de Versionamiento de Base de Datos con Liquibase
## DB Health Monitor (v1.0)
**Institución:** Universidad Privada de Tacna (UPT) — Facultad de Ingeniería (EPIS)  
**Curso:** SI-783 Base de Datos II  
**Grupo:** Grupo 3  
**Motor de Persistencia:** PostgreSQL 16 (Relacional en Tercera Forma Normal - 3FN)  
**Herramienta de Control de Cambios:** Liquibase Community v4.27  

---

## 1. Introducción y Justificación Técnica

En la ingeniería de software moderna y las prácticas de **DevOps para Bases de Datos (Database CI/CD)**, los esquemas de bases de datos nunca deben modificarse de forma manual mediante consolas interactivas o scripts ad-hoc no rastreados. Hacerlo genera el problema conocido como *"Deriva del Esquema"* (*Schema Drift*) y dificulta la replicación de ambientes (desarrollo, pruebas, producción).

**Liquibase** resuelve este problema al tratar la estructura de la base de datos como código versionable. En este proyecto se utilizó para:
1. Asegurar la **trazabilidad histórica** de cada tabla, columna, restricción e índice creado.
2. Garantizar **idempotencia y reproducibilidad** en cualquier servidor o contenedor PostgreSQL.
3. Proporcionar un **mecanismo de reversión (*Rollback*)** automatizado ante incidentes.
4. Evitar condiciones de carrera concurrentes mediante el bloqueo transaccional de `DATABASECHANGELOGLOCK`.

---

## 2. Tablas Internas de Auditoría de Liquibase

Al ejecutarse Liquibase contra la base de datos `db_health_monitor`, se crean automáticamente dos tablas de control:

1. **`DATABASECHANGELOG`:**
   Registra el historial completo de ejecución:
   * `ID`: Identificador del changeset.
   * `AUTHOR`: Autor del cambio (`group-3`).
   * `FILENAME`: Archivo fuente dentro de `changelog/`.
   * `DATEEXECUTED`: Marca de tiempo UTC exacta en que se aplicó la migración.
   * `ORDEREXECUTED`: Secuencia numérica incremental de ejecución.
   * `EXECTYPE`: Resultado de la operación (`EXECUTED`).
   * `MD5SUM`: Hash criptográfico del contenido del changeset (detecta alteraciones accidentales del código SQL/XML).
   * `COMMENTS`: Descripción funcional del cambio.

2. **`DATABASECHANGELOGLOCK`:**
   Garantiza que solo una instancia de la aplicación o del pipeline de CI/CD aplique cambios a la vez. Utiliza una bandera booleana `LOCKED` con un tiempo de expiración y la dirección IP del nodo que adquirió el bloqueo.

---

## 3. Matriz de Changesets Implementados

El Changelog Maestro (`changelog/db.changelog-master.xml`) orquesta 5 fases secuenciales:

| ID del ChangeSet | Archivo | Entidades Afectadas | Tipo de Cambio | Estrategia de Rollback |
| :--- | :--- | :--- | :--- | :--- |
| **`01-create-table-users`** | `01-create-initial-schema.xml` | `users` | Creación de tabla y constraint único para emails. | `DROP TABLE users CASCADE;` |
| **`02-create-table-database-engines`** | `01-create-initial-schema.xml` | `database_engines` | Catálogo maestro de motores (`mongodb`, `redis`). | `DROP TABLE database_engines CASCADE;` |
| **`03-create-table-monitored-databases`** | `01-create-initial-schema.xml` | `monitored_databases` | Tabla de instancias con claves foráneas e índices. | `DROP TABLE monitored_databases CASCADE;` |
| **`04-create-table-monitoring-schedules`** | `01-create-initial-schema.xml` | `monitoring_schedules` | Tabla de leases para el worker concurrente. | `DROP TABLE monitoring_schedules;` |
| **`05-create-table-metric-definitions`** | `01-create-initial-schema.xml` | `metric_definitions` | Catálogo de métricas con dirección de alerta. | `DROP TABLE metric_definitions;` |
| **`06-create-table-threshold-profiles-and-rules`** | `01-create-initial-schema.xml` | `threshold_profiles`, `threshold_rules`, `database_threshold_profiles` | Perfiles y reglas de umbral por instancia. | `DROP TABLE ... CASCADE;` |
| **`07-create-table-samples-values-and-health`** | `01-create-initial-schema.xml` | `metric_samples`, `metric_values`, `health_assessments`, `alerts` | Almacenamiento histórico inmutable y alertas. | `DROP TABLE ... CASCADE;` |
| **`02-insert-initial-seeds`** | `02-insert-initial-seeds.xml` | `database_engines`, `metric_definitions` | Inserción de semillas base (10 métricas). | `DELETE FROM metric_definitions; DELETE FROM database_engines;` |
| **`03-expand-metric-catalog-batch1`** | `03-expand-metric-catalog.xml` | `metric_definitions` | Agrega 10 métricas operativas (WiredTiger, fragmentación). | `DELETE WHERE code IN (...);` |
| **`03-expand-metric-catalog-batch2`** | `03-expand-metric-catalog.xml` | `metric_definitions` | Agrega 27 métricas avanzadas (cursores, replicación, pubsub). | `DELETE WHERE code IN (...);` |
| **`04-add-alert-deduplication`** | `04-add-alert-deduplication.xml` | `alerts` | Columna `deduplication_key` e índice parcial único. | `DROP INDEX ...; ALTER TABLE DROP COLUMN;` |
| **`05-add-telegram-notification-columns`** | `05-add-telegram-notification-columns.xml` | `monitored_databases` | Agrega columnas para bots de Telegram. | `ALTER TABLE DROP COLUMN ...;` |

---

## 4. Evidencia de Ejecución y Verificación

### Comando de Aplicación:
```bash
# En Windows (PowerShell):
.\liquibase\run-liquibase.ps1 -Action update

# En Linux / Mac (Bash):
./liquibase/run-liquibase.sh update
```

### Salida de Consola Exitosa:
```text
=========================================================
     LIQUIBASE MIGRATION RUNNER — DB HEALTH MONITOR      
=========================================================
Acción solicitada: update
Destino: jdbc:postgresql://localhost:5432/db_health_monitor

[INFO] Reading from databasechangelog
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::01-create-table-users::group-3
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::02-create-table-database-engines::group-3
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::03-create-table-monitored-databases::group-3
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::04-create-table-monitoring-schedules::group-3
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::05-create-table-metric-definitions::group-3
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::06-create-table-threshold-profiles-and-rules::group-3
[INFO] Running Changeset: changelog/01-create-initial-schema.xml::07-create-table-samples-values-and-health::group-3
[INFO] Running Changeset: changelog/02-insert-initial-seeds.xml::02-insert-initial-seeds::group-3
[INFO] Running Changeset: changelog/03-expand-metric-catalog.xml::03-expand-metric-catalog-batch1::group-3
[INFO] Running Changeset: changelog/03-expand-metric-catalog.xml::03-expand-metric-catalog-batch2::group-3
[INFO] Running Changeset: changelog/04-add-alert-deduplication.xml::04-add-alert-deduplication::group-3
[INFO] Running Changeset: changelog/05-add-telegram-notification-columns.xml::05-add-telegram-notification-columns::group-3
[INFO] Update command completed successfully.
Liquibase: Update has been successful.
```

---

## 5. Verificación de Integridad y Consulta SQL

Tras la aplicación, se puede comprobar el estado en PostgreSQL mediante la siguiente consulta:

```sql
SELECT id, author, dateexecuted, orderexecuted, exectype, md5sum, description
FROM databasechangelog
ORDER BY orderexecuted ASC;
```

**Resultado:** 12 changesets aplicados en estado `EXECUTED`, con 0 errores y bloqueo liberado.

---

## 6. Conclusión

La implementación de **Liquibase** en **DB Health Monitor** garantiza que el ciclo de vida del esquema relacional esté completamente automatizado, auditable y listo para despliegues continuos sin riesgo de desincronización entre entornos.
