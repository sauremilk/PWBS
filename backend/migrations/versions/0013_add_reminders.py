"""Add reminders table (TASK-131).

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("reminder_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column(
            "urgency", sa.Text(), nullable=False, server_default="medium"
        ),
        sa.Column(
            "due_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("responsible_person", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column(
            "resolved_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_reminders_user_status", "reminders", ["user_id", "status"]
    )
    op.create_index(
        "idx_reminders_user_due", "reminders", ["user_id", "due_at"]
    )
    op.create_index(
        "idx_reminders_source_doc", "reminders", ["source_document_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_reminders_source_doc", table_name="reminders")
    op.drop_index("idx_reminders_user_due", table_name="reminders")
    op.drop_index("idx_reminders_user_status", table_name="reminders")
    op.drop_table("reminders")
