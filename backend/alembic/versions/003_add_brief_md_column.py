"""Add brief_md and brief_updated_at columns to operations table.

Revision ID: 003
Revises: 002
Create Date: 2026-04-09

Stores the auto-generated Operation Brief markdown after each OODA cycle.
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE operations
        ADD COLUMN IF NOT EXISTS brief_md TEXT
    """)
    op.execute("""
        ALTER TABLE operations
        ADD COLUMN IF NOT EXISTS brief_updated_at TIMESTAMPTZ
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE operations DROP COLUMN IF EXISTS brief_updated_at")
    op.execute("ALTER TABLE operations DROP COLUMN IF EXISTS brief_md")
