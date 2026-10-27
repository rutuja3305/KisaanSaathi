import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from backend.knowledge.document_ingestion import (
    DocumentIngestionPipeline,
    has_pdf_signature,
    sha256_file,
)


class FakeMetadata(dict):
    pass


class FakePage:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error

    def extract_text(self, extraction_mode="layout"):
        if self.error:
            raise self.error
        return self.text


class FakeReader:
    pages_by_path = {}
    metadata_by_path = {}
    encrypted_paths = set()

    def __init__(self, path, strict=False):
        if path not in self.pages_by_path:
            raise ValueError("Synthetic PDF parse failure")
        self.pages = self.pages_by_path[path]
        self.metadata = self.metadata_by_path.get(path, FakeMetadata())
        self.is_encrypted = path in self.encrypted_paths

    def decrypt(self, password):
        return 0


class DocumentIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "authoritative_documents"
        self.output = Path(self.temp.name) / "intermediate"
        self.topic = self.root / "pm_kisan"
        self.topic.mkdir(parents=True)
        self.catalog = {
            "pm_kisan_official": {
                "source_id": "pm_kisan_official",
                "scheme_id": "pm_kisan",
                "topic": "PM-KISAN",
                "authority": "Government of India",
                "department": "Department of Agriculture & Farmers Welfare",
                "official_url": "https://pmkisan.gov.in/",
                "document_title": "PM-KISAN FAQ",
                "validation_status": "PENDING",
            }
        }
        FakeReader.pages_by_path = {}
        FakeReader.metadata_by_path = {}
        FakeReader.encrypted_paths = set()
        self.pipeline = DocumentIngestionPipeline(
            documents_root=self.root,
            output_root=self.output,
            source_catalog=self.catalog,
            reader_factory=FakeReader,
        )

    def tearDown(self):
        self.temp.cleanup()

    def make_pdf(self, name="sample.pdf", content=b"%PDF-1.7 synthetic"):
        path = self.topic / name
        path.write_bytes(content)
        return path

    def test_pdf_discovery_and_empty_topic_folder(self):
        pdf = self.make_pdf()
        (self.root / "empty_topic").mkdir()
        (self.topic / "ignored.txt").write_text("not a PDF", encoding="utf-8")

        found = self.pipeline.discover()

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["filename"], pdf.name)
        self.assertEqual(found[0]["source_id"], "pm_kisan_official")

    def test_only_authoritative_root_is_scanned_not_legacy_schemes(self):
        self.make_pdf()
        legacy = Path(self.temp.name) / "backend" / "schemes"
        legacy.mkdir(parents=True)
        (legacy / "old.pdf").write_bytes(b"%PDF-1.4 legacy")

        found = self.pipeline.discover()

        self.assertEqual([item["filename"] for item in found], ["sample.pdf"])

    def test_sha256_generation(self):
        pdf = self.make_pdf()
        self.assertEqual(sha256_file(pdf), hashlib.sha256(pdf.read_bytes()).hexdigest())

    def test_pdf_signature_validation(self):
        valid = self.make_pdf("valid.pdf", b"%PDF-1.5 body")
        invalid = self.make_pdf("invalid.pdf", b"not a pdf")
        self.assertTrue(has_pdf_signature(valid))
        self.assertFalse(has_pdf_signature(invalid))

    def test_page_numbering_extraction_structure_and_provenance(self):
        pdf = self.make_pdf()
        FakeReader.pages_by_path[str(pdf.resolve())] = [
            FakePage("SECTION 1: ELIGIBILITY\n\n1.1 Farmer qualification\n\n- Land records"),
            FakePage("TABLE\nCrop  Season\nWheat  Rabi"),
        ]
        FakeReader.metadata_by_path[str(pdf.resolve())] = FakeMetadata({"/Title": "Official PM-KISAN FAQ"})

        report = self.pipeline.ingest()
        record = report.documents[0]

        self.assertEqual(record["source_id"], "pm_kisan_official")
        self.assertEqual(record["sha256"], sha256_file(pdf))
        self.assertEqual(record["title"], "Official PM-KISAN FAQ")
        self.assertEqual([page["page_number"] for page in record["pages"]], [1, 2])
        self.assertTrue(all(page["has_text"] for page in record["pages"]))
        self.assertEqual(record["pages"][0]["extraction_status"], "SUCCESS")
        self.assertTrue(record["pages"][0]["structure"]["numbered_sections"])
        self.assertTrue(record["pages"][0]["structure"]["list_items"])
        self.assertTrue(record["pages"][1]["structure"]["table_candidates"])
        self.assertTrue(Path(record["intermediate_output_path"]).is_file())
        output_record = json.loads(Path(record["intermediate_output_path"]).read_text(encoding="utf-8"))
        self.assertEqual(output_record["relative_source_path"], record["relative_source_path"])
        self.assertEqual(output_record["pages"][1]["page_number"], 2)

    def test_empty_page_is_preserved(self):
        pdf = self.make_pdf()
        FakeReader.pages_by_path[str(pdf.resolve())] = [FakePage("")]

        report = self.pipeline.ingest()
        page = report.documents[0]["pages"][0]

        self.assertEqual(page["page_number"], 1)
        self.assertFalse(page["has_text"])
        self.assertEqual(page["extraction_status"], "EMPTY")
        self.assertEqual(report.pages_empty, 1)

    def test_page_failure_does_not_stop_remaining_pages(self):
        pdf = self.make_pdf()
        FakeReader.pages_by_path[str(pdf.resolve())] = [
            FakePage("Page one"),
            FakePage(error=RuntimeError("synthetic extraction error")),
            FakePage("Page three"),
        ]

        report = self.pipeline.ingest()
        pages = report.documents[0]["pages"]

        self.assertEqual([page["page_number"] for page in pages], [1, 2, 3])
        self.assertEqual(pages[1]["extraction_status"], "EXTRACTION_FAILED")
        self.assertEqual(pages[2]["text"], "Page three")
        self.assertEqual(report.pages_failed, 1)

    def test_invalid_pdf_is_reported_without_extraction(self):
        self.make_pdf(content=b"invalid data")

        report = self.pipeline.ingest()

        self.assertEqual(report.documents_failed, 1)
        self.assertEqual(report.documents[0]["extraction_status"], "INVALID_PDF")
        self.assertEqual(report.documents[0]["pages"], [])

    def test_repeated_ingestion_never_overwrites_existing_output(self):
        pdf = self.make_pdf()
        FakeReader.pages_by_path[str(pdf.resolve())] = [FakePage("A stable page")]
        first = self.pipeline.ingest()
        output_path = Path(first.documents[0]["intermediate_output_path"])
        original_bytes = output_path.read_bytes()

        second = self.pipeline.ingest()

        self.assertEqual(second.documents_skipped_existing_output, 1)
        self.assertEqual(output_path.read_bytes(), original_bytes)
        self.assertEqual(second.documents[0]["output_status"], "OUTPUT_EXISTS_UNCHANGED")

    def test_unmapped_source_is_not_silently_assigned(self):
        folder = self.root / "unregistered_topic"
        folder.mkdir()
        (folder / "unknown.pdf").write_bytes(b"%PDF-1.4 unknown")
        found = self.pipeline.discover()
        record = next(item for item in found if item["filename"] == "unknown.pdf")
        self.assertIsNone(record["source_id"])
        self.assertEqual(record["source_mapping_status"], "UNMAPPED")


if __name__ == "__main__":
    unittest.main()
