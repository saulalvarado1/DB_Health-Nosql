#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# LIQUIBASE MIGRATION RUNNER (BASH / LINUX / MAC)
# =============================================================================

ACTION="${1:-update}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-db_health_monitor}"
DB_USER="${DB_USER:-db_health_app}"
DB_PASS="${DB_PASS:-db_health_secret}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JDBC_URL="jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "========================================================="
echo "     LIQUIBASE MIGRATION RUNNER — DB HEALTH MONITOR      "
echo "========================================================="
echo "Acción solicitada: ${ACTION}"
echo "Destino: ${JDBC_URL}"
echo ""

docker run --rm \
  -v "${SCRIPT_DIR}:/liquibase/workspace" \
  --network host \
  liquibase/liquibase:4.29.2 \
  --searchPath=/liquibase/workspace \
  --defaults-file=/liquibase/workspace/liquibase.properties \
  --url="${JDBC_URL}" \
  --username="${DB_USER}" \
  --password="${DB_PASS}" \
  --changeLogFile=changelog/db.changelog-master.xml \
  "${ACTION}"

echo ""
echo "Operación de Liquibase completada con éxito."
