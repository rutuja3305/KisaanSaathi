from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pypdf import PdfReader

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
DEFAULT_DOCUMENTS_ROOT = MODULE_DIR / "authoritative_documents"
DEFAULT_OUTPUT_ROOT = MODULE_DIR / "ingestion_output"
DEFAULT_DATABASE = MODULE_DIR / "knowledge.sqlite"

FOLDER_SOURCE_IDS = {
    "pm_kisan": "pm_kisan_official",
    "pmfby": "pmfby_official",
    "kcc": "kcc_rbi_gov",
    "loan_restructuring": "rbi_natural_calamity_relief",
    "namo_shetkari": "namo_shetkari_mahadbt",
    "drought_relief": "maharashtra_drought_relief",
    "mahadbt_agriculture": "mahadbt_agriculture_schemes",
    "msp": "msp_official",
    "helplines": "official_helplines",
    "application_channels": "official_application_channels",
    "crop_risk": "crop_risk_reference",
    "district_risk": "district_risk_reference",
    "scheme_document_requirements": "scheme_document_requirements",
}

_NUMBERED_SECTION = re.compile(r"^\s*(?:\d+(?:\.\d+)*(?:[.)])?|[A-Z][.)])\s+\S")
_BULLET = re.compile(r"^\s*(?:[-*\u2022\u25cf\u25aa\u2013\u2014]|\d+[.)])\s+\S")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def has_pdf_signature(path: Path) -> bool:
    try:
        with path.open("rb") as source:
            return source.read(5) == b"%PDF-"
    except OSError:
        return False


def _sqlite_readonly_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def load_source_catalog(database_path: str | Path = DEFAULT_DATABASE) -> dict[str, dict[str, Any]]:
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(f"Source registry database not found: {path}")
    connection = sqlite3.connect(_sqlite_readonly_uri(path), uri=True)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM source_registry").fetchall()
        return {row["source_id"]: dict(row) for row in rows}
    finally:
        connection.close()


def _json_metadata(reader: PdfReader) -> dict[str, Any]:
    metadata = reader.metadata
    if metadata is None:
        return {}
    result: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key).lstrip("/")
        if value is not None:
            result[normalized_key] = str(value)
    return result


def _line_structure(text: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in text.splitlines()]
    nonempty = [(index + 1, line.strip()) for index, line in enumerate(lines) if line.strip()]
    headings: list[dict[str, Any]] = []
    numbered_sections: list[dict[str, Any]] = []
    list_items: list[dict[str, Any]] = []
    for line_number, line in nonempty:
        if _NUMBERED_SECTION.match(line):
            numbered_sections.append({"line_number": line_number, "text": line})
        if _BULLET.match(line):
            list_items.append({"line_number": line_number, "text": line})
        is_upper_heading = len(line) <= 140 and any(char.isalpha() for char in line) and line == line.upper()
        is_short_heading = (
            len(line) <= 100
            and not re.search(r"[.!?;:]$", line)
            and not _BULLET.match(line)
            and len(line.split()) <= 12
            and line[:1].isupper()
        )
        if is_upper_heading or is_short_heading:
            headings.append({"line_number": line_number, "text": line})

    table_candidates: list[dict[str, Any]] = []
    current_rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        cells = [cell.strip() for cell in re.split(r"\t+|\s{2,}", stripped) if cell.strip()]
        if stripped and len(cells) >= 2:
            current_rows.append({"line_number": line_number, "cells": cells, "text": stripped})
        else:
            if len(current_rows) >= 2:
                table_candidates.append({"start_line": current_rows[0]["line_number"], "rows": current_rows})
            current_rows = []
    if len(current_rows) >= 2:
        table_candidates.append({"start_line": current_rows[0]["line_number"], "rows": current_rows})

    list_boundaries: list[dict[str, int]] = []
    if list_items:
        start = previous = list_items[0]["line_number"]
        for item in list_items[1:]:
            line_number = item["line_number"]
            if line_number > previous + 1:
                list_boundaries.append({"start_line": start, "end_line": previous})
                start = line_number
            previous = line_number
        list_boundaries.append({"start_line": start, "end_line": previous})

    return {
        "headings": headings,
        "section_titles": [item["text"] for item in headings],
        "numbered_sections": numbered_sections,
        "list_items": list_items,
        "list_boundaries": list_boundaries,
        "table_candidates": table_candidates,
    }


