# KisaanSaathi Local Document Location Report

**Search root:** `D:\KisanSathi`  
**Search extensions:** PDF, DOC, DOCX, TXT  
**Excluded from traversal:** `venv`, `.git`, `node_modules`, `dist`, `build`, `__pycache__`  
**Audit date:** 2026-09-28

## Located Corpus

**Likely existing KisaanSaathi topic corpus:** `D:\KisanSathi\backend\schemes`

It contains 14 topic-named text files totaling 69,534 bytes. The filenames and headings closely cover 14 of the 15 registry source topics. The contents are locally compiled farmer-facing summaries with `SOURCE`, `LAST VERIFIED: June 2025`, and `VERSION` labels. They cite official portals and agencies but are not identifiable as original government-issued documents: no issuing authority, publication/effective date, or official document number is stated in the files.

The previously named `backend/data/documents/RAG_Knowledge_Base` directory does not exist. No PDF, DOC, or DOCX files were found anywhere under the requested search root.

## Candidate Directory Counts

| Directory | Files | PDF | DOC/DOCX | TXT | Total size | Assessment |
|---|---:|---:|---:|---:|---:|---|
| `backend` | 1 | 0 | 0 | 1 | 114 bytes | Dependency manifest only; not a corpus |
| `backend/schemes` | 14 | 0 | 0 | 14 | 69,534 bytes | Likely KisaanSaathi topic corpus; compiled summaries, not source documents |

`backend/requirements.txt` is the one TXT file outside the likely corpus and is not knowledge content.

## Document Mapping

Confidence is confidence in the topic/source-ID match, not confidence that the document is official or current. A `PARTIAL_MATCH` means the topic aligns but the TXT is a compiled summary rather than the authoritative document. The distress file is separately marked derived.

| Filename | Directory | Possible source ID | Topic | Mapping | Confidence |
|---|---|---|---|---|---:|
| `crop_risk_profile.txt` | `backend/schemes` | `crop_risk_reference` | Crop risk profile | PARTIAL_MATCH | 0.94 |
| `distress_scenarios.txt` | `backend/schemes` | `kisaansathi_distress_rules` | Distress scenarios | DERIVED_KISAANSAATHI | 0.98 |
| `documents_checklist.txt` | `backend/schemes` | `scheme_document_requirements` | Required documents | PARTIAL_MATCH | 0.97 |
| `drought_relief.txt` | `backend/schemes` | `maharashtra_drought_relief` | Drought / natural calamity relief | PARTIAL_MATCH | 0.96 |
| `gopinath_munde.txt` | `backend/schemes` | `gopinath_munde_official` | Gopinath Munde farmer accident insurance | PARTIAL_MATCH | 0.98 |
| `helpline_numbers.txt` | `backend/schemes` | `official_helplines` | Helpline numbers | PARTIAL_MATCH | 0.99 |
| `kcc.txt` | `backend/schemes` | `kcc_rbi_gov` | Kisan Credit Card | PARTIAL_MATCH | 0.99 |
| `loan_restructuring.txt` | `backend/schemes` | `rbi_natural_calamity_relief` | Loan restructuring / calamity relief | PARTIAL_MATCH | 0.91 |
| `maharashtra_districts_risk.txt` | `backend/schemes` | `district_risk_reference` | Maharashtra district risk | PARTIAL_MATCH | 0.98 |
| `msp_prices.txt` | `backend/schemes` | `msp_official` | MSP prices | PARTIAL_MATCH | 0.99 |
| `namo_shetkari.txt` | `backend/schemes` | `namo_shetkari_mahadbt` | Namo Shetkari | PARTIAL_MATCH | 0.99 |
| `pm_kisan.txt` | `backend/schemes` | `pm_kisan_official` | PM-KISAN | PARTIAL_MATCH | 0.99 |
| `pmfby.txt` | `backend/schemes` | `pmfby_official` | PMFBY / crop insurance | PARTIAL_MATCH | 0.99 |
| `where_to_go.txt` | `backend/schemes` | `official_application_channels` | Where to go / application channels | PARTIAL_MATCH | 0.96 |

**Unmapped document:** `backend/requirements.txt` is a dependency manifest, not knowledge content.  
**Registry source without a local topic document:** `mahadbt_agriculture_schemes` (Agricultural subsidies).

## Light Content Findings

All 14 TXT files identify a title and claim last verification in June 2025. Their version labels refer to 2025 or the 2025-26 seasons. These are approximate self-reported content dates, not publication or effective dates. As of 2026-09-28, currentness is not established and the seasonal references are stale for present-season advice.

