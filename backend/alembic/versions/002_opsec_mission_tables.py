"""Add OPSEC events, credentials, mission objectives, C5ISR history, and event store tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-10

These tables support:
- Phase 1: mission_profile column on operations, noise_level on techniques
- Phase 2: c5isr_status_history for time-series, event_store for audit
- Phase 3: opsec_events for OPSEC monitoring, credentials for credential graph
- Phase 4: mission_objectives for objective tracking
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Phase 1: mission_profile on operations --
    op.execute("""
        ALTER TABLE operations
        ADD COLUMN IF NOT EXISTS mission_profile VARCHAR(2) DEFAULT 'SP'
    """)

    # -- Phase 1: noise_level on techniques --
    op.execute("""
        ALTER TABLE techniques
        ADD COLUMN IF NOT EXISTS noise_level VARCHAR(10) DEFAULT 'medium'
    """)

    # -- Phase 2: C5ISR status history for time-series --
    op.execute("""
        CREATE TABLE IF NOT EXISTS c5isr_status_history (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL,
            domain VARCHAR(20) NOT NULL,
            health_pct REAL,
            status VARCHAR(20),
            metrics JSONB,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_c5isr_hist
        ON c5isr_status_history(operation_id, domain, recorded_at)
    """)

    # -- Phase 2: Event store for audit trail --
    op.execute("""
        CREATE TABLE IF NOT EXISTS event_store (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            payload JSONB NOT NULL,
            actor VARCHAR(50) DEFAULT 'system',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_es_op_type
        ON event_store(operation_id, event_type, created_at)
    """)

    # -- Phase 3: OPSEC events --
    op.execute("""
        CREATE TABLE IF NOT EXISTS opsec_events (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) DEFAULT 'warning',
            detail JSONB,
            target_id TEXT,
            technique_id TEXT,
            noise_points INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_opsec_op_time
        ON opsec_events(operation_id, created_at)
    """)

    # -- Phase 3: Credentials --
    op.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL,
            username VARCHAR(255),
            secret_type VARCHAR(50) NOT NULL,
            secret_value TEXT NOT NULL,
            domain VARCHAR(255),
            source_target_id TEXT,
            source_technique_id TEXT,
            valid_until TIMESTAMPTZ,
            tested_targets JSONB DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cred_op
        ON credentials(operation_id)
    """)

    # -- Phase 4: Mission objectives --
    op.execute("""
        CREATE TABLE IF NOT EXISTS mission_objectives (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL,
            objective TEXT NOT NULL,
            category VARCHAR(20) DEFAULT 'tactical',
            priority INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'pending',
            evidence JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            achieved_at TIMESTAMPTZ
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_obj_op
        ON mission_objectives(operation_id, status)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mission_objectives")
    op.execute("DROP TABLE IF EXISTS credentials")
    op.execute("DROP TABLE IF EXISTS opsec_events")
    op.execute("DROP TABLE IF EXISTS event_store")
    op.execute("DROP TABLE IF EXISTS c5isr_status_history")
    op.execute("ALTER TABLE techniques DROP COLUMN IF EXISTS noise_level")
    op.execute("ALTER TABLE operations DROP COLUMN IF EXISTS mission_profile")
