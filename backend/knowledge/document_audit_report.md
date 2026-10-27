# KisaanSaathi Document Audit

**Audit date:** 2026-09-28  
**Status:** BLOCKED: requested local corpus was not found

## Scope and Result

Requested corpus: `backend/data/documents/RAG_Knowledge_Base`.

That directory does not exist in the workspace. The `backend/data` directory is also absent. A workspace search found no PDF files and no alternate document corpus was used. Existing files outside the requested path were not treated as audit inputs. Therefore, no file contents, titles, authorities, page counts, currentness, policy claims, or duplicates could be inspected.

The authoritative source workbook was read without modification. It contains 15 unique source IDs. The read-only registry snapshot before and after report generation remained 15 records, all `PENDING`, with 0 `VERIFIED`, 0 source validations, 0 knowledge versions, and 0 chunks.

## Document Summary

| Measure | Count |
|---|---:|
| Total documents inspected | 0 |
| MATCHED | 0 |
| PARTIAL_MATCH | 0 |
| NO_MATCH / UNKNOWN / DERIVED_KISAANSAATHI documents | 0 |
| KEEP_FOR_RAG | 0 |
| REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | 0 |
| MANUAL_VALIDATION_REQUIRED | 0 |
| MOVE_TO_STRUCTURED_DATABASE | 0 |
| KEEP_AS_DERIVED_MODEL_DATA | 0 |
| DO_NOT_USE_FOR_RAG | 0 |
| UNKNOWN_REQUIRES_REVIEW | 0 |
| Registry sources without a suitable local document | 15 |
| Document authority metadata missing | Not assessable; no documents found |
| Document numbers missing | Not assessable; no documents found |
| Document dates missing | Not assessable; no documents found |
| Document official URLs missing | Not assessable; no documents found |
| Potentially outdated documents | Not assessable; no documents found |
| Potential duplicate documents | Not assessable; no documents found |
| Documents with dynamic information | Not assessable; no documents found |
| Documents containing derived/model information | Not assessable; no documents found |

These are document-level counts. Separately, the **source master** has 1 missing official URL, 15 missing document numbers, 13 missing publication dates, and 15 missing effective-from and effective-until dates. All 15 entries have `manual_verification = NO` and `validation_status = PENDING`.

## Document-by-Document Findings

No documents were available at the specified corpus path. Consequently, there are no document rows to assign a document-level mapping status or recommended action. No decision is inferred from filenames or from the source-master descriptions.

## Registry Sources Without Local Documents

Every row below has mapping status `REGISTRY_SOURCE_WITHOUT_DOCUMENT`. `Currentness` and authority confidence for a local document are not assessable. Recommended actions are planning guidance based on the workbook’s own source descriptions, not a judgment about an inspected document.

| SOURCE_ID | TOPIC | DOCUMENT | DOCUMENT MATCH | DOCUMENT AUTHORITY | CURRENTNESS | RECOMMENDED ACTION | MISSING METADATA | REPLACEMENT_REQUIRED |
|---|---|---|---|---|---|---|---|---|
| `pm_kisan_official` | PM-KISAN | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; published/effective dates | YES |
| `pmfby_official` | PMFBY / Crop Insurance | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; effective dates | YES |
| `kcc_rbi_gov` | Kisan Credit Card | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; published/effective dates | YES |
| `namo_shetkari_mahadbt` | Namo Shetkari Mahasanman Nidhi | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; published/effective dates | YES |
| `msp_official` | MSP prices | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | MOVE_TO_STRUCTURED_DATABASE | document number; published/effective dates | YES |
| `rbi_natural_calamity_relief` | Loan restructuring / calamity relief | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; effective dates | YES |
| `maharashtra_drought_relief` | Drought / natural calamity relief | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; published/effective dates | YES |
| `mahadbt_agriculture_schemes` | Agricultural subsidies | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; published/effective dates | YES |
| `official_helplines` | Helpline numbers | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | MOVE_TO_STRUCTURED_DATABASE | document number; published/effective dates | YES |
| `official_application_channels` | Application channels / where to go | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | MOVE_TO_STRUCTURED_DATABASE | document number; published/effective dates | YES |
| `scheme_document_requirements` | Required documents | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | MOVE_TO_STRUCTURED_DATABASE | document number; published/effective dates | YES |
| `crop_risk_reference` | Crop risk profile | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | MOVE_TO_STRUCTURED_DATABASE | document number; published/effective dates | YES |
| `district_risk_reference` | Maharashtra district risk | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | MOVE_TO_STRUCTURED_DATABASE | document number; published/effective dates | YES |
| `kisaansathi_distress_rules` | Distress scenarios | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Registry identifies KisaanSaathi-derived rules | Not assessable | KEEP_AS_DERIVED_MODEL_DATA | official URL; document number; dates | YES |
| `gopinath_munde_official` | Gopinath Munde Shetkari Apghat Suraksha | None | REGISTRY_SOURCE_WITHOUT_DOCUMENT | Not assessable | Not assessable | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT | document number; published/effective dates | YES |

