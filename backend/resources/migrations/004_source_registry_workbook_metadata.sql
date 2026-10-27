ALTER TABLE source_registry ADD COLUMN topic TEXT;
ALTER TABLE source_registry ADD COLUMN state TEXT;
ALTER TABLE source_registry ADD COLUMN data_type TEXT;
ALTER TABLE source_registry ADD COLUMN manual_verification TEXT NOT NULL DEFAULT 'NO';
ALTER TABLE source_registry ADD COLUMN rag_allowed INTEGER NOT NULL DEFAULT 0 CHECK (rag_allowed IN (0, 1));
ALTER TABLE source_registry ADD COLUMN structured_db_required INTEGER NOT NULL DEFAULT 0 CHECK (structured_db_required IN (0, 1));
ALTER TABLE source_registry ADD COLUMN replacement_required TEXT;
ALTER TABLE source_registry ADD COLUMN notes TEXT;
