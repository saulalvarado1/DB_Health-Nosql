#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# SCRIPT AUTOMATIZADO DE RESPALDO (BASH / CRON) — DB HEALTH MONITOR
# =============================================================================

DB_NAME="${DB_NAME:-db_health_monitor}"
DB_USER="${DB_USER:-db_health_app}"
CONTAINER_NAME="${CONTAINER_NAME:-}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
STORAGE_DIR="${BASE_DIR}/storage"
LOG_DIR="${BASE_DIR}/logs"

mkdir -p "$STORAGE_DIR" "$LOG_DIR"

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${STORAGE_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
LOG_FILE="${LOG_DIR}/backup_${TIMESTAMP}.log"

log() {
  local msg="[$(date +"%Y-%m-%d %H:%M:%S")] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

log "========================================================="
log "    INICIANDO RESPALDO AUTOMATICO DE BASE DE DATOS       "
log "========================================================="
log "Base de datos objetivo: ${DB_NAME}"
log "Archivo de destino: $(basename "$BACKUP_FILE")"

# Detectar contenedor Docker si no se especificó
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_NAME="$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n 1 || true)"
fi

if [ -n "$CONTAINER_NAME" ]; then
  log "Contenedor PostgreSQL detectado: ${CONTAINER_NAME}"
  docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -b -v > "$BACKUP_FILE" 2>> "$LOG_FILE"
else
  log "Ejecutando pg_dump local..."
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -b -v -f "$BACKUP_FILE" 2>> "$LOG_FILE"
fi

if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
  FILE_SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
  log "Respaldo generado exitosamente (${FILE_SIZE})."

  # Checksum SHA-256
  sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
  log "Checksum SHA-256 generado con exito."

  # Política de retención: borrar respaldos mayores a RETENTION_DAYS
  log "Aplicando politica de retencion (${RETENTION_DAYS} dias)..."
  find "$STORAGE_DIR" -type f -name "*.dump" -mtime +"$RETENTION_DAYS" -exec rm -f {} +
  find "$STORAGE_DIR" -type f -name "*.sha256" -mtime +"$RETENTION_DAYS" -exec rm -f {} +
  log "OPERACION COMPLETADA EXITOSAMENTE."
else
  log "ERROR: El archivo de respaldo no fue generado correctamente."
  exit 1
fi
