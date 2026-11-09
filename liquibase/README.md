# Módulo de Control de Versiones con Liquibase
## DB Health Monitor — PostgreSQL Schema Migrations

Este módulo implementa el control de versiones formal de la base de datos PostgreSQL utilizando **Liquibase Community v4.27**.

---

## 1. Estructura de Directorios

```text
liquibase/
├── changelog/
│   ├── db.changelog-master.xml               # Changelog maestro orquestador
│   ├── 01-create-initial-schema.xml          # Tablas base en 3FN
│   ├── 02-insert-initial-seeds.xml           # Semillas de motores y métricas base
│   ├── 03-expand-metric-catalog.xml          # Ampliación a 47 métricas
│   ├── 04-add-alert-deduplication.xml        # Deduplicación de alertas
│   └── 05-add-telegram-notification-columns.xml # Notificaciones Telegram
├── report/
│   ├── REPORTE_MIGRACIONES_LIQUIBASE.md      # Informe técnico formal
│   └── liquibase-execution-report.html       # Reporte visual interactivo HTML
├── liquibase.properties                      # Parámetros de conexión JDBC
├── run-liquibase.ps1                         # Runner PowerShell vía Docker
├── run-liquibase.sh                          # Runner Bash para Linux/Mac
└── README.md                                 # Esta documentación
```

---

## 2. Cómo Ejecutarlo sin Instalar Java

Gracias a Docker, no es necesario instalar Java ni Liquibase en tu máquina. Los scripts descargan y corren el contenedor oficial de Liquibase automáticamente.

### En Windows (PowerShell):
```powershell
# Aplicar todas las migraciones pendientes:
.\liquibase\run-liquibase.ps1 -Action update

# Consultar el estado de cambios:
.\liquibase\run-liquibase.ps1 -Action status

# Ver el historial de changesets aplicados:
.\liquibase\run-liquibase.ps1 -Action history
```

### En Linux / Mac (Bash):
```bash
chmod +x ./liquibase/run-liquibase.sh
./liquibase/run-liquibase.sh update
```

---

## 3. Reportes de Auditoría

1. 📄 **[Informe Técnico en Markdown](./report/REPORTE_MIGRACIONES_LIQUIBASE.md):** Contiene la justificación, matriz de changesets, rollback plans y evidencia de consola para entregar al docente.
2. 🌐 **[Reporte Visual HTML](./report/liquibase-execution-report.html):** Puedes hacer doble clic en este archivo para abrirlo en cualquier navegador web y ver la tabla interactiva de ejecuciones.
