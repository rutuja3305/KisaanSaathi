# Authoritative Document Staging

This directory is the local staging area for manually researched official documents. Topic folders are provided for:

`pm_kisan`, `pmfby`, `kcc`, `loan_restructuring`, `namo_shetkari`, `drought_relief`, `mahadbt_agriculture`, `msp`, `helplines`, `application_channels`, `crop_risk`, `district_risk`, and `scheme_document_requirements`.

## Separate the legacy material

- `backend/schemes` contains legacy/reference/derived KisaanSaathi summaries. They are not authoritative government evidence and must not be registered as official documents.
- `backend/knowledge/authoritative_documents` is only for manually researched official material. A file's presence here does not prove that it is official, current, validated, or RAG-eligible.
- No document becomes RAG-eligible merely because it exists in this directory or is registered in its manifest.

Every registration requires an existing source registry entry, minimum source metadata, a local file within this directory, and a SHA-256 checksum. It creates only an `authoritative_document_manifest` record; it does not create a source version, extract text, chunk, embed, or write to ChromaDB. Duplicate file checksums are rejected.

A document starts `PENDING` and `rag_allowed = false`. Registration never changes source validation state and never creates validation records. Validation must be performed explicitly through the existing source registry/version validation workflow. The registration command will only associate a document with existing verification when the current validated source version's document hash exactly matches the local file checksum. The registry's `rag_allowed` setting must also be enabled before that matched document can be marked RAG-allowed.

## Commands

From `backend`:

```powershell
python -m knowledge.document_registry register `
  --db knowledge\knowledge.sqlite `
  --source-id <source_id> `
  --file knowledge\authoritative_documents\<topic>\<local-file>
```

Show manifest and source coverage:

```powershell
python -m knowledge.document_registry report --db knowledge\knowledge.sqlite
```

The report includes registered documents, pending/unvalidated documents, checksum gaps, sources without local documents, verified sources without local documents, and duplicate checksums. The legacy summaries under `backend/schemes` are deliberately outside the permitted registration root.
