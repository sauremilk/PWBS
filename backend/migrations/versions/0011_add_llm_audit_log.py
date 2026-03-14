"""Add llm_audit_log table.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column(
            "owner_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("purpose", sa.Text(), server_default="general", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_audit_log_owner_id", "llm_audit_log", ["owner_id"])
    op.create_index(
        "ix_llm_audit_log_owner_created",
        "llm_audit_log",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_audit_log_owner_created", table_name="llm_audit_log")
    op.drop_index("ix_llm_audit_log_owner_id", table_name="llm_audit_log")
    op.drop_table("llm_audit_log")
