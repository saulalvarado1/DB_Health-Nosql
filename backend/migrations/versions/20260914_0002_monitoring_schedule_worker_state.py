"""Add worker state to monitoring schedules.

Revision ID: 20260914_0002
Revises: 20260913_0001
Create Date: 2026-09-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260914_0002"
down_revision = "20260913_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitoring_schedules",
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column("monitoring_schedules", sa.Column("last_run_at", sa.DateTime(timezone=True)))
    op.add_column("monitoring_schedules", sa.Column("lease_owner", sa.String(length=120)))
    op.add_column(
        "monitoring_schedules", sa.Column("lease_expires_at", sa.DateTime(timezone=True))
    )
    op.add_column("monitoring_schedules", sa.Column("last_error", sa.Text()))
    op.create_index(
        "ix_monitoring_schedules_due",
        "monitoring_schedules",
        ["is_enabled", "next_run_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_monitoring_schedules_due", table_name="monitoring_schedules")
    op.drop_column("monitoring_schedules", "last_error")
    op.drop_column("monitoring_schedules", "lease_expires_at")
    op.drop_column("monitoring_schedules", "lease_owner")
    op.drop_column("monitoring_schedules", "last_run_at")
    op.drop_column("monitoring_schedules", "next_run_at")
