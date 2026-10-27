from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import KnowledgeChunk, KnowledgeDocument, SourceRegistry, SourceVersion
from .repository import KnowledgeRepository

INITIAL_TOPICS = (
    ("pm_kisan", "PM-KISAN"),
    ("pmfby", "PMFBY"),
    ("kcc", "Kisan Credit Card (KCC)"),
    ("namo_shetkari", "Namo Shetkari"),
    ("msp_prices", "Minimum Support Price (MSP)"),
    ("loan_restructuring", "Loan restructuring"),
    ("drought_relief", "Drought relief"),
    ("agricultural_subsidies", "Agricultural subsidies"),
    ("helpline_numbers", "Helpline information"),
    ("maharashtra_districts_risk", "District-wise risk information"),
    ("distress_scenarios", "Distress guidance"),
    ("documents_checklist", "Required documents"),
    ("where_to_go", "Where-to-go guidance"),
    ("crop_risk_profile", "Crop risk and scheme profile"),
)


def ensure_initial_topics(repository: KnowledgeRepository) -> None:
    """Create pending registry placeholders without fabricating sources or URLs."""
    for scheme_id, scheme_name in INITIAL_TOPICS:
        source_id = f"topic_{scheme_id}"
        exists = repository.connection.execute(
            "SELECT 1 FROM source_registry WHERE scheme_id = ?", (scheme_id,)
        ).fetchone()
        if exists:
            continue
        repository.register_source(SourceRegistry(
            source_id=source_id,
            authority="Not yet verified",
            source_name=scheme_name,
            official_url="",
            jurisdiction="Maharashtra / India",
            source_type="unverified_topic",
            authority_tier=3,
            monitoring_frequency_days=30,
            last_checked=None,
            last_changed=None,
            current_version_id=None,
            status="active",
            scheme_id=scheme_id,
            scheme_name=scheme_name,
            official_source_name="Not yet identified",
            validation_status="PENDING",
            monitoring_frequency="30 days",
        ))

_DATE_PATTERN = re.compile(r"LAST VERIFIED:\s*(.+)", re.IGNORECASE)
_SOURCE_PATTERN = re.compile(r"SOURCE:\s*(\S+)", re.IGNORECASE)
_TITLE_PATTERN = re.compile(r"SCHEME NAME:\s*(.+)", re.IGNORECASE)


def _parse_verified_date(text: str) -> datetime | None:
    match = _DATE_PATTERN.search(text)
    if not match:
        return None
    for date_format in ("%B %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(match.group(1).strip(), date_format).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def import_legacy_schemes(
    repository: KnowledgeRepository,
    schemes_dir: str | Path,
    *,
    retrieved_at: datetime | None = None,
) -> int:
    """Register existing snapshots without treating them as authoritative evidence.

    These files remain available for migration and offline development. They are tier 3,
    validation-pending snapshots until an authoritative source has been verified.
    """
    imported = 0
    for path in sorted(Path(schemes_dir).glob("*.txt")):
        content = path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source_match = _SOURCE_PATTERN.search(content)
        title_match = _TITLE_PATTERN.search(content)
        if not title_match:
            continue
        source_url = source_match.group(1) if source_match else ""
        if not source_url.startswith(("http://", "https://")):
            source_url = ""

        verified_at = _parse_verified_date(content)
        source_key = source_url or path.stem
        source_id = f"legacy_{hashlib.sha256(source_key.encode()).hexdigest()[:16]}"
        version_id = f"snapshot_{content_hash[:24]}"
        document_id = f"document_{content_hash[:24]}"
        now = retrieved_at or datetime.now(timezone.utc)
        source = SourceRegistry(
            source_id=source_id,
            authority="Unverified local snapshot",
            source_name=f"Legacy snapshot: {title_match.group(1).strip()}",
            official_url=source_url,
            jurisdiction="Maharashtra / India",
            source_type="curated_snapshot",
            authority_tier=3,
            monitoring_frequency_days=30,
            last_checked=verified_at,
            last_changed=None,
            current_version_id=version_id,
            status="active",
            scheme_id=path.stem,
            scheme_name=title_match.group(1).strip(),
            official_source_name="Unverified source reference",
            validation_status="PENDING",
            monitoring_frequency="30 days",
        )
        repository.register_source(source)
        repository.add_version(SourceVersion(
            version_id=version_id,
            source_id=source_id,
            document_hash=content_hash,
            retrieved_at=now,
            published_at=None,
            effective_from=verified_at,
            effective_until=None,
            status="current",
            change_summary="Imported from the existing local scheme snapshot.",
            validation_status="pending",
        ))
        repository.add_document(KnowledgeDocument(
            document_id=document_id,
            version_id=version_id,
            scheme_id=path.stem,
            title=title_match.group(1).strip(),
            document_type="scheme_snapshot",
            source_authority="Unverified local snapshot",
            jurisdiction="Maharashtra / India",
            effective_date=verified_at,
            content_hash=content_hash,
            status="current",
        ))
        repository.add_chunks([KnowledgeChunk(
            chunk_id=f"chunk_{content_hash[:24]}",
            document_id=document_id,
            text=content,
            section=None,
            page=None,
            metadata={"origin": "legacy_scheme_file", "validation_status": "pending"},
            embedding_model=None,
            embedding_version=None,
        )])
        imported += 1
    ensure_initial_topics(repository)
    return imported
