import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.knowledge.document_extraction import (
    ChecksumMismatchError,
    DocumentExtractionService,
    ManifestDocumentStore,
)
from backend.knowledge.models import SourceRegistry
from backend.knowledge.repository import KnowledgeRepository


class FakePage:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error

    def extract_text(self, extraction_mode="layout"):
        if self.error:
            raise self.error
        return self.text


class FakeReader:
    pages = []
    metadata = {}
    error = None

    def __init__(self, path, strict=False):
        if self.error:
            raise self.error
        self.pages = type(self).pages
        self.metadata = type(self).metadata
        self.is_encrypted = False


class DocumentExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.authoritative = self.base / "authoritative_documents"
        self.folder = self.authoritative / "pm_kisan"
        self.folder.mkdir(parents=True)
        self.output = self.base / "extraction_output"
        self.db_path = self.base / "knowledge.sqlite"
        self.connection = sqlite3.connect(self.db_path)
        self.repository = KnowledgeRepository(self.connection)
        self.repository.migrate()
        self.repository.register_source(SourceRegistry(
            source_id="pm_kisan_official",
            authority="Government of India",
            source_name="PM-KISAN",
            official_url="https://pmkisan.gov.in/",
            jurisdiction="India",
            source_type="official_document",
            authority_tier=1,
            monitoring_frequency_days=30,
            last_checked=None,
            last_changed=None,
            current_version_id=None,
            status="active",
            scheme_id="pm_kisan",
            validation_status="PENDING",
            document_title="PM-KISAN Revised FAQ",
            document_type="FAQ",
            rag_allowed=False,
        ))
        FakeReader.pages = []
        FakeReader.metadata = {}
        FakeReader.error = None
        self.service = DocumentExtractionService(
            database_path=self.db_path,
            output_root=self.output,
            authoritative_root=self.authoritative,
            reader_factory=FakeReader,
        )

    def tearDown(self):
        self.service.close()
        self.repository.close()
        self.temp.cleanup()

    def make_pdf(self, name="sample.pdf", contents=b"%PDF-1.7 synthetic test file"):
        path = self.folder / name
        path.write_bytes(contents)
        return path

    def register_manifest(self, path, *, checksum=None, source_id="pm_kisan_official", document_id="manifest-doc-1"):
        digest = checksum or hashlib.sha256(path.read_bytes()).hexdigest()
        self.connection.execute(
            """INSERT INTO authoritative_document_manifest
            (document_id, source_id, version_id, scheme_id, topic, authority, department,
             official_url, document_title, document_type, document_number, publication_date,
             effective_from, effective_until, jurisdiction, authority_tier, validation_status,
             validated_by, validated_at, rag_allowed, structured_db_required, local_file,
             checksum, notes, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (document_id, source_id, "local-test-version", "pm_kisan", "PM-KISAN",
             "Government of India", "Department of Agriculture & Farmers Welfare",
             "https://pmkisan.gov.in/", "PM-KISAN Revised FAQ", "FAQ", None,
             None, None, None, "India", 1, "PENDING", None, None, 0, 0,
             str(path.resolve()), digest, "test fixture", "2026-09-28T00:00:00+00:00"),
        )
        self.connection.commit()
        return digest

    def test_valid_registered_pdf_extraction_and_metadata(self):
        path = self.make_pdf()
        digest = self.register_manifest(path)
        FakeReader.pages = [FakePage("""PM-KISAN FREQUENTLY ASKED QUESTIONS

1. Scheme purpose

    PM-KISAN supports eligible farmer families. This paragraph describes the source-backed assistance scheme for agricultural households and includes enough readable sample text to pass the document quality threshold without representing actual policy claims. Extraction preserves the page boundary, its paragraphs, and its provenance metadata.""")]
        FakeReader.metadata = {"/Title": "PM-KISAN FAQ"}

        report = self.service.extract_all()
        record = report.documents[0]

        self.assertEqual(report.documents_extracted, 1)
        self.assertEqual(record["extraction_status"], "SUCCESS")
        self.assertEqual(record["quality_status"], "GOOD")
        self.assertEqual(record["sha256"], digest)
        self.assertEqual(record["title"], "PM-KISAN FAQ")
        self.assertEqual(record["pages"][0]["page_number"], 1)
        self.assertEqual(record["pages"][0]["source_id"], "pm_kisan_official")
        self.assertEqual(record["pages"][0]["document_id"], "manifest-doc-1")
        self.assertEqual(record["pages"][0]["filename"], path.name)
        self.assertGreater(record["pages"][0]["character_count"], 0)
        self.assertTrue(Path(record["intermediate_output_path"]).is_file())

    def test_page_number_preservation(self):
        path = self.make_pdf()
        self.register_manifest(path)
        FakeReader.pages = [FakePage("Page one has readable text."), FakePage("Page two has different readable text.")]

        record = self.service.extract_all().documents[0]

        self.assertEqual([page["page_number"] for page in record["pages"]], [1, 2])

    def test_checksum_mismatch_is_rejected_without_output(self):
        path = self.make_pdf()
        self.register_manifest(path, checksum="0" * 64)
        FakeReader.pages = [FakePage("This should not be extracted.")]

        report = self.service.extract_all()

        self.assertEqual(report.failed, 1)
        self.assertIn("ChecksumMismatchError", report.documents[0]["error"])
        self.assertEqual(list(self.output.rglob("*.json")), [])

    def test_missing_file_is_reported(self):
        missing = self.folder / "missing.pdf"
        self.register_manifest(missing, checksum="a" * 64)

        report = self.service.extract_all()

        self.assertEqual(report.failed, 1)
        self.assertIn("does not exist", report.documents[0]["error"])

    def test_empty_scanned_pdf_is_marked_ocr_required(self):
        path = self.make_pdf()
        self.register_manifest(path)
        FakeReader.pages = [FakePage(None), FakePage("")]

        report = self.service.extract_all()
        record = report.documents[0]

        self.assertEqual(record["quality_status"], "OCR_REQUIRED")
        self.assertEqual(report.ocr_required, 1)
        self.assertEqual([p["extraction_status"] for p in record["pages"]], ["EMPTY", "EMPTY"])
        self.assertTrue(any("OCR is not performed" in warning for warning in record["extraction_warnings"]))

    def test_failed_page_is_preserved_and_later_pages_continue(self):
        path = self.make_pdf()
        self.register_manifest(path)
        FakeReader.pages = [FakePage("Page one has readable content for extraction."), FakePage(error=RuntimeError("page decode failed")), FakePage("Page three also has readable content for extraction.")]

        report = self.service.extract_all()
        pages = report.documents[0]["pages"]

        self.assertEqual([p["page_number"] for p in pages], [1, 2, 3])
        self.assertEqual(pages[1]["extraction_status"], "EXTRACTION_FAILED")
        self.assertEqual(pages[2]["text"], "Page three also has readable content for extraction.")
        self.assertEqual(report.pages_failed, 1)

    def test_repeated_extraction_does_not_overwrite_output(self):
        path = self.make_pdf()
        self.register_manifest(path)
        FakeReader.pages = [FakePage("A stable page of readable test content for extraction.")]

        first = self.service.extract_all()
        output_path = Path(first.documents[0]["intermediate_output_path"])
        original = output_path.read_bytes()
        second = self.service.extract_all()

        self.assertEqual(second.documents_skipped_existing_output, 1)
        self.assertEqual(output_path.read_bytes(), original)

    def test_extraction_does_not_create_chunks_or_embeddings(self):
        path = self.make_pdf()
        self.register_manifest(path)
        FakeReader.pages = [FakePage("A sufficiently long sample paragraph for extraction testing.")]

        self.service.extract_all()

        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0], 0)
        table_names = {row[0] for row in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertFalse(any("embedding" in name.lower() for name in table_names))

    def test_extraction_preserves_pending_source_validation_status(self):
        path = self.make_pdf()
        self.register_manifest(path)
        FakeReader.pages = [FakePage("A sufficiently long sample paragraph for extraction testing.")]

        self.service.extract_all()

        row = self.connection.execute(
            "SELECT validation_status, manual_verification, rag_allowed FROM source_registry WHERE source_id = ?",
            ("pm_kisan_official",),
        ).fetchone()
        self.assertEqual(tuple(row), ("PENDING", "NO", 0))
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM source_validations").fetchone()[0], 0)

    def test_extract_all_only_reads_manifest_rows(self):
        unregistered = self.make_pdf("not-registered.pdf")
        FakeReader.pages = [FakePage("This file is not listed in the manifest.")]

        report = self.service.extract_all()

        self.assertEqual(report.documents_seen, 0)
        self.assertEqual(report.documents, [])
        self.assertTrue(unregistered.is_file())

    def test_dry_run_checks_checksum_without_writing_output(self):
        path = self.make_pdf()
        self.register_manifest(path)

        report = self.service.extract_all(dry_run=True)

        self.assertTrue(report.documents[0]["would_extract"])
        self.assertEqual(list(self.output.rglob("*.json")) if self.output.exists() else [], [])


if __name__ == "__main__":
    unittest.main()
