"""Expand operational metrics for MongoDB and Redis.

Revision ID: 20260922_0005
Revises: 20260922_0004
Create Date: 2026-09-22
"""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql.selectable import TableClause

revision = "20260922_0005"
down_revision = "20260922_0004"
branch_labels = None
depends_on = None


def definition(
    number: int,
    engine: str,
    code: str,
    display_name: str,
    unit: str,
    direction: str,
    description: str,
) -> dict[str, object]:
    return {
        "id": UUID(f"00000000-0000-0000-0000-{number:012d}"),
        "engine_id": engine,
        "code": code,
        "display_name": display_name,
        "unit": unit,
        "alert_direction": direction,
        "description": description,
        "is_enabled": True,
    }


METRIC_DEFINITIONS = [
    definition(
        110,
        "mongodb",
        "connections_available",
        "Conexiones disponibles",
        "connections",
        "below",
        "Conexiones adicionales que MongoDB puede aceptar.",
    ),
    definition(
        111,
        "mongodb",
        "connections_active",
        "Conexiones activas",
        "connections",
        "above",
        "Conexiones que ejecutan operaciones en ese instante.",
    ),
    definition(
        112,
        "mongodb",
        "global_lock_queue_total",
        "Operaciones en espera",
        "operations",
        "above",
        "Operaciones esperando adquirir un bloqueo.",
    ),
    definition(
        113,
        "mongodb",
        "global_lock_active_clients",
        "Clientes activos",
        "clients",
        "above",
        "Clientes activos reportados por el estado del bloqueo global.",
    ),
    definition(
        114,
        "mongodb",
        "open_cursors",
        "Cursores abiertos",
        "cursors",
        "above",
        "Cursores abiertos actualmente en MongoDB.",
    ),
    definition(
        115,
        "mongodb",
        "documents_read_total",
        "Documentos devueltos",
        "documents",
        "above",
        "Documentos devueltos acumulados desde el último inicio.",
    ),
    definition(
        116,
        "mongodb",
        "documents_written_total",
        "Documentos escritos",
        "documents",
        "above",
        "Documentos insertados, actualizados o eliminados desde el último inicio.",
    ),
    definition(
        117,
        "mongodb",
        "query_scanned_keys_total",
        "Claves de índice examinadas",
        "keys",
        "above",
        "Entradas de índice examinadas acumuladas por el ejecutor de consultas.",
    ),
    definition(
        118,
        "mongodb",
        "query_scanned_documents_total",
        "Documentos examinados",
        "documents",
        "above",
        "Documentos examinados acumulados por el ejecutor de consultas.",
    ),
    definition(
        119,
        "mongodb",
        "wiredtiger_cache_dirty_percent",
        "Caché sucia WiredTiger",
        "percent",
        "above",
        "Porcentaje de la capacidad de caché ocupado por datos modificados pendientes.",
    ),
    definition(
        120,
        "mongodb",
        "network_requests_total",
        "Solicitudes de red",
        "requests",
        "above",
        "Solicitudes de red acumuladas desde el último inicio.",
    ),
    definition(
        212,
        "redis",
        "total_connections_received",
        "Conexiones recibidas",
        "connections",
        "above",
        "Conexiones aceptadas acumuladas desde el último inicio.",
    ),
    definition(
        213,
        "redis",
        "total_commands_processed",
        "Comandos procesados",
        "operations",
        "above",
        "Comandos procesados acumulados desde el último inicio.",
    ),
    definition(
        214,
        "redis",
        "expired_keys",
        "Claves expiradas",
        "keys",
        "above",
        "Claves expiradas acumuladas desde el último inicio.",
    ),
    definition(
        215,
        "redis",
        "keyspace_hits_total",
        "Aciertos acumulados",
        "keys",
        "above",
        "Búsquedas de claves encontradas desde el último inicio.",
    ),
    definition(
        216,
        "redis",
        "keyspace_misses_total",
        "Fallos acumulados",
        "keys",
        "above",
        "Búsquedas de claves no encontradas desde el último inicio.",
    ),
    definition(
        217,
        "redis",
        "network_input_bytes_total",
        "Red recibida",
        "bytes",
        "above",
        "Bytes recibidos acumulados desde el último inicio.",
    ),
    definition(
        218,
        "redis",
        "network_output_bytes_total",
        "Red enviada",
        "bytes",
        "above",
        "Bytes enviados acumulados desde el último inicio.",
    ),
    definition(
        219,
        "redis",
        "instantaneous_input_kbps",
        "Entrada de red",
        "kilobytes/second",
        "above",
        "Tráfico entrante instantáneo informado por Redis.",
    ),
    definition(
        220,
        "redis",
        "instantaneous_output_kbps",
        "Salida de red",
        "kilobytes/second",
        "above",
        "Tráfico saliente instantáneo informado por Redis.",
    ),
    definition(
        221,
        "redis",
        "pubsub_channels",
        "Canales Pub/Sub",
        "channels",
        "above",
        "Canales Pub/Sub con suscriptores activos.",
    ),
    definition(
        222,
        "redis",
        "keys_total",
        "Claves almacenadas",
        "keys",
        "above",
        "Suma de claves almacenadas en todas las bases lógicas.",
    ),
    definition(
        223,
        "redis",
        "expiring_keys_total",
        "Claves con expiración",
        "keys",
        "above",
        "Suma de claves con tiempo de expiración configurado.",
    ),
    definition(
        224,
        "redis",
        "connected_replicas",
        "Réplicas conectadas",
        "replicas",
        "below",
        "Réplicas conectadas al nodo cuando actúa como primario.",
    ),
    definition(
        225,
        "redis",
        "latest_fork_microseconds",
        "Duración del último fork",
        "microseconds",
        "above",
        "Microsegundos empleados por la última operación fork.",
    ),
    definition(
        226,
        "redis",
        "persistence_last_save_success",
        "Último guardado",
        "success_boolean",
        "below",
        "Indica si el último guardado RDB en segundo plano terminó correctamente.",
    ),
    definition(
        227,
        "redis",
        "loading",
        "Carga de datos",
        "loading_boolean",
        "above",
        "Indica si Redis está cargando el conjunto de datos.",
    ),
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
    metric_ids = [item["id"] for item in METRIC_DEFINITIONS]
    definitions = metric_definitions_table()
    op.execute(definitions.delete().where(definitions.c.id.in_(metric_ids)))
