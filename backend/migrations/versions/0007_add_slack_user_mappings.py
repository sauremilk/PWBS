"""Add slack_user_mappings table (TASK-141).

Revision ID: 0007
Revises: 0006
Create Date: 2025-07-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slack_user_mappings",
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("slack_user_id", sa.String(64), nullable=False),
        sa.Column("slack_workspace_id", sa.String(64), nullable=False),
        sa.Column(
            "pwbs_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_unique_constraint(
        "uq_slack_user_workspace", "slack_user_mappings", ["slack_user_id", "slack_workspace_id"]
    )
    op.create_index("idx_slack_mapping_pwbs_user", "slack_user_mappings", ["pwbs_user_id"])


def downgrade() -> None:
    op.drop_index("idx_slack_mapping_pwbs_user", table_name="slack_user_mappings")
    op.drop_constraint("uq_slack_user_workspace", "slack_user_mappings", type_="unique")
    op.drop_table("slack_user_mappings")
