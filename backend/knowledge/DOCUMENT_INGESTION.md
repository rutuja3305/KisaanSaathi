# Page-Aware Document Ingestion (Phase 1)

This phase discovers PDFs only under `backend/knowledge/authoritative_documents/` and extracts text independently per page. It creates JSON intermediate records under `backend/knowledge/ingestion_output/`; it does not create source versions, knowledge documents, chunks, embeddings, or vectors.

The legacy summaries under `backend/schemes/` are never scanned. Empty topic folders are ignored. Folder-to-source mapping uses the existing source registry IDs and the topic folder mapping in `document_ingestion.py`; an unmapped folder is reported as `UNMAPPED` and is not assigned a guessed source ID.

Each extracted document JSON contains the source ID, stable document ID derived from source ID and SHA-256, absolute and relative source path, filename, file type, source checksum, PDF metadata/title, source registry metadata, extraction timestamp/status, and page records. Every page has a one-based page number, text, `has_text`, page extraction status, headings/section hints, numbered-section markers, list boundaries, and conservative table candidates. Empty and failed pages remain in the output.

Outputs are named with a checksum suffix. The command creates output files exclusively and never overwrites them. Re-running ingestion against an identical source reports an unchanged existing output. If an output with the same name has inconsistent provenance, the command reports a conflict and leaves it untouched.

## Commands

From `backend`:

```powershell
python -m pip install -r requirements.txt
python -m knowledge.document_ingestion scan --db knowledge\knowledge.sqlite
python -m knowledge.document_ingestion ingest --db knowledge\knowledge.sqlite
```

`scan` is read-only: it reports discovered PDFs, checksums, PDF signatures, and source mappings without extracting pages or writing output. `ingest` creates the intermediate JSON records. Both commands open the source registry SQLite file in read-only mode.

Optional paths:

```powershell
python -m knowledge.document_ingestion scan `
  --db knowledge\knowledge.sqlite `
  --documents-root knowledge\authoritative_documents `
  --output-dir knowledge\ingestion_output
```

PDF extraction uses `pypdf` one page at a time. It performs lightweight line-based structure detection only; it does not semantically segment/chunk document text.

## Phase 2: hierarchical semantic chunking

Phase 2 consumes the page-aware JSON files under `ingestion_output/`, not the PDFs directly. It verifies each extraction's source ID against `source_registry`, its original PDF path is under `authoritative_documents/`, and its SHA-256 still matches the PDF before producing chunks. Sentence segmentation uses `pysbd`; paragraph and heading boundaries are preserved. Neighboring sentence groups use deterministic TF-IDF cosine similarity (no model embeddings) to offer semantic boundary signals.

The single `ChunkingConfig` in `knowledge/chunking.py` controls the initial targets: 400 target/600 max child tokens, 1 sentence of overlap, 1250 target/1500 max parent tokens, and a 0.12 TF-IDF similarity threshold. Parent and child chunks are stored separately in `chunking_runs` and `hierarchical_chunks`; checksum + chunking version + configuration hash identify a run, so a changed PDF/configuration creates a new historical run without deleting old data. Each chunk snapshots the source validation status as provenance; chunking never changes it.

Run chunk generation and inspect quality:

```powershell
python -m knowledge.chunking run --db knowledge\knowledge.sqlite
python -m knowledge.chunking run --db knowledge\knowledge.sqlite --source-id pm_kisan_official --debug
python -m knowledge.chunking report --db knowledge\knowledge.sqlite
python -m knowledge.chunking report --db knowledge\knowledge.sqlite --debug
```

This phase does not create embeddings, vectors, retrieval, reranking, or LLM answers. It writes only the separate hierarchical chunk tables.

## Registered-manifest extraction

`document_extraction` is the stricter production extraction entry point. Unlike the initial staging scan above, it selects only rows already present in `authoritative_document_manifest`. For each row it requires a local file under `authoritative_documents/`, a non-empty manifest checksum matching the current file, and a valid PDF signature before extracting. A checksum mismatch is reported as a failure and produces no extraction output for that record.

The output is a JSON sidecar under `backend/knowledge/extraction_output/`, separate from the source manifest and from `knowledge_documents`. Each page retains source/document/file/checksum provenance, one-based page number, text, paragraph boundaries, heading/section hints, character count, and extraction status. Scanned/image-only files are marked `OCR_REQUIRED`; OCR is not attempted. `GOOD`, `LOW_TEXT`, `OCR_REQUIRED`, and `FAILED` are extraction-quality labels only and never alter RAG eligibility or source validation.

Commands from `backend`:

```powershell
python -m knowledge.document_extraction extract --db knowledge\knowledge.sqlite --source-id <source_id>
python -m knowledge.document_extraction extract-all --db knowledge\knowledge.sqlite
python -m knowledge.document_extraction extract-all --db knowledge\knowledge.sqlite --dry-run
```

The SQLite connection is read-only. Extraction creates no versions, validation records, manifest entries, knowledge documents, chunks, embeddings, or vectors. Existing JSON output is never overwritten; a matching source/document/checksum output is reported as skipped, while conflicting provenance is reported without replacement.
