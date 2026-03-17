"""Add decisions table for decision support (TASK-129).

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("pro_arguments", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("contra_arguments", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("dependencies", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("decided_by", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("neo4j_node_id", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_decisions_user_status", "decisions", ["user_id", "status"])
    op.create_index("idx_decisions_user_decided_at", "decisions", ["user_id", "decided_at"])


def downgrade() -> None:
    op.drop_index("idx_decisions_user_decided_at", table_name="decisions")
    op.drop_index("idx_decisions_user_status", table_name="decisions")
    op.drop_table("decisions")
