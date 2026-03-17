"""Add onboarding_step and onboarding_completed_at columns to users table.

Revision ID: 0029_add_onboarding_state
Revises: 0028_sync_orm_to_db
Create Date: 2026-03-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0029_add_onboarding_state"
down_revision: str = "0028_sync_orm_to_db"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding_step")
