"""Add deletion_scheduled_at to users table (TASK-105).

Revision ID: 0004
Revises: 0003
Create Date: 2025-07-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "deletion_scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "deletion_scheduled_at")
