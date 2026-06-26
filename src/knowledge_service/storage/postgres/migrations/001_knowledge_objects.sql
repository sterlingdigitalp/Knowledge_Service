-- Migration 001: Knowledge Objects and Source Registry Schema

CREATE TABLE IF NOT EXISTS knowledge_objects (
    id UUID PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    source_url TEXT,
    source_type VARCHAR(50) NOT NULL,
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    markdown TEXT,
    structured_data JSONB,
    raw_content_hash CHAR(64) NOT NULL,
    content_hash CHAR(64) NOT NULL UNIQUE,
    title VARCHAR(500),
    authors TEXT[],
    language VARCHAR(10),
    topics TEXT[],
    word_count INTEGER,
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_count INTEGER NOT NULL,
    citations JSONB,
    acquisition_chain JSONB,
    parent_id UUID,
    chunk_index INTEGER,
    chunk_total INTEGER,
    overlap_with_next_id UUID,
    related_to UUID[],
    relationship_types TEXT[],
    storage_backend VARCHAR(100) NOT NULL,
    index_status VARCHAR(20) NOT NULL,
    retention_policy_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at_storage TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ko_source_id ON knowledge_objects(source_id);
CREATE INDEX IF NOT EXISTS idx_ko_acquired_at ON knowledge_objects(acquired_at);
CREATE INDEX IF NOT EXISTS idx_ko_content_hash ON knowledge_objects(content_hash);
CREATE INDEX IF NOT EXISTS idx_ko_raw_content_hash ON knowledge_objects(raw_content_hash);
CREATE INDEX IF NOT EXISTS idx_ko_parent_id ON knowledge_objects(parent_id);
CREATE INDEX IF NOT EXISTS idx_ko_type ON knowledge_objects(type);

CREATE TABLE IF NOT EXISTS source_registry (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT,
    type VARCHAR(50) NOT NULL,
    owner VARCHAR(255),
    trust_score FLOAT NOT NULL DEFAULT 0.5,
    freshness_score FLOAT NOT NULL DEFAULT 1.0,
    avg_latency_ms INTEGER NOT NULL DEFAULT 0,
    success_rate FLOAT NOT NULL DEFAULT 1.0,
    topics TEXT[],
    cache_policy JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'healthy',
    last_acquired_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source_status ON source_registry(status);
CREATE INDEX IF NOT EXISTS idx_source_topics ON source_registry USING GIN(topics);
