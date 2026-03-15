"""Add sync_runs table (TASK-184).

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str = "0019"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False, comment="pending | running | success | failed"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("errors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Array of {step, message} error objects"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sync_runs_connection", "sync_runs", ["connection_id"])
    op.create_index("idx_sync_runs_status", "sync_runs", ["status"])
    op.create_index("idx_sync_runs_started", "sync_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("idx_sync_runs_started", table_name="sync_runs")
    op.drop_index("idx_sync_runs_status", table_name="sync_runs")
    op.drop_index("idx_sync_runs_connection", table_name="sync_runs")
    op.drop_table("sync_runs")
