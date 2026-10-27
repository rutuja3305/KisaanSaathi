CREATE TABLE IF NOT EXISTS authoritative_document_manifest (
    document_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source_registry(source_id),
    version_id TEXT NOT NULL,
    scheme_id TEXT NOT NULL,
    topic TEXT,
    authority TEXT NOT NULL,
    department TEXT,
    official_url TEXT NOT NULL,
    document_title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    document_number TEXT,
    publication_date TEXT,
    effective_from TEXT,
    effective_until TEXT,
    jurisdiction TEXT NOT NULL,
    authority_tier INTEGER NOT NULL CHECK (authority_tier BETWEEN 1 AND 4),
    validation_status TEXT NOT NULL CHECK (validation_status IN (
        'PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED', 'SUPERSEDED'
    )),
    validated_by TEXT,
    validated_at TEXT,
    rag_allowed INTEGER NOT NULL DEFAULT 0 CHECK (rag_allowed IN (0, 1)),
    structured_db_required INTEGER NOT NULL DEFAULT 0 CHECK (structured_db_required IN (0, 1)),
    local_file TEXT NOT NULL,
    checksum TEXT,
    notes TEXT,
    registered_at TEXT NOT NULL,
    UNIQUE (checksum)
);

CREATE INDEX IF NOT EXISTS idx_authoritative_manifest_source
    ON authoritative_document_manifest (source_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_authoritative_manifest_checksum
    ON authoritative_document_manifest (checksum);
