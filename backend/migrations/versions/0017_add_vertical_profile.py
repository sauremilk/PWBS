"""Add vertical_profile to users (TASK-154).

Revision ID: 0017
Revises: 0016
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "vertical_profile",
            sa.Text(),
            nullable=False,
            server_default="general",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "vertical_profile")
