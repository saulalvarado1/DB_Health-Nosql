# Módulo de Respaldo y Recuperación ante Desastres (Backups & DRP)
## DB Health Monitor — PostgreSQL Disaster Recovery

Este módulo contiene la solución completa de respaldos automatizados, políticas de retención y procedimientos de recuperación ante desastres para la base de datos PostgreSQL de **DB Health Monitor**.

---

## 1. Estructura de Archivos

```text
backups/
├── scripts/
│   ├── backup.ps1               # Respaldo automatizado para Windows (PowerShell)
│   ├── backup.sh                # Respaldo automatizado para Linux / Bash / Cron
│   ├── restore.ps1              # Restauración y validación de hash en Windows
│   ├── restore.sh               # Restauración en Linux / Bash
│   └── schedule-backup-task.ps1 # Automatizador en Windows Task Scheduler
├── storage/                     # Directorio de almacenamiento de archivos .dump (ignorado en git)
├── logs/                        # Logs de auditoría de cada respaldo ejecutado
├── report/
│   └── REPORTE_BACKUPS_Y_RECUPERACION.md # Informe técnico formal para la rúbrica
└── README.md                    # Esta guía
```

---

## 2. Comandos de Uso Rápido

### Generar un respaldo inmediato:
* **En Windows:**
  ```powershell
  .\backups\scripts\backup.ps1
  ```
* **En Linux / Mac:**
  ```bash
  chmod +x ./backups/scripts/*.sh
  ./backups/scripts/backup.sh
  ```

El script detecta automáticamente si PostgreSQL está corriendo dentro del contenedor Docker o en el host local, genera el volcado comprimido (`-Fc`), calcula su firma **SHA-256** y elimina respaldos con más de 7 días de antigüedad.

### Restaurar la base de datos ante una contingencia:
* **En Windows:**
  ```powershell
  .\backups\scripts\restore.ps1
  ```
* **En Linux / Mac:**
  ```bash
  ./backups/scripts/restore.sh
  ```

El script verifica primero la autenticidad criptográfica del archivo `.dump` mediante su hash SHA-256 para asegurar que no esté corrupto, y luego reconstruye la base de datos con `pg_restore`.

### Programar la ejecución automática diaria:
* **En Windows (Crea tarea para ejecutarse a las 02:00 AM todos los días):**
  ```powershell
  .\backups\scripts\schedule-backup-task.ps1
  ```
* **En Linux (Agregar a crontab con `crontab -e`):**
  ```text
  0 2 * * * /opt/db-health-monitor/backups/scripts/backup.sh >/dev/null 2>&1
  ```

---

## 3. Informe Técnico de Validación

Para consultar los Acuerdos de Nivel de Servicio (RPO / RTO), la arquitectura y la evidencia de la prueba de simulación de desastre, revisa:
📄 [**REPORTE_BACKUPS_Y_RECUPERACION.md**](./report/REPORTE_BACKUPS_Y_RECUPERACION.md)
