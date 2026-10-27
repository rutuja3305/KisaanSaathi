CREATE TABLE IF NOT EXISTS chunking_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES source_registry(source_id),
    document_id TEXT NOT NULL,
    document_checksum TEXT NOT NULL,
    chunking_version TEXT NOT NULL,
    configuration_hash TEXT NOT NULL,
    configuration_json TEXT NOT NULL,
    input_extraction_path TEXT NOT NULL,
    source_validation_status TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('COMPLETED', 'FAILED')),
    parent_chunk_count INTEGER NOT NULL DEFAULT 0,
    child_chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE (source_id, document_id, document_checksum, chunking_version, configuration_hash)
);

CREATE TABLE IF NOT EXISTS hierarchical_chunks (
    chunk_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES chunking_runs(run_id),
    chunk_type TEXT NOT NULL CHECK (chunk_type IN ('PARENT', 'CHILD')),
    parent_chunk_id TEXT REFERENCES hierarchical_chunks(chunk_id),
    source_id TEXT NOT NULL REFERENCES source_registry(source_id),
    document_id TEXT NOT NULL,
    document_checksum TEXT NOT NULL,
    source_validation_status TEXT NOT NULL,
    page_start INTEGER NOT NULL CHECK (page_start > 0),
    page_end INTEGER NOT NULL CHECK (page_end >= page_start),
    section_heading TEXT,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    text TEXT NOT NULL,
    sentence_start INTEGER NOT NULL CHECK (sentence_start > 0),
    sentence_end INTEGER NOT NULL CHECK (sentence_end >= sentence_start),
    token_count INTEGER NOT NULL CHECK (token_count >= 0),
    overlap_sentence_count INTEGER NOT NULL DEFAULT 0 CHECK (overlap_sentence_count >= 0),
    overlap_metadata TEXT NOT NULL DEFAULT '{}',
    boundary_reason TEXT,
    chunking_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE (run_id, chunk_type, chunk_index),
    CHECK ((chunk_type = 'PARENT' AND parent_chunk_id IS NULL) OR
           (chunk_type = 'CHILD' AND parent_chunk_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_chunking_runs_document
    ON chunking_runs (source_id, document_id, document_checksum, chunking_version);
CREATE INDEX IF NOT EXISTS idx_hierarchical_chunks_parent
    ON hierarchical_chunks (parent_chunk_id, chunk_type);
CREATE INDEX IF NOT EXISTS idx_hierarchical_chunks_provenance
    ON hierarchical_chunks (source_id, document_id, page_start, page_end);
