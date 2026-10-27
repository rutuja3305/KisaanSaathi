import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook

from backend.knowledge.models import SourceRegistry, SourceValidation, SourceVersion
from backend.knowledge.repository import KnowledgeRepository
from backend.knowledge.source_registry_import import SourceRegistryImporter


class SourceRegistryImportTests(unittest.TestCase):
    def setUp(self):
        self.repository = KnowledgeRepository(sqlite3.connect(":memory:"))
        self.repository.migrate()

    def tearDown(self):
        self.repository.close()

    def import_rows(self, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(list(rows[0]))
        for row in rows[1:]:
            sheet.append(list(row))
        handle, filename = tempfile.mkstemp(suffix=".xlsx")
        import os
        os.close(handle)
        path = Path(filename)
        workbook.save(path)
        report = SourceRegistryImporter(self.repository).import_xlsx(path)
        path.unlink()
        return report

    def row(self, source_id="source-1", **overrides):
        values = {
            "source_id": source_id,
            "scheme_id": "pm_kisan",
            "scheme_name": "PM-KISAN",
            "authority": "Government of India",
            "department": "Agriculture Department",
            "official_source_name": "PM-KISAN Portal",
            "official_url": "https://pmkisan.gov.in",
            "jurisdiction": "India",
            "source_type": "official_portal",
            "authority_tier": 1,
            "document_title": "PM-KISAN operational guidelines",
            "document_type": "guideline",
            "document_number": "PMK/2026/01",
            "publication_date": "2026-01-01",
            "effective_from": "2026-01-01",
            "effective_until": "2026-12-31",
            "dynamic_flag": True,
            "rag_eligibility": "REVIEW_REQUIRED",
            "structured_data_requirement": "eligibility rules",
        }
        values.update(overrides)
        return values

    def test_idempotent_import(self):
        values = self.row()
        headers = tuple(values)
        first = self.import_rows([headers, tuple(values.values())])
        second = self.import_rows([headers, tuple(values.values())])

        self.assertEqual(first.new_sources, 1)
        self.assertEqual(second.new_sources, 0)
        self.assertEqual(second.skipped_sources, 1)

    def test_pending_source_remains_non_authoritative(self):
        values = self.row()
        headers = tuple(values)
        self.import_rows([headers, tuple(values.values())])

        row = self.repository.connection.execute(
            "SELECT validation_status, rag_eligibility FROM source_registry WHERE source_id = ?",
            ("source-1",),
        ).fetchone()
        self.assertEqual(row["validation_status"], "PENDING")
        self.assertTrue(self.repository.validation_report()[0]["classification"] != "AUTHORITATIVE_USABLE")

    def test_verified_source_remains_verified(self):
        self.repository.register_source(SourceRegistry(
            source_id="source-1", authority="Government of India", source_name="PM-KISAN",
            official_url="https://pmkisan.gov.in", jurisdiction="India", source_type="official_portal",
            authority_tier=1, monitoring_frequency_days=30, last_checked=None, last_changed=None,
            current_version_id=None, status="active", scheme_id="pm_kisan", scheme_name="PM-KISAN",
            validation_status="VERIFIED", department="Old Department",
        ))
        validation_time = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.repository.record_validation(__import__("backend.knowledge.models", fromlist=["SourceValidation"]).SourceValidation(
            validation_id="validation-1", source_id="source-1", version_id=None, scheme_id="pm_kisan",
            validation_status="VERIFIED", validated_by="reviewer", validation_method="manual",
            validated_at=validation_time, official_source_url="https://pmkisan.gov.in",
            document_reference="PMK/2026/01", validation_notes="Verified manually",
        ))
        values = self.row(department="New Department")
        headers = tuple(values)
        self.import_rows([headers, tuple(values.values())])

        row = self.repository.connection.execute(
            "SELECT validation_status, department FROM source_registry WHERE source_id = ?",
            ("source-1",),
        ).fetchone()
        self.assertEqual(row["validation_status"], "VERIFIED")
        self.assertEqual(row["department"], "New Department")

    def test_existing_validation_history_is_preserved(self):
        self.repository.register_source(SourceRegistry(
            source_id="source-1", authority="Government of India", source_name="PM-KISAN",
            official_url="https://pmkisan.gov.in", jurisdiction="India", source_type="official_portal",
            authority_tier=1, monitoring_frequency_days=30, last_checked=None, last_changed=None,
            current_version_id=None, status="active", scheme_id="pm_kisan", scheme_name="PM-KISAN",
            validation_status="VERIFIED",
        ))
        self.repository.record_validation(SourceValidation(
            validation_id="validation-1", source_id="source-1", version_id=None, scheme_id="pm_kisan",
            validation_status="VERIFIED", validated_by="reviewer", validation_method="manual",
            validated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            official_source_url="https://pmkisan.gov.in", document_reference="PMK/2026/01",
            validation_notes="Verified manually",
        ))
        values = self.row()
        self.import_rows([tuple(values), tuple(values.values())])

        count = self.repository.connection.execute(
            "SELECT COUNT(*) AS count FROM source_validations WHERE source_id = ?",
            ("source-1",),
        ).fetchone()["count"]
        self.assertEqual(count, 1)

    def test_existing_knowledge_versions_are_preserved(self):
        self.repository.register_source(SourceRegistry(
            source_id="source-1", authority="Government of India", source_name="PM-KISAN",
            official_url="https://pmkisan.gov.in", jurisdiction="India", source_type="official_portal",
            authority_tier=1, monitoring_frequency_days=30, last_checked=None, last_changed=None,
            current_version_id=None, status="active", scheme_id="pm_kisan", scheme_name="PM-KISAN",
            validation_status="VERIFIED",
        ))
        self.repository.add_version(SourceVersion(
            version_id="version-1", source_id="source-1", document_hash="hash",
            retrieved_at=datetime(2026, 1, 2, tzinfo=timezone.utc), published_at=None,
            effective_from=None, effective_until=None, status="current",
            change_summary="Existing version", validation_status="validated",
        ))
        values = self.row()
        self.import_rows([tuple(values), tuple(values.values())])

        row = self.repository.connection.execute(
            "SELECT COUNT(*) AS count, current_version_id FROM source_versions JOIN source_registry ON source_registry.source_id = source_versions.source_id WHERE source_versions.source_id = ?",
            ("source-1",),
        ).fetchone()
        self.assertEqual(row["count"], 1)
        self.assertEqual(row["current_version_id"], "version-1")

    def test_missing_metadata_remains_pending(self):
        values = self.row(official_url="", document_number="")
        headers = tuple(values)
        report = self.import_rows([headers, tuple(values.values())])

        self.assertEqual(report.missing_urls, 1)
        self.assertEqual(report.missing_document_references, 1)
        self.assertEqual(report.pending_sources, 1)

    def test_duplicate_source_handling(self):
        first = self.row()
        second = self.row(document_title="A different title")
        headers = tuple(first)
        report = self.import_rows([headers, tuple(first.values()), tuple(second.values())])

        self.assertEqual(report.total_sources, 2)
        self.assertEqual(report.duplicate_sources, 1)
        self.assertEqual(report.new_sources, 1)
        row = self.repository.connection.execute(
            "SELECT document_title FROM source_registry WHERE source_id = ?", ("source-1",)
        ).fetchone()
        self.assertEqual(row["document_title"], "PM-KISAN operational guidelines")


if __name__ == "__main__":
    unittest.main()
