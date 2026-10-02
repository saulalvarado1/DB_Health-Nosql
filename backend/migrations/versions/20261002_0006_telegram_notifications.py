"""Add telegram notifications configuration to monitored databases.

Revision ID: 20261002_0006
Revises: 20260922_0005
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import op

revision = "20261002_0006"
down_revision = "20260922_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitored_databases",
        sa.Column(
            "telegram_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "monitored_databases",
        sa.Column("telegram_chat_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "monitored_databases",
        sa.Column("telegram_bot_token_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "monitored_databases",
        sa.Column(
            "notify_on_warning",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "monitored_databases",
        sa.Column(
            "notify_on_critical",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "monitored_databases",
        sa.Column(
            "notify_on_recovery",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("monitored_databases", "notify_on_recovery")
    op.drop_column("monitored_databases", "notify_on_critical")
    op.drop_column("monitored_databases", "notify_on_warning")
    op.drop_column("monitored_databases", "telegram_bot_token_encrypted")
    op.drop_column("monitored_databases", "telegram_chat_id")
    op.drop_column("monitored_databases", "telegram_notifications_enabled")
