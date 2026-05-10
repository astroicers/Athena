-- Athena 2.0 initial schema

CREATE TABLE IF NOT EXISTS operations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'planning',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS targets (
    id UUID PRIMARY KEY,
    operation_id UUID REFERENCES operations(id),
    hostname TEXT,
    ip TEXT,
    os TEXT,
    tags JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_id UUID REFERENCES operations(id),
    trait_name TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence SMALLINT NOT NULL DEFAULT 50,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(operation_id, trait_name, fact_value)
);

CREATE TABLE IF NOT EXISTS ooda_iterations (
    id UUID PRIMARY KEY,
    operation_id UUID REFERENCES operations(id),
    state TEXT NOT NULL DEFAULT 'idle',
    iteration_count INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_facts_op ON facts(operation_id);
CREATE INDEX idx_facts_trait ON facts(operation_id, trait_name);
