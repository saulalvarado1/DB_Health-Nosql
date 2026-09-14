"""Add durable alert deduplication keys.

Revision ID: 20260914_0003
Revises: 20260914_0002
Create Date: 2026-09-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260914_0003"
down_revision = "20260914_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("deduplication_key", sa.String(length=160), nullable=True))
    op.execute(
        """
        UPDATE alerts
        SET deduplication_key = CASE
            WHEN threshold_rule_id IS NOT NULL THEN 'threshold-rule:' || threshold_rule_id::text
            ELSE 'legacy:' || id::text
        END
        WHERE deduplication_key IS NULL
        """
    )
    op.alter_column("alerts", "deduplication_key", nullable=False)
    op.create_index(
        "uq_alerts_active_deduplication",
        "alerts",
        ["monitored_database_id", "deduplication_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'acknowledged')"),
    )


def downgrade() -> None:
    op.drop_index("uq_alerts_active_deduplication", table_name="alerts")
    op.drop_column("alerts", "deduplication_key")
