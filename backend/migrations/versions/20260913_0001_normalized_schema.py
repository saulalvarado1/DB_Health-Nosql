"""Create normalized DB Health Monitor schema.

Revision ID: 20260913_0001
Revises:
Create Date: 2026-09-13
"""

from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "20260913_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "database_engines",
        sa.Column("id", sa.String(40), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("display_name"),
    )
    op.bulk_insert(
        sa.table(
            "database_engines",
            sa.column("id", sa.String),
            sa.column("display_name", sa.String),
            sa.column("is_enabled", sa.Boolean),
        ),
        [
            {"id": "mongodb", "display_name": "MongoDB", "is_enabled": True},
            {"id": "redis", "display_name": "Redis", "is_enabled": True},
        ],
    )

    op.create_table(
        "monitored_databases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("engine_id", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("connection_uri_encrypted", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["engine_id"], ["database_engines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "engine_id", "name", name="uq_monitored_database_owner_engine_name"),
    )
    op.create_index("ix_monitored_databases_owner_id", "monitored_databases", ["owner_id"])

    op.create_table(
        "monitoring_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitored_database_id", sa.Uuid(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), server_default="30", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("interval_seconds >= 10", name="ck_monitoring_schedule_minimum_interval"),
        sa.ForeignKeyConstraint(
            ["monitored_database_id"], ["monitored_databases.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("monitored_database_id"),
    )

    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("engine_id", sa.String(40), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("alert_direction", sa.String(10), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["engine_id"], ["database_engines.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "alert_direction IN ('above', 'below')", name="ck_metric_definition_alert_direction"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("engine_id", "code", name="uq_metric_definition_engine_code"),
    )

    op.bulk_insert(
        sa.table(
            "metric_definitions",
            sa.column("id", sa.Uuid),
            sa.column("engine_id", sa.String),
            sa.column("code", sa.String),
            sa.column("display_name", sa.String),
            sa.column("unit", sa.String),
            sa.column("alert_direction", sa.String),
            sa.column("description", sa.Text),
            sa.column("is_enabled", sa.Boolean),
        ),
        [
            {
                "id": UUID("00000000-0000-0000-0000-000000000101"),
                "engine_id": "mongodb",
                "code": "availability",
                "display_name": "Disponibilidad",
                "unit": "boolean",
                "alert_direction": "below",
                "description": "1 si MongoDB respondió al ping; 0 en caso contrario.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000102"),
                "engine_id": "mongodb",
                "code": "connections_current",
                "display_name": "Conexiones actuales",
                "unit": "connections",
                "alert_direction": "above",
                "description": "Conexiones activas reportadas por MongoDB.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000103"),
                "engine_id": "mongodb",
                "code": "memory_resident_mb",
                "display_name": "Memoria residente",
                "unit": "MB",
                "alert_direction": "above",
                "description": "Memoria residente reportada por MongoDB.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000104"),
                "engine_id": "mongodb",
                "code": "operations_total",
                "display_name": "Operaciones acumuladas",
                "unit": "operations",
                "alert_direction": "above",
                "description": "Suma acumulada de operaciones reportadas por MongoDB.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000201"),
                "engine_id": "redis",
                "code": "availability",
                "display_name": "Disponibilidad",
                "unit": "boolean",
                "alert_direction": "below",
                "description": "1 si Redis respondió al ping; 0 en caso contrario.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000202"),
                "engine_id": "redis",
                "code": "used_memory_bytes",
                "display_name": "Memoria usada",
                "unit": "bytes",
                "alert_direction": "above",
                "description": "Memoria usada por Redis.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000203"),
                "engine_id": "redis",
                "code": "memory_usage_percent",
                "display_name": "Uso de memoria",
                "unit": "percent",
                "alert_direction": "above",
                "description": "Porcentaje de maxmemory utilizado; 0 si maxmemory no está definido.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000204"),
                "engine_id": "redis",
                "code": "connected_clients",
                "display_name": "Clientes conectados",
                "unit": "clients",
                "alert_direction": "above",
                "description": "Clientes conectados a Redis.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000205"),
                "engine_id": "redis",
                "code": "operations_per_second",
                "display_name": "Operaciones por segundo",
                "unit": "operations/second",
                "alert_direction": "above",
                "description": "Operaciones instantáneas por segundo reportadas por Redis.",
                "is_enabled": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000206"),
                "engine_id": "redis",
                "code": "rejected_connections",
                "display_name": "Conexiones rechazadas",
                "unit": "connections",
                "alert_direction": "above",
                "description": "Conexiones rechazadas desde el inicio de Redis.",
                "is_enabled": True,
            },
        ],
    )

    op.create_table(
        "threshold_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("engine_id", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["engine_id"], ["database_engines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "engine_id", "name", name="uq_threshold_profile_owner_engine_name"),
    )
    op.create_index(
        "uq_threshold_profiles_default_per_engine_owner",
        "threshold_profiles",
        ["owner_id", "engine_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.create_table(
        "threshold_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("metric_definition_id", sa.Uuid(), nullable=False),
        sa.Column("warning_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("critical_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["metric_definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_id"], ["threshold_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "metric_definition_id", name="uq_threshold_rule_profile_metric"),
    )

    op.create_table(
        "database_threshold_profiles",
        sa.Column("monitored_database_id", sa.Uuid(), nullable=False),
        sa.Column("threshold_profile_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["monitored_database_id"], ["monitored_databases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["threshold_profile_id"], ["threshold_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("monitored_database_id"),
    )

    op.create_table(
        "metric_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitored_database_id", sa.Uuid(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collection_succeeded", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["monitored_database_id"], ["monitored_databases.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_samples_database_collected", "metric_samples", ["monitored_database_id", "collected_at"])

    op.create_table(
        "metric_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("metric_definition_id", sa.Uuid(), nullable=False),
        sa.Column("numeric_value", sa.Numeric(20, 6), nullable=False),
        sa.ForeignKeyConstraint(["metric_definition_id"], ["metric_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sample_id"], ["metric_samples.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id", "metric_definition_id", name="uq_metric_value_sample_definition"),
    )

    op.create_table(
        "health_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_health_assessment_score_range"),
        sa.CheckConstraint(
            "status IN ('healthy', 'warning', 'critical', 'unknown')",
            name="ck_health_assessment_status",
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["metric_samples.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id"),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitored_database_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=True),
        sa.Column("threshold_rule_id", sa.Uuid(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('warning', 'critical')", name="ck_alert_severity"),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')", name="ck_alert_status"
        ),
        sa.ForeignKeyConstraint(
            ["monitored_database_id"], ["monitored_databases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["metric_samples.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["threshold_rule_id"], ["threshold_rules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_database_status", "alerts", ["monitored_database_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_alerts_database_status", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("health_assessments")
    op.drop_table("metric_values")
    op.drop_index("ix_metric_samples_database_collected", table_name="metric_samples")
    op.drop_table("metric_samples")
    op.drop_table("database_threshold_profiles")
    op.drop_table("threshold_rules")
    op.drop_index("uq_threshold_profiles_default_per_engine_owner", table_name="threshold_profiles")
    op.drop_table("threshold_profiles")
    op.drop_table("metric_definitions")
    op.drop_table("monitoring_schedules")
    op.drop_index("ix_monitored_databases_owner_id", table_name="monitored_databases")
    op.drop_table("monitored_databases")
    op.drop_table("database_engines")
    op.drop_table("users")
