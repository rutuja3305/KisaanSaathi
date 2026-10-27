import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.knowledge.document_registry import (
    AUTHORITATIVE_DOCUMENTS_ROOT,
    DuplicateDocumentError,
    DocumentRegistrationError,
    document_registry_report,
    register_document,
    sha256_file,
)
from backend.knowledge.models import SourceRegistry, SourceValidation, SourceVersion
from backend.knowledge.repository import KnowledgeRepository


class AuthoritativeDocumentRegistryTests(unittest.TestCase):
    def setUp(self):
        self.repository = KnowledgeRepository(sqlite3.connect(":memory:"))
        self.repository.migrate()
        self.temp_directory = tempfile.TemporaryDirectory(dir=AUTHORITATIVE_DOCUMENTS_ROOT)
        self.local_file = Path(self.temp_directory.name) / "official-guidance.pdf"
        self.local_file.write_bytes(b"local test document bytes")
        self._register_source()

    def tearDown(self):
        self.repository.close()
        self.temp_directory.cleanup()

    def _register_source(self, *, status="PENDING", rag_allowed=True, current_version_id=None):
        self.repository.register_source(SourceRegistry(
            source_id="test-source",
            authority="Government of India",
            source_name="Test Scheme Source",
            official_url="https://example.gov.in/scheme",
            jurisdiction="India",
            source_type="official_guideline",
            authority_tier=1,
            monitoring_frequency_days=30,
            last_checked=None,
            last_changed=None,
            current_version_id=current_version_id,
            status="active",
            scheme_id="test_scheme",
            scheme_name="Test Scheme",
            official_source_name="Test Scheme Department",
            validation_status=status,
            department="Test Department",
            document_title="Test operational guideline",
            document_type="guideline",
            document_number="GOI/TEST/01",
            rag_allowed=rag_allowed,
            structured_db_required=False,
        ))

    def test_document_registration_records_metadata_and_checksum(self):
        result = register_document(
            self.repository, source_id="test-source", local_file=self.local_file
        )

        self.assertEqual(result["checksum"], sha256_file(self.local_file))
        self.assertEqual(result["validation_status"], "PENDING")
        row = self.repository.connection.execute(
            "SELECT * FROM authoritative_document_manifest WHERE document_id = ?",
            (result["document_id"],),
        ).fetchone()
        self.assertEqual(row["authority"], "Government of India")
        self.assertEqual(row["local_file"].split("/")[-1], "official-guidance.pdf")
        self.assertEqual(row["rag_allowed"], 0)
        self.assertEqual(self.repository.connection.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0], 0)
        self.assertEqual(self.repository.connection.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0], 0)

    def test_missing_source_id_is_rejected(self):
        with self.assertRaisesRegex(DocumentRegistrationError, "Unknown source_id"):
            register_document(
                self.repository, source_id="does-not-exist", local_file=self.local_file
            )

    def test_missing_source_metadata_is_rejected(self):
        self.repository.connection.execute(
            "UPDATE source_registry SET official_url = '' WHERE source_id = 'test-source'"
        )
        with self.assertRaisesRegex(DocumentRegistrationError, "official_url"):
            register_document(
                self.repository, source_id="test-source", local_file=self.local_file
            )

    def test_missing_local_file_is_rejected(self):
        missing_file = AUTHORITATIVE_DOCUMENTS_ROOT / "pm_kisan" / "missing.pdf"
        with self.assertRaisesRegex(DocumentRegistrationError, "does not exist"):
            register_document(
                self.repository, source_id="test-source", local_file=missing_file
            )

    def test_checksum_generation_is_sha256(self):
        checksum = sha256_file(self.local_file)
        self.assertEqual(len(checksum), 64)
        self.assertEqual(checksum, sha256_file(self.local_file))

    def test_duplicate_document_checksum_is_rejected(self):
        register_document(self.repository, source_id="test-source", local_file=self.local_file)
        with self.assertRaises(DuplicateDocumentError):
            register_document(self.repository, source_id="test-source", local_file=self.local_file)

    def test_pending_source_cannot_become_rag_eligible(self):
        result = register_document(
            self.repository, source_id="test-source", local_file=self.local_file
        )
        self.assertEqual(result["validation_status"], "PENDING")
        self.assertFalse(result["rag_allowed"])
        source = self.repository.connection.execute(
            "SELECT validation_status FROM source_registry WHERE source_id = 'test-source'"
        ).fetchone()
        self.assertEqual(source["validation_status"], "PENDING")

    def test_verified_source_can_be_associated_after_existing_validation(self):
        checksum = sha256_file(self.local_file)
        self.repository.add_version(SourceVersion(
            version_id="test-version-1",
            source_id="test-source",
            document_hash=checksum,
            retrieved_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            published_at=None,
            effective_from=None,
            effective_until=None,
            status="current",
            change_summary="Existing source version",
            validation_status="pending",
        ))
        self.repository.record_validation(SourceValidation(
            validation_id="test-validation-1",
            source_id="test-source",
            version_id="test-version-1",
            scheme_id="test_scheme",
            validation_status="VERIFIED",
            validated_by="manual-reviewer",
            validation_method="manual comparison",
            validated_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
            official_source_url="https://example.gov.in/scheme",
            document_reference="GOI/TEST/01",
            validation_notes="Verified through the existing source validation workflow.",
        ))

        result = register_document(
            self.repository, source_id="test-source", local_file=self.local_file
        )

        self.assertEqual(result["validation_status"], "VERIFIED")
        self.assertTrue(result["rag_allowed"])
        self.assertEqual(result["version_id"], "test-version-1")

    def test_legacy_schemes_file_cannot_be_registered_as_authoritative(self):
        legacy_file = Path(__file__).resolve().parents[1] / "backend" / "schemes" / "pm_kisan.txt"
        with self.assertRaisesRegex(DocumentRegistrationError, "must be inside"):
            register_document(
                self.repository, source_id="test-source", local_file=legacy_file
            )

    def test_report_lists_sources_without_documents(self):
        report = document_registry_report(self.repository)
        self.assertEqual(report["totals"]["registered_documents"], 0)
        self.assertEqual(len(report["sources_without_documents"]), 1)


if __name__ == "__main__":
    unittest.main()
