"""Add organization_id to connections and documents.

Revision ID: 0027_add_org_id_cols
Revises: 0026_add_refresh_tokens
Create Date: 2026-03-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_add_org_id_cols"
down_revision: str = "0026_add_refresh_tokens"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "connections",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "organization_id")
    op.drop_column("connections", "organization_id")
