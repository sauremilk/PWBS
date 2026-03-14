"""Add briefing_feedback table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "briefing_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column("briefing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["briefing_id"], ["briefings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("briefing_id", "owner_id", name="uq_feedback_briefing_owner"),
    )
    op.create_index("idx_feedback_owner", "briefing_feedback", ["owner_id"])
    op.create_index("idx_feedback_briefing", "briefing_feedback", ["briefing_id"])


def downgrade() -> None:
    op.drop_index("idx_feedback_briefing", table_name="briefing_feedback")
    op.drop_index("idx_feedback_owner", table_name="briefing_feedback")
    op.drop_table("briefing_feedback")