## Structured-Data Candidates

No local data documents were available to inspect. These candidates come from the source-master topics and notes and should be treated as design guidance only.

| Source/topic | Why not primarily RAG | Suggested structured representation | Future backend query |
|---|---|---|---|
| MSP prices | Season/year-specific numeric values need exact lookup and historical comparison. | `msp_prices`: crop, marketing season, year, amount, unit, publication/effective date, source version. | Filter by crop and season/year; return value with source and effective date. |
| Helplines | Exact contacts change and need deterministic lookup plus verification dates. | `official_contacts`: scheme, department, contact type/value, jurisdiction, source/version, last verified. | Filter by scheme, issue, location, and contact type; return current verified entries. |
| Application channels and offices | URLs, offices, and routing can change and misdirect users if stale. | `scheme_channels`: scheme, channel type, URL/address, jurisdiction, source/version, validity period. | Resolve by scheme/service/location and effective date. |
| Required documents | Requirements vary by scheme and applicant conditions. | `scheme_requirements`: scheme, applicant condition, requirement type/value, source/version, validity. | Filter by scheme and applicant facts and return scoped requirements with provenance. |
| Crop/district indicators | Keyed values and model outputs need stable identifiers and must distinguish official data from derived scores. | `agricultural_indicators`: geography/crop/season, value/unit, source/version/date, derived flag/model version. | Query by stable crop/district ID and period; label official observations and model outputs separately. |
| Scheme benefits, eligibility, availability, and application windows | Values can vary by date, season, location, or scheme and need effective-dated checks. | `scheme_terms`: scheme, term type/value/unit, conditions, jurisdiction, source/version, effective interval. | Resolve against scheme, applicant conditions, location, and date. |

## KisaanSaathi-Derived Information

The registry identifies `kisaansathi_distress_rules` as application/model-derived rather than government evidence. It should be stored as versioned rules containing rule ID, model version, inputs, thresholds, outputs, rationale, and source basis. It must not be described as government policy.

The registry also flags crop and district risk references as mixed official-data/model material. Keep government observations separate from KisaanSaathi thresholds, risk scores, and labels; version the model and preserve its input provenance. No such local documents were found to inspect.

## Source-Master Metadata Gaps

| Field | Missing rows |
|---|---:|
| Authority | 0 |
| Department | 0 |
| Official source name | 0 |
| Official URL | 1 (`kisaansathi_distress_rules`) |
| Document title | 0 |
| Document type | 0 |
| Document number | 15 |
| Published date | 13 |
| Effective from | 15 |
| Effective until | 15 |
| Jurisdiction | 0 |
| State | 0 |
| Duplicate source IDs | 0 |

## Most Serious Audit Limitations

1. The requested corpus directory is missing, preventing all file-level authority, currentness, policy, dynamic-data, duplication, and safety checks.
2. All 15 source records remain pending and manually unverified, as expected.
3. The source master has no document numbers for any entry and lacks publication/effective dates for most or all entries.
4. The distress-rules source has no official URL and is explicitly KisaanSaathi-derived; it must not be treated as government evidence.
5. MSP, contacts, application routing, requirements, and crop/district indicators need structured, date-aware representations in addition to or instead of prose retrieval.

## Validation and State Safety

- Registry importer tests: **7 passed**.
- Existing knowledge architecture tests: **8 passed**.
- Python compilation: **passed**.
- Registry snapshot unchanged: 15 sources, 15 `PENDING`, 0 `VERIFIED`.
- Source validation records created: 0.
- Knowledge versions created: 0.
- Chunks or embeddings created: 0.

No PDF was modified or deleted; no document was downloaded; no website was crawled; no extraction, chunking, or embedding occurred; ChromaDB and the frontend were not modified.

**Next prerequisite:** place or restore the corpus at `backend/data/documents/RAG_Knowledge_Base`, then rerun the document audit before making any document suitability or currentness claims.
