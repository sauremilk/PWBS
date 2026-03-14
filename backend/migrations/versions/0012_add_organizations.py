"""Add organizations and organization_members tables (TASK-144).

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "organization_members",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_org_member"
        ),
    )
    op.create_index(
        "idx_org_members_user", "organization_members", ["user_id"]
    )
    op.create_index(
        "idx_org_members_org_role",
        "organization_members",
        ["organization_id", "role"],
    )


def downgrade() -> None:
    op.drop_index("idx_org_members_org_role", table_name="organization_members")
    op.drop_index("idx_org_members_user", table_name="organization_members")
    op.drop_table("organization_members")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
