import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.knowledge.chunking import (
    ChunkingConfig,
    ChunkingService,
    HierarchicalChunker,
    SentenceRecord,
    build_report,
    cosine_similarity,
    split_sentences,
)
from backend.knowledge.models import SourceRegistry
from backend.knowledge.repository import KnowledgeRepository


class ChunkingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.auth_root = self.base / "authoritative_documents"
        self.topic_dir = self.auth_root / "pm_kisan"
        self.topic_dir.mkdir(parents=True)
        self.input_dir = self.base / "ingestion_output"
        self.input_dir.mkdir()
        self.output_db = self.base / "knowledge.sqlite"
        self.repository = KnowledgeRepository(sqlite3.connect(self.output_db))
        self.connection = self.repository.connection
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
            document_title="PM-KISAN FAQ",
            document_type="FAQ",
            rag_allowed=False,
        ))
        self.pdf_path = self.topic_dir / "sample.pdf"
        self.pdf_path.write_bytes(b"%PDF-1.7 chunking test fixture")
        self.record_path = self.input_dir / "sample.json"
        self.config = ChunkingConfig(
            chunking_version="test-v1",
            target_child_tokens=24,
            max_child_tokens=36,
            min_child_tokens=10,
            overlap_sentences=1,
            parent_target_tokens=100,
            max_parent_tokens=130,
            semantic_min_chunk_tokens=1000,
            semantic_similarity_threshold=0.2,
        )
        self._write_record(self._sample_pages())

    def tearDown(self):
        self.repository.close()
        self.temp.cleanup()

    def _sample_pages(self):
        page_one = """PM-KISAN ELIGIBILITY

1. The farmer family must have cultivable land recorded in its name. State authorities verify the land record before assistance is released.

2. Institutional landholders are excluded from the scheme. Eligible family details must match the application records."""
        page_two = """BENEFIT AND PAYMENT

The benefit is transferred in installments to the verified beneficiary account. Farmers should confirm account information through the official portal.

Contact the local agriculture office for application support and status updates."""
        return [
            {"page_number": 1, "text": page_one, "has_text": True, "extraction_status": "SUCCESS",
             "structure": {"headings": [{"line_number": 1, "text": "PM-KISAN ELIGIBILITY"}]}},
            {"page_number": 2, "text": page_two, "has_text": True, "extraction_status": "SUCCESS",
             "structure": {"headings": [{"line_number": 1, "text": "BENEFIT AND PAYMENT"}]}},
        ]

    def _write_record(self, pages, *, document_id="test-document"):
        digest = hashlib.sha256(self.pdf_path.read_bytes()).hexdigest()
        record = {
            "source_id": "pm_kisan_official",
            "document_id": document_id,
            "filename": self.pdf_path.name,
            "absolute_source_path": str(self.pdf_path.resolve()),
            "relative_source_path": str(self.pdf_path.resolve()),
            "sha256": digest,
            "extraction_status": "SUCCESS",
            "pages": pages,
            "source_metadata": {"validation_status": "PENDING"},
        }
        self.record_path.write_text(json.dumps(record), encoding="utf-8")
        return record

    def _service(self, config=None):
        return ChunkingService(
            database_path=self.output_db,
            input_root=self.input_dir,
            authoritative_root=self.auth_root,
            config=config or self.config,
        )

    def test_sentence_segmentation_handles_government_punctuation(self):
        text = "1.2. Eligibility: Dr. Rao filed the form on 01.05.2025. The rate is 7.5%. Visit https://pmkisan.gov.in.\n(a) Submit land records.\n(b) Verify bank details."

        sentences = split_sentences(text)

        self.assertGreaterEqual(len(sentences), 5)
        self.assertTrue(sentences[0].startswith("1.2."))
        self.assertTrue(any("Dr. Rao" in sentence for sentence in sentences))
        self.assertTrue(any("01.05.2025" in sentence and "7.5%" not in sentence for sentence in sentences))
        self.assertTrue(any("https://pmkisan.gov.in" in sentence for sentence in sentences))
        self.assertTrue(any(sentence.startswith("(a)") for sentence in sentences))
        self.assertTrue(any(sentence.startswith("(b)") for sentence in sentences))

    def test_paragraph_boundaries_are_preserved(self):
        service = self._service()
        try:
            result = service.chunker.chunk_document(json.loads(self.record_path.read_text(encoding="utf-8")))
        finally:
            service.close()

        parent_texts = [row["text"] for row in result["parent_rows"]]
        self.assertTrue(any("\n\n" in text for text in parent_texts))

    def test_heading_preservation_and_parent_child_relationship(self):
        service = self._service()
        try:
            result = service.chunker.chunk_document(json.loads(self.record_path.read_text(encoding="utf-8")))
        finally:
            service.close()

        headings = {row["section_heading"] for row in result["parent_rows"]}
        self.assertIn("PM-KISAN ELIGIBILITY", headings)
        self.assertIn("BENEFIT AND PAYMENT", headings)
        parent_ids = {row["chunk_id"] for row in result["parent_rows"]}
        self.assertTrue(result["child_rows"])
        self.assertTrue(all(row["parent_chunk_id"] in parent_ids for row in result["child_rows"]))

    def test_semantic_similarity_detects_topic_change(self):
        idf = None
        related_a = "Farmer crop insurance premium and notified crop coverage for the season."
        related_b = "Crop insurance premium is paid for notified crops during each season."
        unrelated = "The grievance appeal tribunal hears pension disputes and service complaints."
        self.assertGreater(cosine_similarity(related_a, related_b, idf), cosine_similarity(related_a, unrelated, idf))
        config = ChunkingConfig(
            chunking_version="semantic-boundary-test",
            target_child_tokens=12,
            max_child_tokens=100,
            min_child_tokens=5,
            overlap_sentences=0,
            parent_target_tokens=200,
            max_parent_tokens=250,
            semantic_similarity_threshold=0.2,
            semantic_min_chunk_tokens=5,
        )
        sentences = [
            SentenceRecord(i + 1, text, 1, 0, "Test")
            for i, text in enumerate([related_a, related_b, unrelated])
        ]
        groups = _child_groups_for_test(sentences, config)
        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual(groups[0]["boundary_reason"], "semantic_similarity_drop")

    def test_limits_and_sentence_overlap(self):
        service = self._service()
        try:
            result = service.chunker.chunk_document(json.loads(self.record_path.read_text(encoding="utf-8")))
        finally:
            service.close()

        self.assertGreater(len(result["child_rows"]), 1)
        self.assertTrue(all(row["token_count"] <= self.config.max_child_tokens for row in result["child_rows"]))
        self.assertEqual(result["child_rows"][0]["overlap_sentence_count"], 0)
        later = result["child_rows"][1]
        self.assertEqual(later["overlap_sentence_count"], 1)
        metadata = json.loads(later["overlap_metadata"])
        self.assertEqual(metadata["overlap_sentence_count"], 1)
        self.assertTrue(metadata["overlap_text"][0])

    def test_page_provenance_and_deterministic_ids(self):
        extraction = json.loads(self.record_path.read_text(encoding="utf-8"))
        service = self._service()
        try:
            first = service.chunker.chunk_document(extraction)
            second = service.chunker.chunk_document(extraction)
        finally:
            service.close()

        self.assertEqual([r["chunk_id"] for r in first["parent_rows"]], [r["chunk_id"] for r in second["parent_rows"]])
        self.assertEqual([r["chunk_id"] for r in first["child_rows"]], [r["chunk_id"] for r in second["child_rows"]])
        self.assertEqual({(r["page_start"], r["page_end"]) for r in first["child_rows"]}, {(1, 1), (2, 2)})
        self.assertTrue(all(r["source_id"] == "pm_kisan_official" and r["document_id"] == "test-document" for r in first["child_rows"]))

    def test_run_is_idempotent_and_changed_checksum_creates_history(self):
        service = self._service()
        try:
            first = service.run()
            again = service.run()
            first_checksum = json.loads(self.record_path.read_text(encoding="utf-8"))["sha256"]
            self.pdf_path.write_bytes(b"%PDF-1.7 changed source fixture")
            changed_record = self._write_record(self._sample_pages())
            self.assertNotEqual(first_checksum, changed_record["sha256"])
            changed = service.run()
        finally:
            service.close()

        self.assertEqual(first["documents_processed"], 1)
        self.assertEqual(again["documents_skipped_idempotent"], 1)
        self.assertEqual(changed["documents_processed"], 1)
        self.assertEqual(self.connection_count("chunking_runs"), 2)
        self.assertEqual(self.connection_count("hierarchical_chunks"), first["parent_chunks"] + first["child_chunks"] + changed["parent_chunks"] + changed["child_chunks"])

    def test_source_validation_status_is_not_modified_and_snapshotted(self):
        service = self._service()
        try:
            report = service.run()
        finally:
            service.close()

        status = self.connection.execute("SELECT validation_status FROM source_registry WHERE source_id='pm_kisan_official'").fetchone()[0]
        run_status = self.connection.execute("SELECT source_validation_status FROM chunking_runs").fetchone()[0]
        self.assertEqual(status, "PENDING")
        self.assertEqual(run_status, "PENDING")
        self.assertEqual(report["documents_processed"], 1)

    def test_no_chunks_without_document_provenance(self):
        extraction = json.loads(self.record_path.read_text(encoding="utf-8"))
        extraction.pop("source_id")
        self.record_path.write_text(json.dumps(extraction), encoding="utf-8")
        service = self._service()
        try:
            result = service.run()
        finally:
            service.close()
        self.assertEqual(result["documents_failed"], 1)
        self.assertEqual(self.connection_count("hierarchical_chunks"), 0)

    def test_report_statistics_and_debug_sample(self):
        service = self._service()
        try:
            service.run()
        finally:
            service.close()
        report = build_report(self.output_db, debug=True)
        self.assertEqual(report["documents_processed"], 1)
        self.assertGreater(report["parent_chunks"], 0)
        self.assertGreater(report["child_chunks"], 0)
        self.assertEqual(report["chunks_without_provenance"], 0)
        self.assertTrue(report["sample_chunks"])

    def connection_count(self, table):
        return self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# Exercise the same child grouping implementation directly for a controlled semantic boundary case.
def _child_groups_for_test(sentences, config):
    from backend.knowledge.chunking import _make_child_groups
    return _make_child_groups(sentences, "Test", config)


if __name__ == "__main__":
    unittest.main()
