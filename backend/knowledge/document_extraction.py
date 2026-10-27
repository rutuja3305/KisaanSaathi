from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from matplotlib import text
from pypdf import PdfReader

from .document_ingestion import _json_metadata, _line_structure, has_pdf_signature, sha256_file

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
AUTHORITATIVE_ROOT = (MODULE_DIR / "authoritative_documents").resolve()
DEFAULT_DATABASE = MODULE_DIR / "knowledge.sqlite"
DEFAULT_OUTPUT_ROOT = MODULE_DIR / "extraction_output"
MIN_PAGE_CHARACTERS = 30
MIN_DOCUMENT_CHARACTERS = 200
MIN_TEXT_PAGE_RATIO = 0.70


class ExtractionError(RuntimeError):
    pass


class ChecksumMismatchError(ExtractionError):
    pass


class ManifestDocumentStore:
    """Read-only access to registered document manifest rows."""

    def __init__(self, database_path: str | Path):
        path = Path(database_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Knowledge database not found: {path}")
        self.connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row

    def list_documents(self, source_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM authoritative_document_manifest"
        params: tuple[Any, ...] = ()
        if source_id:
            query += " WHERE source_id = ?"
            params = (source_id,)
        query += " ORDER BY source_id, local_file, document_id"
        return [dict(row) for row in self.connection.execute(query, params).fetchall()]

    def close(self) -> None:
        self.connection.close()


@dataclass
class DocumentExtractionReport:
    documents_seen: int = 0
    documents_extracted: int = 0
    documents_skipped_existing_output: int = 0
    failed: int = 0
    ocr_required: int = 0
    pages: int = 0
    pages_with_text: int = 0
    pages_without_text: int = 0
    pages_failed: int = 0
    characters: int = 0
    documents: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents_seen": self.documents_seen,
            "documents_extracted": self.documents_extracted,
            "documents_skipped_existing_output": self.documents_skipped_existing_output,
            "failed": self.failed,
            "ocr_required": self.ocr_required,
            "pages": self.pages,
            "pages_with_text": self.pages_with_text,
            "pages_without_text": self.pages_without_text,
            "pages_failed": self.pages_failed,
            "characters": self.characters,
            "documents": self.documents,
        }


class DocumentExtractionService:
    def __init__(
        self,
        *,
        database_path: str | Path = DEFAULT_DATABASE,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        authoritative_root: str | Path = AUTHORITATIVE_ROOT,
        reader_factory: Callable[..., PdfReader] = PdfReader,
        store: ManifestDocumentStore | None = None,
        minimum_page_characters: int = MIN_PAGE_CHARACTERS,
        minimum_document_characters: int = MIN_DOCUMENT_CHARACTERS,
        minimum_text_page_ratio: float = MIN_TEXT_PAGE_RATIO,
    ):
        self.output_root = Path(output_root).resolve()
        self.authoritative_root = Path(authoritative_root).resolve()
        self.reader_factory = reader_factory
        self.store = store or ManifestDocumentStore(database_path)
        self._owns_store = store is None
        self.minimum_page_characters = minimum_page_characters
        self.minimum_document_characters = minimum_document_characters
        self.minimum_text_page_ratio = minimum_text_page_ratio

    def close(self) -> None:
        if self._owns_store:
            self.store.close()

    def extract_all(self, *, dry_run: bool = False) -> DocumentExtractionReport:
        return self._extract(self.store.list_documents(), dry_run=dry_run)

    def extract_source(self, source_id: str, *, dry_run: bool = False) -> DocumentExtractionReport:
        rows = self.store.list_documents(source_id)
        if not rows:
            return DocumentExtractionReport(documents_seen=0, documents=[{
                "source_id": source_id,
                "extraction_status": "NOT_REGISTERED",
                "error": "No authoritative_document_manifest row exists for this source_id.",
            }])
        return self._extract(rows, dry_run=dry_run)

    def _extract(self, rows: list[dict[str, Any]], *, dry_run: bool) -> DocumentExtractionReport:
        report = DocumentExtractionReport(documents_seen=len(rows))
        for row in rows:
            if dry_run:
                report.documents.append(self._dry_run_record(row))
                continue
            try:
                record, outcome = self._extract_one(row)
            except Exception as exc:
                record = self._failure_record(row, exc)
                outcome = "FAILED"
            report.documents.append(record)
            if outcome == "EXTRACTED":
                report.documents_extracted += 1
            elif outcome == "SKIPPED_EXISTING":
                report.documents_skipped_existing_output += 1
            elif outcome == "FAILED":
                report.failed += 1
            if record.get("quality_status") == "OCR_REQUIRED":
                report.ocr_required += 1
            pages = record.get("pages", [])
            report.pages += len(pages)
            report.pages_with_text += sum(bool(page.get("text", "").strip()) for page in pages)
            report.pages_without_text += sum(page.get("extraction_status") == "EMPTY" for page in pages)
            report.pages_failed += sum(page.get("extraction_status") == "EXTRACTION_FAILED" for page in pages)
            report.characters += sum(page.get("character_count", 0) for page in pages)
        return report

    def _dry_run_record(self, row: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_manifest_path(row.get("local_file"))
        exists = path.is_file()
        checksum = sha256_file(path) if exists else None
        return {
            "source_id": row["source_id"],
            "document_id": row["document_id"],
            "local_file": row.get("local_file"),
            "absolute_source_path": str(path),
            "exists": exists,
            "manifest_checksum": row.get("checksum"),
            "actual_checksum": checksum,
            "checksum_matches": bool(checksum and row.get("checksum") == checksum),
            "pdf_signature_valid": has_pdf_signature(path) if exists else False,
            "would_extract": bool(exists and checksum and row.get("checksum") == checksum and has_pdf_signature(path)),
            "dry_run": True,
        }

    def _resolve_manifest_path(self, local_file: str | None) -> Path:
        if not local_file:
            raise ExtractionError("Manifest local_file is empty")
        stored = Path(local_file)
        path = (PROJECT_ROOT / stored).resolve() if not stored.is_absolute() else stored.resolve()
        if not path.is_relative_to(self.authoritative_root):
            raise ExtractionError(f"Manifest file is outside authoritative_documents: {path}")
        return path

    def _extract_one(self, row: dict[str, Any]) -> tuple[dict[str, Any], str]:
        path = self._resolve_manifest_path(row.get("local_file"))
        source_id = row["source_id"]
        manifest_id = row["document_id"]
        expected_checksum = row.get("checksum")
        record: dict[str, Any] = {
            "source_id": source_id,
            "document_id": manifest_id,
            "manifest_id": manifest_id,
            "version_id": row.get("version_id"),
            "filename": path.name,
            "local_file": row.get("local_file"),
            "absolute_source_path": str(path),
            "sha256": expected_checksum,
            "file_size_bytes": None,
            "file_type": path.suffix.lower(),
            "title": row.get("document_title"),
            "document_metadata": {},
            "manifest_metadata": row,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_status": "PENDING",
            "quality_status": "FAILED",
            "quality_statistics": {},
            "extraction_warnings": [],
            "pages": [],
        }
        if not path.is_file():
            record["extraction_status"] = "FAILED"
            record["error"] = f"Manifest file does not exist: {path}"
            return record, "FAILED"
        record["file_size_bytes"] = path.stat().st_size
        if not expected_checksum:
            record["extraction_status"] = "FAILED"
            record["error"] = "Manifest checksum is missing; refusing extraction without integrity verification."
            return record, "FAILED"
        actual_checksum = sha256_file(path)
        record["actual_sha256"] = actual_checksum
        if actual_checksum.lower() != str(expected_checksum).lower():
            raise ChecksumMismatchError(
                f"Checksum mismatch for {path}: manifest={expected_checksum}, actual={actual_checksum}"
            )
        if path.suffix.lower() != ".pdf" or not has_pdf_signature(path):
            record["extraction_status"] = "FAILED"
            record["error"] = "Manifest file is not a valid PDF signature/file type."
            return record, "FAILED"

        reader = self.reader_factory(str(path), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("Encrypted PDF cannot be opened with an empty password")
        record["document_metadata"] = _json_metadata(reader)
        record["title"] = record["document_metadata"].get("Title") or row.get("document_title") or path.stem
        record["page_count"] = len(reader.pages)
        for page_number, pdf_page in enumerate(reader.pages, start=1):
            try:
                text = pdf_page.extract_text() or ""
                page_record = self._page_record(row, path, page_number, text)
            except Exception as exc:
                page_record = self._page_record(
                    row, path, page_number, "", extraction_status="EXTRACTION_FAILED",
                    error=f"{type(exc).__name__}: {exc}",
                )
            record["pages"].append(page_record)

        self._quality_assessment(record)
        record["extraction_status"] = self._document_status(record)
        output_path = self._output_path(row, actual_checksum)
        record["intermediate_output_path"] = str(output_path)
        output_status = self._write_exclusive_or_reuse(output_path, record, actual_checksum)
        record["output_status"] = output_status
        if output_status == "OUTPUT_CONFLICT":
            record["extraction_status"] = "OUTPUT_CONFLICT"
            record["extraction_error"] = "Existing intermediate output has different manifest/checksum provenance; it was not overwritten."
            return record, "FAILED"
        if output_status == "OUTPUT_EXISTS_UNCHANGED":
            return record, "SKIPPED_EXISTING"
        return record, "EXTRACTED"

    @staticmethod
    def _page_record(
        row: dict[str, Any],
        path: Path,
        page_number: int,
        text: str,
        *,
        extraction_status: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        structure = _line_structure(text)
        headings = structure["headings"]
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text.strip()) if part.strip()]
        status = extraction_status or (
            "EMPTY" if not text.strip() else
            "LOW_TEXT" if len(text.strip()) < MIN_PAGE_CHARACTERS else "SUCCESS"
        )
        page: dict[str, Any] = {
            "source_id": row["source_id"],
            "document_id": row["document_id"],
            "filename": path.name,
            "local_file": row.get("local_file"),
            "sha256": row.get("checksum"),
            "page_number": page_number,
            "section_heading": headings[0]["text"] if headings else None,
            "text": text,
            "paragraphs": paragraphs,
            "character_count": len(text),
            "extraction_status": status,
            "structure": structure,
        }
        if error:
            page["error"] = error
        return page

    def _quality_assessment(self, record: dict[str, Any]) -> None:
        pages = record["pages"]
        total_pages = len(pages)
        text_pages = [p for p in pages if p["text"].strip()]
        total_characters = sum(p["character_count"] for p in pages)
        ratio = (len(text_pages) / total_pages) if total_pages else 0.0
        warnings: list[str] = []
        if total_pages == 0:
            quality = "FAILED"
            warnings.append("PDF has no extractable pages.")
        elif not text_pages or total_characters == 0:
            quality = "OCR_REQUIRED"
            warnings.append("No extractable text found; document may be scanned/image-only. OCR is not performed by this pipeline.")
        elif total_characters < self.minimum_document_characters or ratio < self.minimum_text_page_ratio:
            quality = "LOW_TEXT"
            warnings.append("Extracted text volume or text-bearing page ratio is below the quality threshold.")
        else:
            quality = "GOOD"

        low_text_pages = [p["page_number"] for p in pages if p["extraction_status"] == "LOW_TEXT"]
        empty_pages = [p["page_number"] for p in pages if p["extraction_status"] == "EMPTY"]
        failed_pages = [p["page_number"] for p in pages if p["extraction_status"] == "EXTRACTION_FAILED"]
        if low_text_pages:
            warnings.append(f"Very little text on pages: {low_text_pages}")
        if empty_pages:
            warnings.append(f"No text extracted from pages: {empty_pages}")
        if failed_pages:
            warnings.append(f"Page extraction failed for pages: {failed_pages}")
        warnings.extend(self._repeated_header_footer_warnings(pages))
        record["quality_status"] = quality
        record["quality_statistics"] = {
            "page_count": total_pages,
            "pages_with_text": len(text_pages),
            "pages_without_text": len(empty_pages),
            "pages_failed": len(failed_pages),
            "text_page_ratio": ratio,
            "total_characters": total_characters,
            "minimum_page_characters": self.minimum_page_characters,
            "minimum_document_characters": self.minimum_document_characters,
            "minimum_text_page_ratio": self.minimum_text_page_ratio,
        }
        record["extraction_warnings"] = warnings

    @staticmethod
    def _repeated_header_footer_warnings(pages: list[dict[str, Any]]) -> list[str]:
        if len(pages) < 3:
            return []
        top_lines: Counter[str] = Counter()
        bottom_lines: Counter[str] = Counter()
        for page in pages:
            lines = [line.strip() for line in page.get("text", "").splitlines() if line.strip()]
            if lines:
                top_lines[lines[0]] += 1
                bottom_lines[lines[-1]] += 1
        threshold = max(3, int(len(pages) * 0.4 + 0.999))
        warnings: list[str] = []
        warnings.extend(f"Repeated page header candidate: {line!r}" for line, count in top_lines.items() if count >= threshold)
        warnings.extend(f"Repeated page footer candidate: {line!r}" for line, count in bottom_lines.items() if count >= threshold)
        return warnings

    @staticmethod
    def _document_status(record: dict[str, Any]) -> str:
        pages = record["pages"]
        if not pages:
            return "FAILED"
        if any(p["extraction_status"] == "EXTRACTION_FAILED" for p in pages):
            return "PARTIAL_FAILURE"
        if any(p["extraction_status"] in {"EMPTY", "LOW_TEXT"} for p in pages):
            return "PARTIAL"
        return "SUCCESS"

    def _output_path(self, row: dict[str, Any], checksum: str) -> Path:
        source_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", row["source_id"])
        document_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", row["document_id"])
        return self.output_root / source_id / f"{document_id}.{checksum[:16]}.json"

    @staticmethod
    def _write_exclusive_or_reuse(path: Path, record: dict[str, Any], checksum: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = (json.dumps(record, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
        try:
            with path.open("xb") as destination:
                destination.write(serialized)
            return "WRITTEN"
        except FileExistsError:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("source_id") == record.get("source_id") and \
                        existing.get("document_id") == record.get("document_id") and \
                        existing.get("sha256") == checksum:
                    return "OUTPUT_EXISTS_UNCHANGED"
            except Exception:
                pass
            return "OUTPUT_CONFLICT"

    def _failure_record(self, row: dict[str, Any], error: Exception) -> dict[str, Any]:
        return {
            "source_id": row.get("source_id"),
            "document_id": row.get("document_id"),
            "manifest_id": row.get("document_id"),
            "filename": Path(row.get("local_file") or "").name,
            "local_file": row.get("local_file"),
            "sha256": row.get("checksum"),
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_status": "FAILED",
            "quality_status": "FAILED",
            "extraction_warnings": [],
            "pages": [],
            "error": f"{type(error).__name__}: {error}",
        }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    service = DocumentExtractionService(database_path=args.db, output_root=args.output_dir)
    try:
        if args.command == "extract":
            report = service.extract_source(args.source_id, dry_run=args.dry_run)
        else:
            report = service.extract_all(dry_run=args.dry_run)
        return report.to_dict()
    finally:
        service.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract registered authoritative PDFs to page-aware JSON only")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("extract", "extract-all"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--db", default=str(DEFAULT_DATABASE))
        subparser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT))
        subparser.add_argument("--dry-run", action="store_true", help="Validate manifest paths/checksums without PDF extraction or output writes")
        if command == "extract":
            subparser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    print(json.dumps(_run(args), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
