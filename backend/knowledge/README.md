# Versioned Government Knowledge

The knowledge store separates source identity, retrieved source versions, documents, and chunks. Existing files under `schemes/` are imported as tier-3 `curated_snapshot` records with `validation_status = pending`; they remain available for migration and offline work but are not authoritative retrieval evidence.

## Retrieval contract

`KnowledgeRepository.retrieve_current(scheme_id)` only returns chunks whose source is active and tier 1 or 2, whose version and document are current, whose version is validated, and whose effective period includes the retrieval time. `STALE`, `CHANGE_DETECTED`, and `SUPERSEDED` evidence is excluded. `REVIEW_DUE` evidence may be returned with its freshness status so callers can surface the warning.

When no qualifying evidence remains, the result sets `insufficient_current_evidence = true`. Callers must pass that signal to the response layer and must not infer or invent eligibility rules.

Each result exposes `source`, `authority`, `document`, `version`, `effective_date`, `last_verified_date`, `confidence`, and `freshness_status` through `response_metadata()`.

## Version lifecycle

1. Register the authoritative source and monitoring cadence.
2. Insert a retrieved version with its content hash and validation state. Inserting a new current version supersedes the prior current version for that source.
3. Add the document and chunks, optionally attaching embedding model/version metadata later.
4. Validate source content before changing `validation_status` to `validated`.
5. Re-run retrieval; superseded or stale versions cannot be selected when a current valid version exists.

No crawler is included. A future monitor can populate the same interfaces without changing retrieval behavior.

## Validation report

After creating a SQLite database and importing the legacy files, run:

```powershell
python -m knowledge.report --db path\to\knowledge.sqlite
```

Use `--json` for API-friendly output. Record a manual decision with
`KnowledgeRepository.record_validation(SourceValidation(...))`; a `VERIFIED`
record must include the official URL, validator, and validation timestamp.

## Excel registry import

Install the backend dependencies, then run:

```powershell
cd d:\KisanSathi\backend
python -m knowledge.source_registry_import d:\path\kisaansathi_authoritative_sources.xlsx --db d:\path\knowledge.sqlite
```

The command imports registry metadata only. New rows remain `PENDING`, existing
`VERIFIED` rows cannot be downgraded, and duplicate `source_id` rows in one workbook
are reported and applied only once. It does not read or modify PDF/TXT contents,
create versions, chunk documents, or create embeddings.
