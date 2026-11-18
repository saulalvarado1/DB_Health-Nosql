"""Add github issues configuration to monitored databases.

Revision ID: 20261117_0007
Revises: 20261002_0006
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_0007"
down_revision = "20261002_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitored_databases",
        sa.Column(
            "github_issues_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "monitored_databases",
        sa.Column("github_repository", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "monitored_databases",
        sa.Column("github_token_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("monitored_databases", "github_token_encrypted")
    op.drop_column("monitored_databases", "github_repository")
    op.drop_column("monitored_databases", "github_issues_enabled")
