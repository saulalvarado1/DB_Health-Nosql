"""Expand the MongoDB and Redis metric catalog.

Revision ID: 20260922_0004
Revises: 20260914_0003
Create Date: 2026-09-22
"""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.selectable import TableClause

revision = "20260922_0004"
down_revision = "20260914_0003"
branch_labels = None
depends_on = None


METRIC_DEFINITIONS = [
    {
        "id": UUID("00000000-0000-0000-0000-000000000105"),
        "engine_id": "mongodb",
        "code": "connections_usage_percent",
        "display_name": "Uso de conexiones",
        "unit": "percent",
        "alert_direction": "above",
        "description": "Porcentaje de conexiones actuales sobre la capacidad reportada.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000106"),
        "engine_id": "mongodb",
        "code": "uptime_seconds",
        "display_name": "Tiempo activo",
        "unit": "seconds",
        "alert_direction": "below",
        "description": "Segundos transcurridos desde el último inicio de MongoDB.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000107"),
        "engine_id": "mongodb",
        "code": "network_bytes_in",
        "display_name": "Red recibida",
        "unit": "bytes",
        "alert_direction": "above",
        "description": "Bytes recibidos acumulados desde el inicio de MongoDB.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000108"),
        "engine_id": "mongodb",
        "code": "network_bytes_out",
        "display_name": "Red enviada",
        "unit": "bytes",
        "alert_direction": "above",
        "description": "Bytes enviados acumulados desde el inicio de MongoDB.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000109"),
        "engine_id": "mongodb",
        "code": "wiredtiger_cache_usage_percent",
        "display_name": "Uso de caché WiredTiger",
        "unit": "percent",
        "alert_direction": "above",
        "description": "Porcentaje de la caché WiredTiger que está en uso.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000207"),
        "engine_id": "redis",
        "code": "blocked_clients",
        "display_name": "Clientes bloqueados",
        "unit": "clients",
        "alert_direction": "above",
        "description": "Clientes esperando una operación bloqueante en Redis.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000208"),
        "engine_id": "redis",
        "code": "evicted_keys",
        "display_name": "Claves expulsadas",
        "unit": "keys",
        "alert_direction": "above",
        "description": "Claves expulsadas acumuladas por el límite de memoria de Redis.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000209"),
        "engine_id": "redis",
        "code": "keyspace_hit_rate_percent",
        "display_name": "Aciertos de caché",
        "unit": "percent",
        "alert_direction": "below",
        "description": "Porcentaje de búsquedas de claves que Redis resolvió con éxito.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000210"),
        "engine_id": "redis",
        "code": "memory_fragmentation_ratio",
        "display_name": "Fragmentación de memoria",
        "unit": "ratio",
        "alert_direction": "above",
        "description": "Relación entre memoria residente y memoria asignada por Redis.",
        "is_enabled": True,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000211"),
        "engine_id": "redis",
        "code": "uptime_seconds",
        "display_name": "Tiempo activo",
        "unit": "seconds",
        "alert_direction": "below",
        "description": "Segundos transcurridos desde el último inicio de Redis.",
        "is_enabled": True,
    },
]


def metric_definitions_table() -> TableClause:
    return sa.table(
        "metric_definitions",
        sa.column("id", sa.Uuid),
        sa.column("engine_id", sa.String),
        sa.column("code", sa.String),
        sa.column("display_name", sa.String),
        sa.column("unit", sa.String),
        sa.column("alert_direction", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_enabled", sa.Boolean),
    )


def upgrade() -> None:
    op.bulk_insert(metric_definitions_table(), METRIC_DEFINITIONS)


def downgrade() -> None:
    metric_ids = [definition["id"] for definition in METRIC_DEFINITIONS]
    definitions = metric_definitions_table()
    op.execute(definitions.delete().where(definitions.c.id.in_(metric_ids)))
