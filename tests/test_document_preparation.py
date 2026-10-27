import hashlib
import json
import sqlite3
import tempfile
import unittest
import unicodedata
from pathlib import Path

from backend.knowledge.document_preparation import (
    DocumentPreparationService,
    ManifestDocumentStore,
    normalize_paragraph,
)
from backend.knowledge.models import SourceRegistry
from backend.knowledge.repository import KnowledgeRepository


class FakeManifestStore:
    def __init__(self, rows):
        self.rows = rows

    def list_documents(self, source_id=None):
        return [row for row in self.rows if source_id is None or row["source_id"] == source_id]

    def close(self):
        pass


class DocumentPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.auth_root = self.base / "authoritative_documents"
        self.pdf_dir = self.auth_root / "pm_kisan"
        self.pdf_dir.mkdir(parents=True)
        self.extraction_root = self.base / "extraction_output"
        self.extraction_root.mkdir()
        self.prepared_root = self.base / "prepared_output"
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
            manual_verification="NO",
            document_title="Official PM-KISAN FAQ",
            document_type="FAQ",
            rag_allowed=False,
        ))
        self.pdf_path = self.pdf_dir / "faq.pdf"
        self.pdf_path.write_bytes(b"%PDF-1.7 test bytes")
        self.checksum = hashlib.sha256(self.pdf_path.read_bytes()).hexdigest()
        self.document_id = "manifest-pmk-001"
        self.manifest = {
            "document_id": self.document_id,
            "source_id": "pm_kisan_official",
            "version_id": "local-test-version",
            "scheme_id": "pm_kisan",
            "topic": "PM-KISAN",
            "authority": "Government of India",
            "department": "Department of Agriculture & Farmers Welfare",
            "official_url": "https://pmkisan.gov.in/",
            "document_title": "Official PM-KISAN FAQ",
            "document_type": "FAQ",
            "document_number": None,
            "publication_date": None,
            "effective_from": None,
            "effective_until": None,
            "jurisdiction": "India",
            "authority_tier": 1,
            "validation_status": "PENDING",
            "validated_by": None,
            "validated_at": None,
            "rag_allowed": 0,
            "structured_db_required": 1,
            "local_file": str(self.pdf_path.resolve()),
            "checksum": self.checksum,
            "notes": "Source record stays pending.",
        }
        self.extraction_path = self.extraction_root / "pmk.json"
        self.write_extraction(self.good_extraction())
        self.store = FakeManifestStore([self.manifest])
        self.service = DocumentPreparationService(
            database_path=self.db_path,
            extraction_root=self.extraction_root,
            prepared_root=self.prepared_root,
            manifest_store=self.store,
            authoritative_root=self.auth_root,
        )

    def tearDown(self):
        self.service.close()
        self.repository.close()
        self.temp.cleanup()

    def good_extraction(self):
        raw_first = "PM-KISAN ELIGIBILITY\n\nFarmer famil-\nies must meet the scheme rules.\n\nDr. Rao submitted form 1.2 on 01.05.2025."
        raw_second = "Payment details\n\nBenefits are paid to the verified bank account.\n\nContact the local office for help."
        return {
            "source_id": "pm_kisan_official",
            "document_id": self.document_id,
            "manifest_id": self.document_id,
            "version_id": "local-test-version",
            "filename": self.pdf_path.name,
            "local_file": str(self.pdf_path.resolve()),
            "absolute_source_path": str(self.pdf_path.resolve()),
            "sha256": self.checksum,
            "file_type": ".pdf",
            "title": "PM-KISAN FAQ PDF title",
            "document_metadata": {"Title": "PDF metadata title", "Author": "Department"},
            "manifest_metadata": self.manifest,
            "source_metadata": {"validation_status": "PENDING", "manual_verification": "NO"},
            "extraction_status": "SUCCESS",
            "extraction_timestamp": "2026-09-28T10:00:00+00:00",
            "pages": [
                {"page_number": 1, "text": raw_first, "has_text": True, "extraction_status": "SUCCESS",
                 "structure": {"headings": [{"line_number": 1, "text": "PM-KISAN ELIGIBILITY"}]}},
                {"page_number": 2, "text": raw_second, "has_text": True, "extraction_status": "SUCCESS",
                 "structure": {"headings": [{"line_number": 1, "text": "Payment details"}]}},
            ],
        }

    def write_extraction(self, data):
        self.extraction_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load_prepared(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def test_raw_text_is_preserved_and_cleaned_text_is_separate(self):
        source = self.good_extraction()
        original_raw = source["pages"][0]["text"]
        self.write_extraction(source)

        report = self.service.prepare_all()
        prepared = self.load_prepared(report.prepared_outputs[0])

        self.assertEqual(prepared["pages"][0]["raw_text"], original_raw)
        self.assertNotEqual(prepared["pages"][0]["cleaned_text"], original_raw)
        self.assertIn("families", prepared["pages"][0]["cleaned_text"])

    def test_whitespace_unicode_and_hyphenation_normalization(self):
        text = "  Caf\u0065\u0301   benefit-\n amount  \n\n\n  next line  "

        cleaned = normalize_paragraph(text)

        self.assertEqual(cleaned, "Caf\u00e9 benefitamount next line")
        self.assertEqual(cleaned, unicodedata.normalize("NFC", cleaned))

    def test_paragraphs_headings_and_sections_are_preserved(self):
        self.write_extraction(self.good_extraction())
        report = self.service.prepare_all()
        prepared = self.load_prepared(report.prepared_outputs[0])

        self.assertGreaterEqual(len(prepared["sections"]), 2)
        self.assertEqual(prepared["pages"][0]["paragraphs"][0]["section_heading"], "PM-KISAN ELIGIBILITY")
        self.assertGreaterEqual(len(prepared["pages"][0]["paragraphs"]), 2)
        self.assertTrue(any(section["heading"] == "Payment details" for section in prepared["sections"]))
        self.assertIn("\n\n", prepared["pages"][0]["cleaned_text"])

    def test_sentence_mapping_and_character_offsets(self):
        self.write_extraction(self.good_extraction())
        report = self.service.prepare_all()
        prepared = self.load_prepared(report.prepared_outputs[0])
        all_sentences = [sentence for page in prepared["pages"] for sentence in page["sentences"]]

        self.assertTrue(all_sentences)
        for sentence in all_sentences:
            page = next(item for item in prepared["pages"] if item["page_number"] == sentence["page_number"])
            paragraph = next(item for item in page["paragraphs"] if item["paragraph_id"] == sentence["paragraph_id"])
            self.assertEqual(sentence["section_id"], paragraph["section_id"])
            self.assertEqual(paragraph["cleaned_text"][sentence["character_start"]:sentence["character_end"]], sentence["text"])
            self.assertEqual(sentence["offset_basis"], "paragraph.cleaned_text")

    def test_exact_page_mapping_and_page_boundaries(self):
        self.write_extraction(self.good_extraction())
        prepared = self.load_prepared(self.service.prepare_all().prepared_outputs[0])

        self.assertEqual([page["page_number"] for page in prepared["pages"]], [1, 2])
        self.assertTrue(all(sentence["page_number"] == 1 for sentence in prepared["pages"][0]["sentences"]))
        self.assertTrue(all(sentence["page_number"] == 2 for sentence in prepared["pages"][1]["sentences"]))

    def test_document_metadata_and_checksum_are_preserved(self):
        self.write_extraction(self.good_extraction())
        prepared = self.load_prepared(self.service.prepare_all().prepared_outputs[0])

        self.assertEqual(prepared["source_id"], self.manifest["source_id"])
        self.assertEqual(prepared["document_id"], self.document_id)
        self.assertEqual(prepared["document_checksum"], self.checksum)
        self.assertEqual(prepared["manifest_metadata"]["department"], self.manifest["department"])
        self.assertEqual(prepared["document_metadata"]["Author"], "Department")
        self.assertEqual(prepared["extraction_timestamp"], "2026-09-28T10:00:00+00:00")
        self.assertEqual(prepared["preparation_version"], "prepared-text-v1")

    def test_idempotent_preparation_does_not_overwrite(self):
        self.write_extraction(self.good_extraction())
        first = self.service.prepare_all()
        output_path = Path(first.prepared_outputs[0])
        original = output_path.read_bytes()
        second = self.service.prepare_all()

        self.assertEqual(first.documents_processed, 1)
        self.assertEqual(second.documents_skipped_idempotent, 1)
        self.assertEqual(output_path.read_bytes(), original)

    def test_malformed_extraction_record_is_reported(self):
        malformed = self.good_extraction()
        malformed["pages"] = [{"page_number": "one", "text": "text"}]
        self.write_extraction(malformed)

        report = self.service.prepare_all()

        self.assertEqual(report.documents_invalid_extraction, 1)
        self.assertIn("positive page_number", report.errors[0]["error"])
        self.assertEqual(report.prepared_outputs, [])

    def test_empty_pages_are_preserved(self):
        extraction = self.good_extraction()
        extraction["pages"].insert(1, {"page_number": 3, "text": "", "has_text": False, "extraction_status": "EMPTY", "structure": {"headings": []}})
        self.write_extraction(extraction)

        prepared = self.load_prepared(self.service.prepare_all().prepared_outputs[0])

        empty = next(page for page in prepared["pages"] if page["page_number"] == 3)
        self.assertEqual(empty["raw_text"], "")
        self.assertEqual(empty["cleaned_text"], "")
        self.assertEqual(empty["paragraphs"], [])
        self.assertEqual(empty["sentences"], [])

    def test_unregistered_extraction_is_ignored(self):
        extraction = self.good_extraction()
        extraction["document_id"] = "not-in-manifest"
        self.write_extraction(extraction)

        report = self.service.prepare_all()

        self.assertEqual(report.manifest_documents, 1)
        self.assertEqual(report.documents_missing_extraction, 1)
        self.assertEqual(report.documents_processed, 0)

    def test_registry_and_chunk_tables_are_not_changed(self):
        self.write_extraction(self.good_extraction())
        self.service.prepare_all()

        source = self.connection.execute("SELECT validation_status,manual_verification,rag_allowed FROM source_registry WHERE source_id=?", ("pm_kisan_official",)).fetchone()
        self.assertEqual(tuple(source), ("PENDING", "NO", 0))
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM source_validations").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM hierarchical_chunks").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
