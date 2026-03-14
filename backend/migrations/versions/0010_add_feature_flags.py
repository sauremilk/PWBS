"""Add feature_flags table and users.is_admin column.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("flag_name", sa.Text(), nullable=False),
        sa.Column("enabled_globally", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "enabled_for_users",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag_name"),
    )
    op.create_index("ix_feature_flags_flag_name", "feature_flags", ["flag_name"])
    op.add_column(
        "users", sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
    op.drop_index("ix_feature_flags_flag_name", table_name="feature_flags")
    op.drop_table("feature_flags")
