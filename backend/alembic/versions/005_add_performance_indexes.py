"""Add performance indexes for facts and technique_executions

Revision ID: 005
Revises: 004
Create Date: 2026-04-26
"""
from alembic import op

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_facts_trait ON facts(trait)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_facts_source_target ON facts(source_target_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_facts_operation_trait ON facts(operation_id, trait)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_te_status ON technique_executions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_te_operation_status ON technique_executions(operation_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_swarm_status ON swarm_tasks(status)")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_facts_trait")
    op.execute("DROP INDEX IF EXISTS idx_facts_category")
    op.execute("DROP INDEX IF EXISTS idx_facts_source_target")
    op.execute("DROP INDEX IF EXISTS idx_facts_operation_trait")
    op.execute("DROP INDEX IF EXISTS idx_te_status")
    op.execute("DROP INDEX IF EXISTS idx_te_operation_status")
    op.execute("DROP INDEX IF EXISTS idx_swarm_status")
