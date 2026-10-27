from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from .freshness import freshness_status, parse_datetime, utc_now
from .models import (
    FreshnessStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    RetrievalEvidence,
    RetrievalResult,
    SourceRegistry,
    SourceVersion,
    SourceValidation,
    ValidationStatus,
)


MIGRATIONS_PATH = Path(__file__).parent.parent / "resources" / "migrations"


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return normalized.isoformat()


class KnowledgeRepository:
    """Persistence and evidence-safety boundary for government knowledge."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def from_path(cls, path: str | Path) -> "KnowledgeRepository":
        connection = sqlite3.connect(path)
        repository = cls(connection)
        repository.migrate()
        return repository

    def migrate(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS knowledge_migrations (name TEXT PRIMARY KEY)"
        )
        for migration in sorted(MIGRATIONS_PATH.glob("*.sql")):
            applied = self.connection.execute(
                "SELECT 1 FROM knowledge_migrations WHERE name = ?", (migration.name,)
            ).fetchone()
            if applied:
                continue
            if migration.name == "001_versioned_knowledge.sql" and self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'source_registry'"
            ).fetchone():
                self.connection.execute(
                    "INSERT INTO knowledge_migrations (name) VALUES (?)", (migration.name,)
                )
                continue
            if migration.name == "002_source_registry_validation.sql" and self._has_column(
                "source_registry", "validation_status"
            ):
                self.connection.execute(
                    "INSERT INTO knowledge_migrations (name) VALUES (?)", (migration.name,)
                )
                continue
            if migration.name == "003_source_registry_document_metadata.sql" and self._has_column(
                "source_registry", "department"
            ):
                self.connection.execute(
                    "INSERT INTO knowledge_migrations (name) VALUES (?)", (migration.name,)
                )
                continue
            self.connection.executescript(migration.read_text(encoding="utf-8"))
            self.connection.execute(
                "INSERT INTO knowledge_migrations (name) VALUES (?)", (migration.name,)
            )
        self.connection.commit()

    def _has_column(self, table: str, column: str) -> bool:
        columns = self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in columns)

    def close(self) -> None:
        self.connection.close()

    def register_source(self, source: SourceRegistry) -> None:
        self.connection.execute(
              """INSERT INTO source_registry
            (source_id, authority, source_name, official_url, jurisdiction, source_type,
             authority_tier, monitoring_frequency_days, last_checked, last_changed,
               current_version_id, status, scheme_id, scheme_name, official_source_name,
                             validation_status, monitoring_frequency, department, document_title,
                             document_type, document_number, publication_date, effective_from,
                             effective_until, dynamic_flag, rag_eligibility, structured_data_requirement,
                             topic, state, data_type, manual_verification, rag_allowed,
                             structured_db_required, replacement_required, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(source_id) DO UPDATE SET
                                authority = excluded.authority,
                                source_name = excluded.source_name,
                                official_url = excluded.official_url,
                                jurisdiction = excluded.jurisdiction,
                                source_type = excluded.source_type,
                                authority_tier = excluded.authority_tier,
                                monitoring_frequency_days = excluded.monitoring_frequency_days,
                                last_checked = excluded.last_checked,
                                last_changed = excluded.last_changed,
                                current_version_id = excluded.current_version_id,
                                status = excluded.status,
                                scheme_id = excluded.scheme_id,
                                scheme_name = excluded.scheme_name,
                                official_source_name = excluded.official_source_name,
                                validation_status = excluded.validation_status,
                                monitoring_frequency = excluded.monitoring_frequency,
                                department = excluded.department,
                                document_title = excluded.document_title,
                                document_type = excluded.document_type,
                                document_number = excluded.document_number,
                                publication_date = excluded.publication_date,
                                effective_from = excluded.effective_from,
                                effective_until = excluded.effective_until,
                                dynamic_flag = excluded.dynamic_flag,
                                rag_eligibility = excluded.rag_eligibility,
                                structured_data_requirement = excluded.structured_data_requirement,
                                topic = excluded.topic,
                                state = excluded.state,
                                data_type = excluded.data_type,
                                manual_verification = excluded.manual_verification,
                                rag_allowed = excluded.rag_allowed,
                                structured_db_required = excluded.structured_db_required,
                                replacement_required = excluded.replacement_required,
                                notes = excluded.notes""",
            (source.source_id, source.authority, source.source_name, source.official_url,
             source.jurisdiction, source.source_type, source.authority_tier,
             source.monitoring_frequency_days, _timestamp(source.last_checked),
               _timestamp(source.last_changed), source.current_version_id, source.status,
               source.scheme_id, source.scheme_name, source.official_source_name,
               source.validation_status, source.monitoring_frequency, source.department,
               source.document_title, source.document_type, source.document_number,
               _timestamp(source.publication_date), _timestamp(source.effective_from),
               _timestamp(source.effective_until), int(source.dynamic_flag),
               source.rag_eligibility, source.structured_data_requirement, source.topic,
               source.state, source.data_type, source.manual_verification, int(source.rag_allowed),
               int(source.structured_db_required), source.replacement_required, source.notes),
        )
        self.connection.commit()

    def add_version(self, version: SourceVersion) -> None:
        self.connection.execute(
            "UPDATE source_versions SET status = 'superseded' WHERE source_id = ? AND status = 'current'",
            (version.source_id,),
        )
        self.connection.execute(
            """INSERT INTO source_versions
            (version_id, source_id, document_hash, retrieved_at, published_at,
             effective_from, effective_until, status, change_summary, validation_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (version.version_id, version.source_id, version.document_hash,
             _timestamp(version.retrieved_at), _timestamp(version.published_at),
             _timestamp(version.effective_from), _timestamp(version.effective_until),
             version.status, version.change_summary, version.validation_status),
        )
        self.connection.execute(
            "UPDATE source_registry SET current_version_id = ?, last_checked = ? WHERE source_id = ?",
            (version.version_id, _timestamp(version.retrieved_at), version.source_id),
        )
        self.connection.commit()

    def record_validation(self, validation: SourceValidation) -> None:
        """Record an auditable decision and update the source/version gate."""
        if validation.validation_status == ValidationStatus.VERIFIED.value:
            if not validation.official_source_url or not validation.validated_by:
                raise ValueError("Verified sources require an official URL and validator")
            if not validation.validated_at:
                raise ValueError("Verified sources require a validation timestamp")

        source = self.connection.execute(
            "SELECT source_id FROM source_registry WHERE source_id = ?",
            (validation.source_id,),
        ).fetchone()
        if not source:
            raise ValueError(f"Unknown source_id: {validation.source_id}")

        self.connection.execute(
            """INSERT INTO source_validations
            (validation_id, source_id, version_id, scheme_id, validation_status,
             validated_by, validation_method, validated_at, official_source_url,
             document_reference, validation_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (validation.validation_id, validation.source_id, validation.version_id,
             validation.scheme_id, validation.validation_status, validation.validated_by,
             validation.validation_method, _timestamp(validation.validated_at),
             validation.official_source_url, validation.document_reference,
             validation.validation_notes),
        )
        self.connection.execute(
            """UPDATE source_registry
               SET validation_status = ?,
                   official_url = COALESCE(NULLIF(?, ''), official_url),
                   last_checked = COALESCE(?, last_checked)
               WHERE source_id = ?""",
            (validation.validation_status, validation.official_source_url,
             _timestamp(validation.validated_at), validation.source_id),
        )
        version_status = {
            ValidationStatus.VERIFIED.value: "validated",
            ValidationStatus.REJECTED.value: "rejected",
        }.get(validation.validation_status, "pending")
        if validation.version_id:
            self.connection.execute(
                "UPDATE source_versions SET validation_status = ? WHERE version_id = ? AND source_id = ?",
                (version_status, validation.version_id, validation.source_id),
            )
        self.connection.commit()

    def validation_report(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Return registry rows grouped by usability and validation/freshness state."""
        reference_time = now or utc_now()
        rows = self.connection.execute(
            """SELECT s.*, v.version_id, v.effective_from, v.effective_until,
                      v.retrieved_at, v.status AS version_status,
                      v.validation_status AS version_validation_status
               FROM source_registry s
               LEFT JOIN source_versions v ON v.version_id = s.current_version_id
               ORDER BY COALESCE(s.scheme_name, s.source_name)"""
        ).fetchall()
        report: list[dict[str, Any]] = []
        for row in rows:
            freshness = freshness_status(
                last_checked=parse_datetime(row["last_checked"]),
                last_changed=parse_datetime(row["last_changed"]),
                monitoring_frequency_days=row["monitoring_frequency_days"],
                version_status=row["version_status"] or "superseded",
                source_status=row["status"],
                now=reference_time,
            )
            missing_metadata = [
                field for field, value in {
                    "authority": row["authority"],
                    "official_url": row["official_url"],
                    "jurisdiction": row["jurisdiction"],
                    "current_version_id": row["current_version_id"],
                }.items() if not value or not str(value).strip()
            ]
            usable = (
                row["validation_status"] == ValidationStatus.VERIFIED.value
                and row["version_validation_status"] == "validated"
                and row["authority_tier"] <= 2
                and freshness not in {
                    FreshnessStatus.STALE, FreshnessStatus.CHANGE_DETECTED,
                    FreshnessStatus.SUPERSEDED,
                }
                and not missing_metadata
            )
            if usable:
                classification = "AUTHORITATIVE_USABLE"
            elif row["validation_status"] == ValidationStatus.PENDING.value:
                classification = "VALIDATION_PENDING"
            elif freshness == FreshnessStatus.STALE:
                classification = "STALE"
            elif row["version_status"] in {"superseded", "withdrawn"} or \
                    row["validation_status"] == ValidationStatus.SUPERSEDED.value:
                classification = "SUPERSEDED"
            elif missing_metadata:
                classification = "MISSING_METADATA"
            else:
                classification = row["validation_status"]
            report.append({
                "scheme": row["scheme_name"] or row["source_name"],
                "source": row["official_source_name"] or row["source_name"],
                "authority_tier": row["authority_tier"],
                "official_url": row["official_url"] or None,
                "current_version": row["version_id"],
                "effective_date": row["effective_from"],
                "last_verified": row["last_checked"],
                "freshness": freshness.value,
                "validation_status": row["validation_status"],
                "classification": classification,
                "missing_metadata": missing_metadata,
            })
        return report

    def add_document(self, document: KnowledgeDocument) -> None:
        self.connection.execute(
            """INSERT INTO knowledge_documents
            (document_id, version_id, scheme_id, title, document_type, source_authority,
             jurisdiction, effective_date, content_hash, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (document.document_id, document.version_id, document.scheme_id, document.title,
             document.document_type, document.source_authority, document.jurisdiction,
             _timestamp(document.effective_date), document.content_hash, document.status),
        )
        self.connection.commit()

    def add_chunks(self, chunks: Iterable[KnowledgeChunk]) -> None:
        self.connection.executemany(
            """INSERT INTO knowledge_chunks
            (chunk_id, document_id, text, section, page, metadata, embedding_model, embedding_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(chunk.chunk_id, chunk.document_id, chunk.text, chunk.section, chunk.page,
              json.dumps(chunk.metadata), chunk.embedding_model, chunk.embedding_version)
             for chunk in chunks],
        )
        self.connection.commit()

    def retrieve_current(
        self,
        scheme_id: str,
        *,
        limit: int = 5,
        now: datetime | None = None,
    ) -> RetrievalResult:
        """Return only current, validated, effective evidence from authoritative sources."""
        reference_time = now or utc_now()
        rows = self.connection.execute(
            """SELECT c.*, d.document_id, d.version_id, d.scheme_id, d.title,
                      d.document_type, d.source_authority, d.jurisdiction,
                      d.effective_date, d.content_hash, d.status AS document_status,
                      v.source_id, v.document_hash, v.retrieved_at, v.published_at,
                      v.effective_from, v.effective_until, v.status AS version_status,
                      v.change_summary, v.validation_status,
                      s.authority, s.source_name, s.official_url, s.source_type,
                      s.authority_tier, s.monitoring_frequency_days, s.last_checked,
                      s.last_changed, s.status AS source_status
               FROM knowledge_chunks c
               JOIN knowledge_documents d ON d.document_id = c.document_id
               JOIN source_versions v ON v.version_id = d.version_id
               JOIN source_registry s ON s.source_id = v.source_id
               WHERE d.scheme_id = ?
                 AND s.status = 'active'
                 AND s.authority_tier <= 2
                 AND s.validation_status = 'VERIFIED'
                 AND v.status = 'current'
                 AND v.validation_status = 'validated'
                 AND d.status = 'current'
                 AND (v.effective_from IS NULL OR v.effective_from <= ?)
                 AND (v.effective_until IS NULL OR v.effective_until >= ?)
               ORDER BY s.authority_tier ASC, v.retrieved_at DESC
               LIMIT ?""",
            (scheme_id, _timestamp(reference_time), _timestamp(reference_time), limit),
        ).fetchall()

        evidence: list[RetrievalEvidence] = []
        for row in rows:
            status = freshness_status(
                last_checked=parse_datetime(row["last_checked"]),
                last_changed=parse_datetime(row["last_changed"]),
                monitoring_frequency_days=row["monitoring_frequency_days"],
                version_status=row["version_status"],
                source_status=row["source_status"],
                now=reference_time,
            )
            if status in {FreshnessStatus.STALE, FreshnessStatus.CHANGE_DETECTED,
                          FreshnessStatus.SUPERSEDED}:
                continue
            evidence.append(self._evidence_from_row(row, status))

        return RetrievalResult(tuple(evidence), insufficient_current_evidence=not evidence)

    @staticmethod
    def _evidence_from_row(row: sqlite3.Row, status: FreshnessStatus) -> RetrievalEvidence:
        chunk = KnowledgeChunk(
            chunk_id=row["chunk_id"], document_id=row["document_id"], text=row["text"],
            section=row["section"], page=row["page"], metadata=json.loads(row["metadata"]),
            embedding_model=row["embedding_model"], embedding_version=row["embedding_version"],
        )
        document = KnowledgeDocument(
            document_id=row["document_id"], version_id=row["version_id"], scheme_id=row["scheme_id"],
            title=row["title"], document_type=row["document_type"],
            source_authority=row["source_authority"], jurisdiction=row["jurisdiction"],
            effective_date=parse_datetime(row["effective_date"]), content_hash=row["content_hash"],
            status=row["document_status"],
        )
        version = SourceVersion(
            version_id=row["version_id"], source_id=row["source_id"], document_hash=row["document_hash"],
            retrieved_at=parse_datetime(row["retrieved_at"]), published_at=parse_datetime(row["published_at"]),
            effective_from=parse_datetime(row["effective_from"]), effective_until=parse_datetime(row["effective_until"]),
            status=row["version_status"], change_summary=row["change_summary"],
            validation_status=row["validation_status"],
        )
        source = SourceRegistry(
            source_id=row["source_id"], authority=row["authority"], source_name=row["source_name"],
            official_url=row["official_url"], jurisdiction=row["jurisdiction"], source_type=row["source_type"],
            authority_tier=row["authority_tier"], monitoring_frequency_days=row["monitoring_frequency_days"],
            last_checked=parse_datetime(row["last_checked"]), last_changed=parse_datetime(row["last_changed"]),
            current_version_id=row["version_id"], status=row["source_status"],
        )
        return RetrievalEvidence(chunk, document, version, source, status, confidence=1.0 / source.authority_tier)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
