import sqlite3
import unittest
from datetime import datetime, timezone

from knowledge.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    SourceRegistry,
    SourceValidation,
    SourceVersion,
)
from knowledge.repository import KnowledgeRepository


class KnowledgeRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = KnowledgeRepository(sqlite3.connect(":memory:"))
        self.repository.migrate()
        self.checked_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        self.repository.register_source(SourceRegistry(
            source_id="pm_kisan_source", authority="Government of India",
            source_name="PM-KISAN official portal", official_url="https://pmkisan.gov.in",
            jurisdiction="India", source_type="official_portal", authority_tier=1,
            monitoring_frequency_days=30, last_checked=self.checked_at,
            last_changed=None, current_version_id=None, status="active",
        ))
        self.repository.add_version(SourceVersion(
            version_id="pm_kisan_v1", source_id="pm_kisan_source", document_hash="hash-v1",
            retrieved_at=self.checked_at, published_at=None, effective_from=None,
            effective_until=None, status="current", change_summary="Initial validation",
            validation_status="validated",
        ))
        self.repository.add_document(KnowledgeDocument(
            document_id="pm_kisan_doc_v1", version_id="pm_kisan_v1", scheme_id="pm_kisan",
            title="PM-KISAN", document_type="official_guidance", source_authority="Government of India",
            jurisdiction="India", effective_date=self.checked_at, content_hash="hash-v1", status="current",
        ))
        self.repository.add_chunks([KnowledgeChunk(
            chunk_id="pm_kisan_chunk_v1", document_id="pm_kisan_doc_v1",
            text="Eligibility must be verified against the current official guidance.",
            section="Eligibility", page=1, metadata={}, embedding_model=None, embedding_version=None,
        )])

    def test_current_authoritative_evidence_exposes_provenance(self):
        self._verify_source()
        result = self.repository.retrieve_current("pm_kisan", now=self.checked_at)

        self.assertFalse(result.insufficient_current_evidence)
        evidence = result.evidence[0]
        self.assertEqual(evidence.source.authority, "Government of India")
        self.assertEqual(evidence.version.version_id, "pm_kisan_v1")
        self.assertEqual(evidence.freshness_status.value, "VERIFIED")
        self.assertEqual(evidence.effective_date, self.checked_at)

    def test_superseded_version_is_never_retrieved(self):
        self._verify_source()
        self.repository.add_version(SourceVersion(
            version_id="pm_kisan_v2", source_id="pm_kisan_source", document_hash="hash-v2",
            retrieved_at=self.checked_at, published_at=None, effective_from=None,
            effective_until=None, status="current", change_summary="Updated guidance",
            validation_status="pending",
        ))

        result = self.repository.retrieve_current("pm_kisan", now=self.checked_at)

        self.assertTrue(result.insufficient_current_evidence)
        self.assertEqual(result.evidence, ())

    def test_no_authoritative_evidence_sets_insufficient_flag(self):
        self.repository.connection.execute("UPDATE source_registry SET authority_tier = 3")
        self.repository.connection.commit()

        result = self.repository.retrieve_current("pm_kisan", now=self.checked_at)

        self.assertTrue(result.insufficient_current_evidence)

    def test_pending_source_cannot_be_retrieved(self):
        result = self.repository.retrieve_current("pm_kisan", now=self.checked_at)

        self.assertTrue(result.insufficient_current_evidence)

    def test_verified_source_becomes_authoritative(self):
        self._verify_source()

        result = self.repository.retrieve_current("pm_kisan", now=self.checked_at)

        self.assertFalse(result.insufficient_current_evidence)

    def test_stale_source_cannot_be_retrieved(self):
        self._verify_source()

        result = self.repository.retrieve_current(
            "pm_kisan", now=datetime(2026, 12, 1, tzinfo=timezone.utc)
        )

        self.assertTrue(result.insufficient_current_evidence)

    def test_missing_official_source_remains_pending(self):
        self.repository.register_source(SourceRegistry(
            source_id="missing_url_source", authority="Not yet verified",
            source_name="Agricultural subsidies", official_url="", jurisdiction="Maharashtra / India",
            source_type="unverified_topic", authority_tier=3, monitoring_frequency_days=30,
            last_checked=None, last_changed=None, current_version_id=None, status="active",
            scheme_id="agricultural_subsidies", scheme_name="Agricultural subsidies",
            official_source_name="Not yet identified",
        ))

        row = next(item for item in self.repository.validation_report() if item["scheme"] == "Agricultural subsidies")

        self.assertEqual(row["validation_status"], "PENDING")
        self.assertIn("official_url", row["missing_metadata"])

    def test_validation_metadata_is_preserved(self):
        self._verify_source()
        row = self.repository.connection.execute(
            "SELECT * FROM source_validations WHERE source_id = ?",
            ("pm_kisan_source",),
        ).fetchone()

        self.assertEqual(row["validated_by"], "manual-reviewer")
        self.assertEqual(row["document_reference"], "PM-KISAN circular 2026-01")
        self.assertEqual(row["validation_notes"], "Matched eligibility and benefit sections.")

    def _verify_source(self):
        self.repository.record_validation(SourceValidation(
            validation_id="validation_pm_kisan_v1",
            source_id="pm_kisan_source",
            version_id="pm_kisan_v1",
            scheme_id="pm_kisan",
            validation_status="VERIFIED",
            validated_by="manual-reviewer",
            validation_method="manual comparison",
            validated_at=self.checked_at,
            official_source_url="https://pmkisan.gov.in",
            document_reference="PM-KISAN circular 2026-01",
            validation_notes="Matched eligibility and benefit sections.",
        ))


if __name__ == "__main__":
    unittest.main()
