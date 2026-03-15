"""Add timezone, language, briefing_auto_generate, reminder_frequency to users (TASK-183).

Revision ID: 0022_add_user_settings_columns
Revises: 0021_add_search_enhancements
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_add_user_settings_columns"
down_revision = "0021_add_search_enhancements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("timezone", sa.Text(), server_default="Europe/Berlin", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("language", sa.Text(), server_default="de", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("briefing_auto_generate", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("reminder_frequency", sa.Text(), server_default="daily", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "reminder_frequency")
    op.drop_column("users", "briefing_auto_generate")
    op.drop_column("users", "language")
    op.drop_column("users", "timezone")
