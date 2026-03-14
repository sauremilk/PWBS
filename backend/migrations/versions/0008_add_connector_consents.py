"""Add connector_consents table (TASK-173).

Revision ID: 0008
Revises: 0007
Create Date: 2025-07-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_consents",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("connector_type", sa.Text(), nullable=False),
        sa.Column("consent_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "connector_type", name="uq_consent_owner_type"),
    )
    op.create_index("idx_consent_owner", "connector_consents", ["owner_id"])


def downgrade() -> None:
    op.drop_index("idx_consent_owner", table_name="connector_consents")
    op.drop_table("connector_consents")
