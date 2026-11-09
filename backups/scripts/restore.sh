#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# SCRIPT DE RESTAURACION Y PRUEBA DE RECUPERACION — DB HEALTH MONITOR
# =============================================================================

BACKUP_FILE="${1:-}"
DB_NAME="${DB_NAME:-db_health_monitor}"
DB_USER="${DB_USER:-db_health_app}"
CONTAINER_NAME="${CONTAINER_NAME:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
STORAGE_DIR="${BASE_DIR}/storage"

echo "========================================================="
echo "   RESTAURACION Y PRUEBA DE RECUPERACION ANTE DESASTRES  "
echo "========================================================="

# 1. Determinar archivo
if [ -z "$BACKUP_FILE" ]; then
  BACKUP_FILE="$(find "$STORAGE_DIR" -type f -name "*.dump" | sort -r | head -n 1 || true)"
  if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: No se encontraron archivos .dump en $STORAGE_DIR"
    exit 1
  fi
fi

echo "Archivo seleccionado: $(basename "$BACKUP_FILE")"
echo "Base de datos destino: ${DB_NAME}"

# 2. Verificación de Integridad con SHA-256
if [ -f "${BACKUP_FILE}.sha256" ]; then
  echo "Verificando hash SHA-256..."
  sha256sum -c "${BACKUP_FILE}.sha256"
  echo "INTEGRIDAD VERIFICADA: Archivo autentico y no alterado."
fi

# 3. Detectar contenedor
if [ -z "$CONTAINER_NAME" ]; then
  CONTAINER_NAME="$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n 1 || true)"
fi

echo "Ejecutando pg_restore..."
if [ -n "$CONTAINER_NAME" ]; then
  docker cp "$BACKUP_FILE" "${CONTAINER_NAME}:/tmp/restore_target.dump"
  docker exec "$CONTAINER_NAME" pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner /tmp/restore_target.dump
  docker exec "$CONTAINER_NAME" rm -f /tmp/restore_target.dump
else
  pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner "$BACKUP_FILE"
fi

echo "RESTAURACION COMPLETADA EXITOSAMENTE."
