"""Add feedbacks table (TASK-188).

Revision ID: 0025
Revises: 0024_email_primary_briefing_channel
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str = "0024_email_brief_channel"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "feedbacks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_type", sa.Text(), nullable=False, comment="bug | feature | praise"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "context_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
            comment="url, browser_info, viewport_size – no sensitive data",
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_feedbacks_user", "feedbacks", ["user_id"])
    op.create_index("idx_feedbacks_type", "feedbacks", ["feedback_type"])
    op.create_index("idx_feedbacks_created", "feedbacks", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_feedbacks_created", table_name="feedbacks")
    op.drop_index("idx_feedbacks_type", table_name="feedbacks")
    op.drop_index("idx_feedbacks_user", table_name="feedbacks")
    op.drop_table("feedbacks")
