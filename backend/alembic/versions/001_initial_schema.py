"""Initial schema — all 22 tables migrated from SQLite to PostgreSQL.

Revision ID: 001
Revises: None
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- users --
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            callsign TEXT NOT NULL,
            role TEXT DEFAULT 'Commander',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- operations --
    op.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            codename TEXT NOT NULL,
            strategic_intent TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planning',
            current_ooda_phase TEXT NOT NULL DEFAULT 'observe',
            ooda_iteration_count INTEGER DEFAULT 0,
            threat_level REAL DEFAULT 0.0,
            success_rate REAL DEFAULT 0.0,
            techniques_executed INTEGER DEFAULT 0,
            techniques_total INTEGER DEFAULT 0,
            active_agents INTEGER DEFAULT 0,
            data_exfiltrated_bytes INTEGER DEFAULT 0,
            automation_mode TEXT DEFAULT 'semi_auto',
            max_iterations INTEGER DEFAULT 0,
            risk_threshold TEXT DEFAULT 'medium',
            operator_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- targets --
    op.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            hostname TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            os TEXT,
            role TEXT NOT NULL,
            network_segment TEXT DEFAULT '10.0.1.0/24',
            is_compromised BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT FALSE,
            privilege_level TEXT,
            access_status TEXT DEFAULT 'unknown',
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(ip_address, operation_id)
        )
    """)

    # -- agents --
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            paw TEXT NOT NULL,
            host_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'pending',
            privilege TEXT DEFAULT 'User',
            last_beacon TIMESTAMPTZ,
            beacon_interval_sec INTEGER DEFAULT 5,
            platform TEXT DEFAULT 'windows',
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(paw, operation_id)
        )
    """)

    # -- techniques --
    op.execute("""
        CREATE TABLE IF NOT EXISTS techniques (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            mitre_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            tactic TEXT NOT NULL,
            tactic_id TEXT NOT NULL,
            description TEXT,
            kill_chain_stage TEXT DEFAULT 'exploit',
            risk_level TEXT DEFAULT 'medium',
            c2_ability_id TEXT,
            platforms TEXT DEFAULT '["windows"]'
        )
    """)

    # -- technique_executions --
    op.execute("""
        CREATE TABLE IF NOT EXISTS technique_executions (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            technique_id TEXT NOT NULL,
            target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            ooda_iteration_id TEXT,
            engine TEXT DEFAULT 'ssh',
            status TEXT DEFAULT 'queued',
            result_summary TEXT,
            facts_collected_count INTEGER DEFAULT 0,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- facts --
    op.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            trait TEXT NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'host',
            source_technique_id TEXT,
            source_target_id TEXT,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            score INTEGER DEFAULT 1,
            collected_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_dedup ON facts(operation_id, trait, value)")

    # -- ooda_iterations --
    op.execute("""
        CREATE TABLE IF NOT EXISTS ooda_iterations (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            iteration_number INTEGER NOT NULL,
            phase TEXT DEFAULT 'observe',
            observe_summary TEXT,
            orient_summary TEXT,
            decide_summary TEXT,
            act_summary TEXT,
            recommendation_id TEXT,
            technique_execution_id TEXT,
            started_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ
        )
    """)

    # -- ooda_directives --
    op.execute("""
        CREATE TABLE IF NOT EXISTS ooda_directives (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
            directive TEXT NOT NULL,
            scope TEXT DEFAULT 'next_cycle',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            consumed_at TIMESTAMPTZ
        )
    """)

    # -- recommendations --
    op.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            ooda_iteration_id TEXT,
            situation_assessment TEXT NOT NULL,
            recommended_technique_id TEXT NOT NULL,
            confidence REAL NOT NULL,
            options TEXT NOT NULL,
            reasoning_text TEXT NOT NULL,
            accepted BOOLEAN,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- mission_steps --
    op.execute("""
        CREATE TABLE IF NOT EXISTS mission_steps (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            step_number INTEGER NOT NULL,
            technique_id TEXT NOT NULL,
            technique_name TEXT NOT NULL,
            target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            target_label TEXT NOT NULL,
            engine TEXT DEFAULT 'ssh',
            status TEXT DEFAULT 'queued',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
    """)

    # -- c5isr_statuses --
    op.execute("""
        CREATE TABLE IF NOT EXISTS c5isr_statuses (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            domain TEXT NOT NULL,
            status TEXT NOT NULL,
            health_pct REAL DEFAULT 100.0,
            detail TEXT DEFAULT '',
            numerator INTEGER,
            denominator INTEGER,
            metric_label TEXT DEFAULT '',
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(operation_id, domain)
        )
    """)

    # -- log_entries --
    op.execute("""
        CREATE TABLE IF NOT EXISTS log_entries (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            severity TEXT DEFAULT 'info',
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            operation_id TEXT,
            technique_id TEXT,
            target_id TEXT
        )
    """)

    # -- recon_scans --
    op.execute("""
        CREATE TABLE IF NOT EXISTS recon_scans (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            ip_address TEXT,
            status TEXT DEFAULT 'pending',
            nmap_result TEXT,
            open_ports TEXT,
            os_guess TEXT,
            initial_access_method TEXT,
            credential_found TEXT,
            agent_deployed BOOLEAN DEFAULT FALSE,
            facts_written INTEGER DEFAULT 0,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
    """)

    # -- engagements --
    op.execute("""
        CREATE TABLE IF NOT EXISTS engagements (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            client_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            roe_document_path TEXT,
            roe_signed_at TIMESTAMPTZ,
            scope_type TEXT DEFAULT 'whitelist',
            in_scope TEXT NOT NULL DEFAULT '[]',
            out_of_scope TEXT DEFAULT '[]',
            start_time TIMESTAMPTZ,
            end_time TIMESTAMPTZ,
            emergency_contact TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- vuln_cache --
    op.execute("""
        CREATE TABLE IF NOT EXISTS vuln_cache (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            cpe_string TEXT NOT NULL,
            cve_id TEXT NOT NULL,
            cvss_score REAL,
            severity TEXT,
            description TEXT,
            exploit_available BOOLEAN DEFAULT FALSE,
            cached_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(cpe_string, cve_id)
        )
    """)

    # -- technique_playbooks --
    op.execute("""
        CREATE TABLE IF NOT EXISTS technique_playbooks (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            mitre_id TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'linux',
            command TEXT NOT NULL,
            output_parser TEXT,
            facts_traits TEXT NOT NULL DEFAULT '[]',
            source TEXT DEFAULT 'seed',
            tags TEXT DEFAULT '[]',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- tool_registry --
    op.execute("""
        CREATE TABLE IF NOT EXISTS tool_registry (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            tool_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            kind TEXT NOT NULL DEFAULT 'tool',
            category TEXT NOT NULL DEFAULT 'reconnaissance',
            version TEXT,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            source TEXT NOT NULL DEFAULT 'seed',
            config_json TEXT DEFAULT '{}',
            mitre_techniques TEXT DEFAULT '[]',
            risk_level TEXT DEFAULT 'low',
            output_traits TEXT DEFAULT '[]',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- attack_graph_nodes --
    op.execute("""
        CREATE TABLE IF NOT EXISTS attack_graph_nodes (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            technique_id TEXT NOT NULL,
            tactic_id TEXT NOT NULL,
            status TEXT DEFAULT 'unreachable',
            confidence REAL DEFAULT 0.0,
            risk_level TEXT DEFAULT 'medium',
            information_gain REAL DEFAULT 0.0,
            effort INTEGER DEFAULT 1,
            prerequisites TEXT DEFAULT '[]',
            satisfied_prerequisites TEXT DEFAULT '[]',
            source TEXT DEFAULT 'deterministic',
            execution_id TEXT,
            depth INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agn_operation ON attack_graph_nodes(operation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agn_status ON attack_graph_nodes(operation_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agn_technique ON attack_graph_nodes(operation_id, technique_id)")

    # -- attack_graph_edges --
    op.execute("""
        CREATE TABLE IF NOT EXISTS attack_graph_edges (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            source_node_id TEXT REFERENCES attack_graph_nodes(id) ON DELETE CASCADE,
            target_node_id TEXT REFERENCES attack_graph_nodes(id) ON DELETE CASCADE,
            weight REAL DEFAULT 0.0,
            relationship TEXT DEFAULT 'enables',
            required_facts TEXT DEFAULT '[]',
            source_type TEXT DEFAULT 'deterministic',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_age_operation ON attack_graph_edges(operation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_age_source ON attack_graph_edges(source_node_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_age_target ON attack_graph_edges(target_node_id)")

    # -- swarm_tasks --
    op.execute("""
        CREATE TABLE IF NOT EXISTS swarm_tasks (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            ooda_iteration_id TEXT REFERENCES ooda_iterations(id) ON DELETE CASCADE,
            operation_id TEXT REFERENCES operations(id) ON DELETE CASCADE,
            technique_id TEXT NOT NULL,
            target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            engine TEXT DEFAULT 'ssh',
            status TEXT DEFAULT 'pending',
            error TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # -- vulnerabilities --
    op.execute("""
        CREATE TABLE IF NOT EXISTS vulnerabilities (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            operation_id TEXT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
            cve_id TEXT NOT NULL,
            target_id TEXT REFERENCES targets(id) ON DELETE CASCADE,
            severity TEXT NOT NULL DEFAULT 'info',
            status TEXT NOT NULL DEFAULT 'discovered',
            cvss_score REAL DEFAULT 0.0,
            description TEXT,
            source_fact_id TEXT,
            discovered_at TIMESTAMPTZ DEFAULT NOW(),
            confirmed_at TIMESTAMPTZ,
            exploited_at TIMESTAMPTZ,
            reported_at TIMESTAMPTZ,
            UNIQUE(operation_id, cve_id, target_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_vuln_operation ON vulnerabilities(operation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vuln_status ON vulnerabilities(operation_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vuln_cve ON vulnerabilities(cve_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vuln_severity ON vulnerabilities(operation_id, severity)")


def downgrade() -> None:
    tables = [
        "vulnerabilities", "swarm_tasks", "attack_graph_edges", "attack_graph_nodes",
        "tool_registry", "technique_playbooks", "vuln_cache", "engagements",
        "recon_scans", "log_entries", "c5isr_statuses", "mission_steps",
        "recommendations", "ooda_directives", "ooda_iterations", "facts",
        "technique_executions", "techniques", "agents", "targets",
        "operations", "users",
    ]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
