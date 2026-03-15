"""Add referrals table (TASK-180).

Revision ID: 0018
Revises: 0017
Create Date: 2026-03-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referrals",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("referrer_id", sa.Uuid(), nullable=False),
        sa.Column("referee_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "converted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            ["referrer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referee_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_referrals_code"),
        sa.UniqueConstraint("referee_id", name="uq_referrals_referee"),
    )
    op.create_index("idx_referrals_referrer", "referrals", ["referrer_id"])
    op.create_index("idx_referrals_status", "referrals", ["status"])
    op.create_index("idx_referrals_code", "referrals", ["code"])


def downgrade() -> None:
    op.drop_index("idx_referrals_code", table_name="referrals")
    op.drop_index("idx_referrals_status", table_name="referrals")
    op.drop_index("idx_referrals_referrer", table_name="referrals")
    op.drop_table("referrals")
