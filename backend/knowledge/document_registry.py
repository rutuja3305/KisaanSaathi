from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .repository import KnowledgeRepository, _timestamp

MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = MODULE_PATH.parents[1]
AUTHORITATIVE_DOCUMENTS_ROOT = MODULE_PATH.parent / "authoritative_documents"
_REQUIRED_SOURCE_FIELDS = (
    "scheme_id",
    "authority",
    "official_url",
    "document_title",
    "document_type",
    "jurisdiction",
    "authority_tier",
)


class DocumentRegistrationError(ValueError):
    pass


class DuplicateDocumentError(DocumentRegistrationError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolved_local_file(value: str | Path) -> tuple[Path, str]:
    input_path = Path(value)
    resolved = (PROJECT_ROOT / input_path).resolve() if not input_path.is_absolute() else input_path.resolve()
    root = AUTHORITATIVE_DOCUMENTS_ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise DocumentRegistrationError(
            f"Document must be inside {root}; legacy/reference files are not authoritative inputs"
        )
    if not resolved.exists() or not resolved.is_file():
        raise DocumentRegistrationError(f"Local document does not exist or is not a file: {resolved}")
    return resolved, resolved.relative_to(PROJECT_ROOT).as_posix()


def _matching_validation(
    connection: sqlite3.Connection,
    source: sqlite3.Row,
    checksum: str,
    requested_version_id: str | None,
) -> sqlite3.Row | None:
    version_id = requested_version_id or source["current_version_id"]
    if source["validation_status"] != "VERIFIED" or not version_id:
        return None
    version = connection.execute(
        """SELECT version_id FROM source_versions
           WHERE version_id = ? AND source_id = ? AND document_hash = ?
             AND status = 'current' AND validation_status = 'validated'""",
        (version_id, source["source_id"], checksum),
    ).fetchone()
    if not version:
        return None
    return connection.execute(
        """SELECT validated_by, validated_at FROM source_validations
           WHERE source_id = ? AND version_id = ? AND validation_status = 'VERIFIED'
           ORDER BY validated_at DESC LIMIT 1""",
        (source["source_id"], version_id),
    ).fetchone()


def register_document(
    repository: KnowledgeRepository,
    *,
    source_id: str,
    local_file: str | Path,
    version_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    source = repository.connection.execute(
        "SELECT * FROM source_registry WHERE source_id = ?", (source_id,)
    ).fetchone()
    if not source:
        raise DocumentRegistrationError(f"Unknown source_id: {source_id}")

    missing = [field for field in _REQUIRED_SOURCE_FIELDS if source[field] in (None, "")]
    if missing:
        raise DocumentRegistrationError(
            f"Source {source_id} is missing required registry metadata: {', '.join(missing)}"
        )

    path, relative_path = _resolved_local_file(local_file)
    checksum = sha256_file(path)
    duplicate = repository.connection.execute(
        "SELECT document_id, source_id, local_file FROM authoritative_document_manifest WHERE checksum = ?",
        (checksum,),
    ).fetchone()
    if duplicate:
        raise DuplicateDocumentError(
            f"Duplicate document checksum {checksum}: already registered as "
            f"{duplicate['document_id']} for {duplicate['source_id']} ({duplicate['local_file']})"
        )

    validation = _matching_validation(repository.connection, source, checksum, version_id)
    is_verified = validation is not None
    manifest_version_id = version_id or source["current_version_id"] or f"local-{checksum[:20]}"
    document_id = f"adoc_{uuid4().hex}"
    effective_validation_status = "VERIFIED" if is_verified else "PENDING"
    rag_allowed = bool(is_verified and source["rag_allowed"])
    registered_at = datetime.now(timezone.utc)

    repository.connection.execute(
        """INSERT INTO authoritative_document_manifest
        (document_id, source_id, version_id, scheme_id, topic, authority, department,
         official_url, document_title, document_type, document_number, publication_date,
         effective_from, effective_until, jurisdiction, authority_tier, validation_status,
         validated_by, validated_at, rag_allowed, structured_db_required, local_file,
         checksum, notes, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (document_id, source_id, manifest_version_id, source["scheme_id"], source["topic"],
         source["authority"], source["department"], source["official_url"],
         source["document_title"], source["document_type"], source["document_number"],
         source["publication_date"], source["effective_from"], source["effective_until"],
         source["jurisdiction"], source["authority_tier"], effective_validation_status,
         validation["validated_by"] if validation else None,
         validation["validated_at"] if validation else None, int(rag_allowed),
         int(source["structured_db_required"]), relative_path, checksum, notes or source["notes"],
         _timestamp(registered_at)),
    )
    repository.connection.commit()
    return {
        "document_id": document_id,
        "source_id": source_id,
        "version_id": manifest_version_id,
        "local_file": relative_path,
        "checksum": checksum,
        "validation_status": effective_validation_status,
        "rag_allowed": rag_allowed,
    }


def document_registry_report(repository: KnowledgeRepository) -> dict[str, Any]:
    connection = repository.connection
    documents = [dict(row) for row in connection.execute(
        """SELECT d.*, s.validation_status AS source_validation_status
           FROM authoritative_document_manifest d
           JOIN source_registry s ON s.source_id = d.source_id
           ORDER BY d.source_id, d.local_file"""
    ).fetchall()]
    sources_without_documents = [dict(row) for row in connection.execute(
        """SELECT s.source_id, s.scheme_id, s.topic, s.validation_status
           FROM source_registry s
           LEFT JOIN authoritative_document_manifest d ON d.source_id = s.source_id
           WHERE d.document_id IS NULL ORDER BY s.source_id"""
    ).fetchall()]
    verified_without_document = [
        source for source in sources_without_documents if source["validation_status"] == "VERIFIED"
    ]
    duplicates = [dict(row) for row in connection.execute(
        """SELECT checksum, COUNT(*) AS document_count,
                  GROUP_CONCAT(document_id) AS document_ids
           FROM authoritative_document_manifest
           WHERE checksum IS NOT NULL AND checksum <> ''
           GROUP BY checksum HAVING COUNT(*) > 1"""
    ).fetchall()]
    return {
        "registered_authoritative_documents": documents,
        "documents_without_validation": [d for d in documents if d["validation_status"] != "VERIFIED"],
        "documents_without_checksums": [d for d in documents if not d["checksum"]],
        "sources_without_documents": sources_without_documents,
        "verified_sources_without_local_document": verified_without_document,
        "pending_documents": [d for d in documents if d["validation_status"] == "PENDING"],
        "duplicate_documents": duplicates,
        "totals": {
            "registered_documents": len(documents),
            "verified_documents": sum(d["validation_status"] == "VERIFIED" for d in documents),
            "pending_documents": sum(d["validation_status"] == "PENDING" for d in documents),
            "sources_without_documents": len(sources_without_documents),
            "duplicate_checksums": len(duplicates),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Register local official documents without ingestion")
    commands = parser.add_subparsers(dest="command", required=True)
    register_parser = commands.add_parser("register", help="Register and checksum a local document")
    register_parser.add_argument("--db", required=True)
    register_parser.add_argument("--source-id", required=True)
    register_parser.add_argument("--file", required=True)
    register_parser.add_argument("--version-id")
    register_parser.add_argument("--notes")
    report_parser = commands.add_parser("report", help="Report local document registration state")
    report_parser.add_argument("--db", required=True)
    args = parser.parse_args()

    repository = KnowledgeRepository.from_path(args.db)
    try:
        if args.command == "register":
            result = register_document(
                repository,
                source_id=args.source_id,
                local_file=args.file,
                version_id=args.version_id,
                notes=args.notes,
            )
        else:
            result = document_registry_report(repository)
        print(json.dumps(result, indent=2, default=str))
    finally:
        repository.close()


if __name__ == "__main__":
    main()
