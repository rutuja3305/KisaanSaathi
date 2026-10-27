ALTER TABLE source_registry ADD COLUMN scheme_id TEXT;
ALTER TABLE source_registry ADD COLUMN scheme_name TEXT;
ALTER TABLE source_registry ADD COLUMN official_source_name TEXT;
ALTER TABLE source_registry ADD COLUMN validation_status TEXT NOT NULL DEFAULT 'PENDING'
    CHECK (validation_status IN ('PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED', 'SUPERSEDED'));
ALTER TABLE source_registry ADD COLUMN monitoring_frequency TEXT;

CREATE TABLE IF NOT EXISTS source_validations (
    validation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source_registry(source_id),
    version_id TEXT REFERENCES source_versions(version_id),
    scheme_id TEXT NOT NULL,
    validation_status TEXT NOT NULL CHECK (validation_status IN (
        'PENDING', 'VERIFIED', 'REVIEW_REQUIRED', 'REJECTED', 'SUPERSEDED'
    )),
    validated_by TEXT,
    validation_method TEXT,
    validated_at TEXT,
    official_source_url TEXT,
    document_reference TEXT,
    validation_notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_source_registry_scheme
    ON source_registry (scheme_id, validation_status);
CREATE INDEX IF NOT EXISTS idx_source_validations_source_version
    ON source_validations (source_id, version_id, validated_at);
