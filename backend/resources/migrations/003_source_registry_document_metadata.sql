ALTER TABLE source_registry ADD COLUMN department TEXT;
ALTER TABLE source_registry ADD COLUMN document_title TEXT;
ALTER TABLE source_registry ADD COLUMN document_type TEXT;
ALTER TABLE source_registry ADD COLUMN document_number TEXT;
ALTER TABLE source_registry ADD COLUMN publication_date TEXT;
ALTER TABLE source_registry ADD COLUMN effective_from TEXT;
ALTER TABLE source_registry ADD COLUMN effective_until TEXT;
ALTER TABLE source_registry ADD COLUMN dynamic_flag INTEGER NOT NULL DEFAULT 1 CHECK (dynamic_flag IN (0, 1));
ALTER TABLE source_registry ADD COLUMN rag_eligibility TEXT NOT NULL DEFAULT 'NOT_ELIGIBLE'
    CHECK (rag_eligibility IN ('ELIGIBLE', 'NOT_ELIGIBLE', 'REVIEW_REQUIRED'));
ALTER TABLE source_registry ADD COLUMN structured_data_requirement TEXT;
