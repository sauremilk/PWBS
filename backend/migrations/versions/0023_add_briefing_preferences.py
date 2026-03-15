"""Add briefing_preferences JSONB column to users (TASK-186).

Revision ID: 0023_add_briefing_preferences
Revises: 0022_add_user_settings_columns
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = "0023_add_briefing_preferences"
down_revision = "0022_add_user_settings_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("briefing_preferences", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "briefing_preferences")
