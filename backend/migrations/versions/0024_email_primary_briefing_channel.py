"""Email as primary briefing channel (ADR-019).

- Change email_briefing_enabled default to True for new users
- Update existing users to opt-in (email_briefing_enabled = True)
- Add email_sent_at to briefings table for idempotency guard

Revision ID: 0024_email_brief_channel
Revises: 0023_add_briefing_preferences
Create Date: 2026-03-16
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0024_email_brief_channel"
down_revision = "0023_add_briefing_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # L1: Change default for new users from False to True
    op.alter_column(
        "users",
        "email_briefing_enabled",
        server_default="true",
    )
    # Opt-in existing users (they can opt-out via settings)
    op.execute(
        "UPDATE users SET email_briefing_enabled = true WHERE email_briefing_enabled = false"
    )

    # Idempotency guard: track when briefing email was sent
    op.add_column(
        "briefings",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("briefings", "email_sent_at")
    op.alter_column(
        "users",
        "email_briefing_enabled",
        server_default="false",
    )
