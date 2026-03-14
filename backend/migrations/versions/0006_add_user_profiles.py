"""Add user_profiles table (TASK-134).

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("analysis_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("top_themes", JSONB(), nullable=True),
        sa.Column("avg_meetings_per_week", sa.Float(), nullable=True),
        sa.Column("preferred_hours", JSONB(), nullable=True),
        sa.Column("decision_speed_avg_days", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("idx_user_profiles_user_id", "user_profiles", ["user_id"])
    op.create_index(
        "idx_user_profiles_user_version",
        "user_profiles",
        ["user_id", "version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_user_profiles_user_version", table_name="user_profiles")
    op.drop_index("idx_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")