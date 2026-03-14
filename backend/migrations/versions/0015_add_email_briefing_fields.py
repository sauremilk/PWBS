"""Add email briefing fields to users (TASK-177).

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_briefing_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "briefing_email_time",
            sa.Time(),
            nullable=False,
            server_default="06:30:00",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "briefing_email_time")
    op.drop_column("users", "email_briefing_enabled")
