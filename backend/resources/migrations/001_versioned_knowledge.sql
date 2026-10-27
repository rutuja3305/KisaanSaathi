PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_registry (
    source_id TEXT PRIMARY KEY,
    authority TEXT NOT NULL,
    source_name TEXT NOT NULL,
    official_url TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    source_type TEXT NOT NULL,
    authority_tier INTEGER NOT NULL CHECK (authority_tier BETWEEN 1 AND 4),
    monitoring_frequency_days INTEGER NOT NULL CHECK (monitoring_frequency_days > 0),
    last_checked TEXT,
    last_changed TEXT,
    current_version_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE IF NOT EXISTS source_versions (
    version_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source_registry(source_id),
    document_hash TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    published_at TEXT,
    effective_from TEXT,
    effective_until TEXT,
    status TEXT NOT NULL CHECK (status IN ('current', 'superseded', 'withdrawn')),
    change_summary TEXT NOT NULL DEFAULT '',
    validation_status TEXT NOT NULL CHECK (validation_status IN ('pending', 'validated', 'rejected'))
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    document_id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL REFERENCES source_versions(version_id),
    scheme_id TEXT NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    source_authority TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    effective_date TEXT,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('current', 'superseded', 'withdrawn'))
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES knowledge_documents(document_id),
    text TEXT NOT NULL,
    section TEXT,
    page INTEGER,
    metadata TEXT NOT NULL DEFAULT '{}',
    embedding_model TEXT,
    embedding_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_source_versions_current
    ON source_versions (source_id, status, validation_status);
CREATE INDEX IF NOT EXISTS idx_documents_scheme_status
    ON knowledge_documents (scheme_id, status);
CREATE INDEX IF NOT EXISTS idx_chunks_document
    ON knowledge_chunks (document_id);

CREATE TRIGGER IF NOT EXISTS source_version_current_unique
BEFORE UPDATE OF status ON source_versions
WHEN NEW.status = 'current'
BEGIN
    UPDATE source_versions SET status = 'superseded'
    WHERE source_id = NEW.source_id
      AND version_id <> NEW.version_id
      AND status = 'current';
END;