@dataclass
class IngestionReport:
    documents_discovered: int = 0
    documents_processed: int = 0
    documents_failed: int = 0
    documents_skipped_existing_output: int = 0
    pages_total: int = 0
    pages_successful: int = 0
    pages_empty: int = 0
    pages_failed: int = 0
    documents: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents_discovered": self.documents_discovered,
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "documents_skipped_existing_output": self.documents_skipped_existing_output,
            "pages_total": self.pages_total,
            "pages_successful": self.pages_successful,
            "pages_empty": self.pages_empty,
            "pages_failed": self.pages_failed,
            "documents": self.documents,
        }


class DocumentIngestionPipeline:
    def __init__(
        self,
        *,
        documents_root: str | Path = DEFAULT_DOCUMENTS_ROOT,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        source_catalog: dict[str, dict[str, Any]] | None = None,
        reader_factory: Callable[..., PdfReader] = PdfReader,
    ):
        self.documents_root = Path(documents_root).resolve()
        self.output_root = Path(output_root).resolve()
        self.source_catalog = source_catalog or {}
        self.reader_factory = reader_factory

    def discover(self) -> list[dict[str, Any]]:
        if not self.documents_root.is_dir():
            return []
        discovered: list[dict[str, Any]] = []
        for path in sorted(self.documents_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() != ".pdf":
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(self.documents_root):
                continue
            relative = resolved.relative_to(PROJECT_ROOT) if resolved.is_relative_to(PROJECT_ROOT) else resolved.relative_to(self.documents_root)
            relative_path = relative.as_posix()
            topic_folder = path.relative_to(self.documents_root).parts[0]
            source_id = FOLDER_SOURCE_IDS.get(topic_folder)
            source = self.source_catalog.get(source_id) if source_id else None
            if source_id and not source:
                source_id = None
            checksum = sha256_file(resolved)
            discovered.append({
                "filename": path.name,
                "absolute_source_path": str(resolved),
                "relative_source_path": relative_path,
                "relative_topic_path": path.relative_to(self.documents_root).as_posix(),
                "topic_folder": topic_folder,
                "source_id": source_id,
                "source_mapping_status": "MATCHED" if source_id and source else "UNMAPPED",
                "sha256": checksum,
                "file_type": "application/pdf",
                "extension": path.suffix.lower(),
                "file_size_bytes": resolved.stat().st_size,
                "pdf_signature_valid": has_pdf_signature(resolved),
            })
        return discovered

    def scan(self) -> IngestionReport:
        files = self.discover()
        report = IngestionReport(documents_discovered=len(files))
        report.documents = files
        return report

    def ingest(self) -> IngestionReport:
        files = self.discover()
        report = IngestionReport(documents_discovered=len(files))
        for item in files:
            record, output_status = self._ingest_one(item)
            report.documents.append(record)
            if record["extraction_status"] in {"FAILED", "UNMAPPED_SOURCE", "INVALID_PDF"} or output_status == "OUTPUT_CONFLICT":
                report.documents_failed += 1
            else:
                report.documents_processed += 1
            if output_status == "OUTPUT_EXISTS_UNCHANGED":
                report.documents_skipped_existing_output += 1
            report.pages_total += len(record["pages"])
            report.pages_successful += sum(p["extraction_status"] == "SUCCESS" for p in record["pages"])
            report.pages_empty += sum(p["extraction_status"] == "EMPTY" for p in record["pages"])
            report.pages_failed += sum(p["extraction_status"] == "EXTRACTION_FAILED" for p in record["pages"])
        return report

    def _ingest_one(self, item: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        pdf_path = Path(item["absolute_source_path"])
        source_id = item["source_id"]
        source = self.source_catalog.get(source_id) if source_id else None
        checksum = item["sha256"]
        document_id = "doc_" + hashlib.sha256(f"{source_id or 'unmapped'}:{checksum}".encode()).hexdigest()[:24]
        extracted_at = datetime.now(timezone.utc).isoformat()
        base: dict[str, Any] = {
            "source_id": source_id,
            "document_id": document_id,
            "filename": item["filename"],
            "absolute_source_path": item["absolute_source_path"],
            "relative_source_path": item["relative_source_path"],
            "relative_topic_path": item["relative_topic_path"],
            "file_type": item["file_type"],
            "file_extension": item["extension"],
            "sha256": checksum,
            "title": None,
            "title_source": None,
            "document_metadata": {},
            "source_metadata": source,
            "extraction_timestamp": extracted_at,
            "extraction_status": "PENDING",
            "pages": [],
        }
        if not source_id or not source:
            base["extraction_status"] = "UNMAPPED_SOURCE"
            base["error"] = "No existing source registry entry matches this authoritative topic folder."
            return base, None
        if not item["pdf_signature_valid"]:
            base["extraction_status"] = "INVALID_PDF"
            base["error"] = "File does not begin with a PDF signature (%PDF-)."
            return base, None

        try:
            reader = self.reader_factory(str(pdf_path), strict=False)
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValueError("Encrypted PDF cannot be opened with an empty password")
            metadata = _json_metadata(reader)
            base["document_metadata"] = metadata
            base["title"] = metadata.get("Title") or source.get("document_title") or pdf_path.stem
            base["title_source"] = "pdf_metadata" if metadata.get("Title") else (
                "source_registry" if source.get("document_title") else "filename"
            )
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text(extraction_mode="layout")
                    if text is None:
                        text = ""
                    status = "SUCCESS" if text.strip() else "EMPTY"
                    page_record = {
                        "source_id": source_id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "text": text,
                        "has_text": bool(text.strip()),
                        "extraction_status": status,
                        "structure": _line_structure(text),
                    }
                except Exception as exc:
                    page_record = {
                        "source_id": source_id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "text": "",
                        "has_text": False,
                        "extraction_status": "EXTRACTION_FAILED",
                        "error": f"{type(exc).__name__}: {exc}",
                        "structure": _line_structure(""),
                    }
                base["pages"].append(page_record)
            if not base["pages"]:
                base["extraction_status"] = "FAILED"
                base["error"] = "PDF contains no pages."
            elif any(page["extraction_status"] == "EXTRACTION_FAILED" for page in base["pages"]):
                base["extraction_status"] = "PARTIAL_FAILURE"
            elif any(page["extraction_status"] == "EMPTY" for page in base["pages"]):
                base["extraction_status"] = "PARTIAL"
            else:
                base["extraction_status"] = "SUCCESS"
        except Exception as exc:
            base["extraction_status"] = "FAILED"
            base["error"] = f"{type(exc).__name__}: {exc}"

        output_path = self.output_root / item["topic_folder"] / f"{pdf_path.stem}.{checksum[:16]}.json"
        base["intermediate_output_path"] = str(output_path)
        output_status: str | None = None
        if base["extraction_status"] not in {"FAILED", "INVALID_PDF", "UNMAPPED_SOURCE"}:
            serialized = (json.dumps(base, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with output_path.open("xb") as output:
                    output.write(serialized)
                output_status = "WRITTEN"
            except FileExistsError:
                try:
                    existing = json.loads(output_path.read_text(encoding="utf-8"))
                    if existing.get("sha256") == checksum and existing.get("source_id") == source_id:
                        output_status = "OUTPUT_EXISTS_UNCHANGED"
                    else:
                        output_status = "OUTPUT_CONFLICT"
                        base["output_error"] = "Existing output has different provenance; it was not overwritten."
                except Exception as exc:
                    output_status = "OUTPUT_CONFLICT"
                    base["output_error"] = f"Existing output could not be validated and was not overwritten: {exc}"
        base["output_status"] = output_status
        return base, output_status


def _pipeline(args: argparse.Namespace) -> DocumentIngestionPipeline:
    catalog = load_source_catalog(args.db)
    return DocumentIngestionPipeline(
        documents_root=args.documents_root,
        output_root=args.output_dir,
        source_catalog=catalog,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Page-aware PDF extraction to intermediate JSON only")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("scan", "ingest"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--db", default=str(DEFAULT_DATABASE))
        subparser.add_argument("--documents-root", default=str(DEFAULT_DOCUMENTS_ROOT))
        subparser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args()
    report = _pipeline(args).scan() if args.command == "scan" else _pipeline(args).ingest()
    print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