| Filename | Detected source/authority references | Document number / publication / effective date | Government material? | Dynamic or policy flags | Recommended action |
|---|---|---|---|---|---|
| `crop_risk_profile.txt` | Compiled from agricoop.nic.in, dfpd.gov.in and Maharashtra Agriculture Department | None / none / none | Not an original official document identified | Input costs, MSP and enrollment dates marked VERIFY; derived crop risk levels | KEEP_AS_DERIVED_MODEL_DATA |
| `distress_scenarios.txt` | Compiled from PM-KISAN, PMFBY, KCC and Maharashtra guidelines | None / none / none | No; scenario/action-plan content | Risk levels, relief amounts and past 2025 deadlines; VERIFY claims | KEEP_AS_DERIVED_MODEL_DATA |
| `documents_checklist.txt` | Compiled from PM-KISAN, PMFBY, NABARD and Maharashtra references | None / none / none | No; compiled checklist | Requirements vary by scheme; at least one entry marked VERIFY | MOVE_TO_STRUCTURED_DATABASE |
| `drought_relief.txt` | Maharashtra disaster-management and agriculture URLs | None / none / none | No GR/notification number identified | Event declarations, thresholds, compensation amounts and timelines; VERIFY claims | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `gopinath_munde.txt` | Maharashtra Agriculture portal | None / none / none | No specific government order identified | Benefit, age eligibility and claim deadline marked VERIFY | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `helpline_numbers.txt` | Compiled from official portals/sites | None / none / none | No; compiled contact list | Phone numbers, service hours and portals marked VERIFY | MOVE_TO_STRUCTURED_DATABASE |
| `kcc.txt` | NABARD and RBI | None / none / none | No current circular identified | Interest/subvention, limits, insurance and relief marked VERIFY | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `loan_restructuring.txt` | RBI Master Circular mentioned without identifier | None / none / none | No; summary of purported rules | Crop-loss threshold, automatic moratorium, response times and 2017 waiver claims; VERIFY | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `maharashtra_districts_risk.txt` | Maharashtra disaster-management and Agriculture Department references | None / none / none | Not an official district risk classification identified | Risk zones, rainfall and historic frequency marked VERIFY; derived labels | KEEP_AS_DERIVED_MODEL_DATA |
| `msp_prices.txt` | DFPD, Agriculture Department and CACP references | None / none / none | No announcement/document ID identified | Kharif 2025 numeric prices marked VERIFY; historical seasonal data | MOVE_TO_STRUCTURED_DATABASE |
| `namo_shetkari.txt` | MahaDBT portal | None / none / none | No GR/order identified | Amounts, installments and eligibility marked VERIFY | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `pm_kisan.txt` | PM-KISAN portal | None / none / none | No current circular/guideline ID identified | Amount, eligibility, exclusions and installments marked VERIFY | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `pmfby.txt` | PMFBY portal | None / none / none | No current guideline/notification ID identified | Premiums, notified crops and seasonal deadlines marked VERIFY | REPLACE_WITH_CURRENT_OFFICIAL_DOCUMENT |
| `where_to_go.txt` | Compiled from Maharashtra office hierarchy and scheme guidelines | None / none / none | No; no specific office-directory sources identified | Locations, charges and response times marked VERIFY | MOVE_TO_STRUCTURED_DATABASE |

The detailed inventory fields, sizes, source URL strings, currentness, mapping, and reasons are in [document_location_report.json](document_location_report.json).

## Derived and Structured Candidates

- `distress_scenarios.txt`: risk levels, scenario thresholds and recommendation logic. Treat as versioned KisaanSaathi model rules, not government policy.
- `crop_risk_profile.txt`: separate official crop facts from derived input-cost estimates, risk scores and thresholds.
- `maharashtra_districts_risk.txt`: do not present “HIGH RISK ZONE” labels as government classifications; retain model outputs separately from official indicators.
- `msp_prices.txt`: structured crop/season/year/amount/unit/source records.
- `helpline_numbers.txt`: structured contacts with jurisdiction, originating source URL and last verified date.
- `where_to_go.txt`: structured scheme/service channels, URLs, offices, locations, validity dates and source versions.
- `documents_checklist.txt`: structured requirements keyed by scheme and applicant condition.
- PM-KISAN, PMFBY, KCC, Namo Shetkari, drought relief and accident insurance: dynamic terms such as benefit amounts, eligibility, scheme availability and application windows need effective-dated records and current provenance.

The JSON report gives suggested table shapes and future backend lookup patterns for these candidates.

## Outdated, Unsafe, and Overlapping Claims

Several files contain explicit `[VERIFY]` markers. Notable examples include:

- PM-KISAN amounts, exclusions and installment timing.
- PMFBY premium percentages and 2025 enrollment deadlines; crop/district notifications vary by season.
- KCC interest/subvention and credit limits.
- Namo Shetkari amount, combined benefit and eligibility assumptions.
- Drought compensation amounts, crop-loss thresholds and relief timelines.
- Loan restructuring threshold, automatic moratorium, bank response times and historic loan-waiver statements.
- Gopinath Munde benefit amounts, age range and reporting deadline.
- Helpline numbers and service hours.
- MSP values explicitly labeled Kharif 2025.
- District risk labels, rainfall and historical claims, with old district names appearing.
- Office response times and service charges.

Potential topic overlap (not confirmed duplicate files): distress scenarios overlap PM-KISAN/PMFBY/KCC guidance; crop and district risk files overlap risk claims; PM-KISAN and Namo content recur in distress advice. No exact duplicate was established by the light inspection.

## Recommended Next Action

Use `D:\KisanSathi\backend\schemes` as the located legacy KisaanSaathi topic corpus, **not** as an authoritative government-document corpus. Keep source registry records pending. Manually locate and validate current official source documents with document numbers and effective dates. Keep dynamic numeric data in structured tables and version derived model logic separately. Do not treat these summaries as authoritative RAG evidence without that work.

## Safety Check

- No files were modified, moved, renamed, or deleted except creation of the two requested report files.
- No documents were downloaded and no websites were accessed.
- No validation records or source versions were created; no source was marked VERIFIED.
- No chunks or embeddings were created.
- ChromaDB and the frontend were not modified.
