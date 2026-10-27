from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class FreshnessStatus(StrEnum):
    VERIFIED = "VERIFIED"
    REVIEW_DUE = "REVIEW_DUE"
    STALE = "STALE"
    CHANGE_DETECTED = "CHANGE_DETECTED"
    SUPERSEDED = "SUPERSEDED"


class ValidationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class SourceRegistry:
    source_id: str
    authority: str
    source_name: str
    official_url: str
    jurisdiction: str
    source_type: str
    authority_tier: int
    monitoring_frequency_days: int
    last_checked: datetime | None
    last_changed: datetime | None
    current_version_id: str | None
    status: str
    scheme_id: str | None = None
    scheme_name: str | None = None
    official_source_name: str | None = None
    validation_status: str = ValidationStatus.PENDING.value
    monitoring_frequency: str | None = None
    department: str | None = None
    document_title: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    publication_date: datetime | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    dynamic_flag: bool = True
    rag_eligibility: str = "NOT_ELIGIBLE"
    structured_data_requirement: str | None = None
    topic: str | None = None
    state: str | None = None
    data_type: str | None = None
    manual_verification: str = "NO"
    rag_allowed: bool = False
    structured_db_required: bool = False
    replacement_required: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class SourceValidation:
    validation_id: str
    source_id: str
    version_id: str | None
    scheme_id: str
    validation_status: str
    validated_by: str | None
    validation_method: str | None
    validated_at: datetime | None
    official_source_url: str | None
    document_reference: str | None
    validation_notes: str


@dataclass(frozen=True)
class AuthoritativeDocument:
    document_id: str
    source_id: str
    version_id: str
    scheme_id: str
    topic: str | None
    authority: str
    department: str | None
    official_url: str
    document_title: str
    document_type: str
    document_number: str | None
    publication_date: datetime | None
    effective_from: datetime | None
    effective_until: datetime | None
    jurisdiction: str
    authority_tier: int
    validation_status: str
    validated_by: str | None
    validated_at: datetime | None
    rag_allowed: bool
    structured_db_required: bool
    local_file: str
    checksum: str | None
    notes: str | None


@dataclass(frozen=True)
class SourceVersion:
    version_id: str
    source_id: str
    document_hash: str
    retrieved_at: datetime
    published_at: datetime | None
    effective_from: datetime | None
    effective_until: datetime | None
    status: str
    change_summary: str
    validation_status: str


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    version_id: str
    scheme_id: str
    title: str
    document_type: str
    source_authority: str
    jurisdiction: str
    effective_date: datetime | None
    content_hash: str
    status: str


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    text: str
    section: str | None
    page: int | None
    metadata: dict[str, Any]
    embedding_model: str | None
    embedding_version: str | None


@dataclass(frozen=True)
class RetrievalEvidence:
    chunk: KnowledgeChunk
    document: KnowledgeDocument
    version: SourceVersion
    source: SourceRegistry
    freshness_status: FreshnessStatus
    confidence: float

    @property
    def effective_date(self) -> datetime | None:
        return self.document.effective_date or self.version.effective_from

    @property
    def last_verified_date(self) -> datetime:
        return self.version.retrieved_at

    def provenance(self) -> dict[str, Any]:
        return {
            "source": self.source.official_url,
            "authority": self.source.authority,
            "document": self.document.title,
            "version": self.version.version_id,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "last_verified_date": self.last_verified_date.isoformat(),
            "confidence": self.confidence,
            "freshness_status": self.freshness_status.value,
        }


@dataclass(frozen=True)
class RetrievalResult:
    evidence: tuple[RetrievalEvidence, ...]
    insufficient_current_evidence: bool

    @property
    def context(self) -> str:
        return "\n\n".join(item.chunk.text for item in self.evidence)

    def response_metadata(self) -> dict[str, Any]:
        return {
            "insufficient_current_evidence": self.insufficient_current_evidence,
            "evidence": [item.provenance() for item in self.evidence],
        }
