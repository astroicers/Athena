"""Add failure_category column to technique_executions.

Revision ID: 004
Revises: 003
Create Date: 2026-04-09

Adds a structured failure classification column so Orient can reason
about dead attack paths beyond raw error_message strings. Values are
written by ``engine_router._classify_failure`` at every execution path
failure site. See ADR-046 and SPEC-053 for the full value enumeration
and rule #9 pivot semantics.

The column is nullable because:
  - Succeeded executions do not have a failure category
  - Pre-existing failed rows (before this migration) have NULL until
    they age out; Orient renders NULL as "unknown"

A partial index narrows the write path to rows where the classification
is actually present, keeping the index small and query-local.
"""
from alembic import op


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE technique_executions
        ADD COLUMN IF NOT EXISTS failure_category TEXT
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_te_failure_category
        ON technique_executions (operation_id, failure_category)
        WHERE failure_category IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_te_failure_category")
    op.execute(
        "ALTER TABLE technique_executions DROP COLUMN IF EXISTS failure_category"
    )
