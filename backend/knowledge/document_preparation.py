from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pysbd

from .document_extraction import ManifestDocumentStore

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
AUTHORITATIVE_ROOT = (MODULE_DIR / "authoritative_documents").resolve()
DEFAULT_DATABASE = MODULE_DIR / "knowledge.sqlite"
DEFAULT_EXTRACTION_ROOT = MODULE_DIR / "extraction_output"
DEFAULT_PREPARED_ROOT = MODULE_DIR / "prepared_output"
PREPARATION_VERSION = "prepared-text-v1"
_BULLET = re.compile(r"^\s*(?:[-*\u2022\u25cf\u25aa\u2013\u2014]|\d+[.)]|[a-zA-Z][.)])\s+")
_NESTED_HEADING = re.compile(r"^\s*\d+(?:\.\d+)+[.)]?\s+\S")
_NUMBERED_QUESTION = re.compile(r"^\s*\d+[.)]\s+.+\?$")
_STARTER_WORDS = frozenset({"a", "an", "all", "after", "as", "before", "by", "each", "for", "from", "if", "in", "it", "the", "this", "these", "those", "under", "when", "where", "which", "while", "who"})
_HYPHEN_WRAP = re.compile(r"(?<=[a-z])-[ \t]*\r?\n[ \t]*(?=[a-z])")
_HORIZONTAL_SPACE = re.compile(r"[\t\f\v ]+")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative_or_absolute_path(value: str | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    return (PROJECT_ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()


def _normalized_lines(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text).replace("\u00ad", "")
    normalized = _HYPHEN_WRAP.sub("", normalized)
    lines = [_HORIZONTAL_SPACE.sub(" ", line).strip() for line in normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def normalize_paragraph(text: str) -> str:
    """Conservatively normalize PDF whitespace while preserving list line breaks."""
    lines = _normalized_lines(text)
    if not lines:
        return ""
    output = lines[0]
    previous_bullet = bool(_BULLET.match(lines[0]))
    for line in lines[1:]:
        is_bullet = bool(_BULLET.match(line))
        if previous_bullet or is_bullet:
            output += "\n" + line
        else:
            output += " " + line
        previous_bullet = is_bullet
    return _MULTIPLE_NEWLINES.sub("\n\n", output).strip()


def _raw_paragraph_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    start: int | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.strip():
            if start is None:
                start = offset
        elif start is not None:
            end = offset
            raw = text[start:end].rstrip("\r\n")
            if raw.strip():
                spans.append((start, end, raw))
            start = None
        offset += len(line)
    if start is not None:
        raw = text[start:].rstrip("\r\n")
        if raw.strip():
            spans.append((start, len(text), raw))
    return spans


def _heading_map(page_text: str, detected: list[dict[str, Any]]) -> dict[int, str]:
    lines = page_text.splitlines()
    starts: set[int] = set()
    in_paragraph = True
    for number, line in enumerate(lines, start=1):
        if line.strip():
            if in_paragraph:
                starts.add(number)
            in_paragraph = False
        else:
            in_paragraph = True
    result: dict[int, str] = {}
    for candidate in detected:
        number = candidate.get("line_number")
        heading = str(candidate.get("text", "")).strip()
        if not isinstance(number, int) or number not in starts or not heading or _BULLET.match(heading):
            continue
        words = heading.split()
        letters = [char for char in heading if char.isalpha()]
        uppercase = len(words) >= 2 and bool(letters) and heading == heading.upper() and len(heading) <= 140 and not re.search(r"\d|[%=<>]", heading)
        nested = bool(_NESTED_HEADING.match(heading)) and not re.search(r"\s\d+\s*$", heading)
        question = bool(_NUMBERED_QUESTION.match(heading))
        title_case = (
            2 <= len(words) <= 7 and len(heading) <= 80
            and not re.search(r"\d|[%=<>]", heading)
            and not re.search(r"[.!?;:]$", heading)
            and words[0].casefold() not in _STARTER_WORDS
            and sum(word[:1].isupper() for word in words if word[:1].isalpha()) >= max(2, len(words) - 1)
        )
        short_label = (
            len(words) == 2
            and words[0][:1].isupper()
            and words[1][:1].islower()
            and words[0].casefold() not in _STARTER_WORDS
            and not re.search(r"\d|[.!?;:]", heading)
        )
        if uppercase or nested or question or title_case or short_label:
            result[number] = heading
    return result


def _find_heading_in_span(start: int, end: int, raw_text: str, line_offsets: dict[int, int], headings: dict[int, str]) -> tuple[str | None, int | None]:
    for line_number, heading in headings.items():
        line_start = line_offsets.get(line_number)
        if line_start is not None and start <= line_start < end:
            return heading, line_number
    return None, None


def _sentence_offsets(text: str, segmenter: pysbd.Segmenter) -> list[tuple[str, int, int]]:
    sentences: list[tuple[str, int, int]] = []
    cursor = 0
    for segment in segmenter.segment(text):
        sentence = segment.strip()
        if not sentence:
            continue
        location = text.find(sentence, cursor)
        if location < 0:
            location = cursor
        end = location + len(sentence)
        sentences.append((sentence, location, end))
        cursor = end
    return sentences


@dataclass
class PreparationReport:
    manifest_documents: int = 0
    documents_processed: int = 0
    documents_skipped_idempotent: int = 0
    documents_missing_extraction: int = 0
    documents_invalid_extraction: int = 0
    pages_processed: int = 0
    sections: int = 0
    paragraphs: int = 0
    sentences: int = 0
    prepared_outputs: list[str] | None = None
    errors: list[dict[str, str]] | None = None
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_documents": self.manifest_documents,
            "documents_processed": self.documents_processed,
            "documents_skipped_idempotent": self.documents_skipped_idempotent,
            "documents_missing_extraction": self.documents_missing_extraction,
            "documents_invalid_extraction": self.documents_invalid_extraction,
            "pages_processed": self.pages_processed,
            "sections": self.sections,
            "paragraphs": self.paragraphs,
            "sentences": self.sentences,
            "prepared_outputs": self.prepared_outputs or [],
            "errors": self.errors or [],
            "dry_run": self.dry_run,
        }


class DocumentPreparationService:
    def __init__(
        self,
        *,
        database_path: str | Path = DEFAULT_DATABASE,
        extraction_root: str | Path = DEFAULT_EXTRACTION_ROOT,
        prepared_root: str | Path = DEFAULT_PREPARED_ROOT,
        manifest_store: ManifestDocumentStore | None = None,
        segmenter: pysbd.Segmenter | None = None,
        authoritative_root: str | Path = AUTHORITATIVE_ROOT,
    ):
        self.store = manifest_store or ManifestDocumentStore(database_path)
        self.owns_store = manifest_store is None
        self.extraction_root = Path(extraction_root).resolve()
        self.prepared_root = Path(prepared_root).resolve()
        self.authoritative_root = Path(authoritative_root).resolve()
        self.segmenter = segmenter or pysbd.Segmenter(language="en", clean=False)

    def close(self) -> None:
        if self.owns_store:
            self.store.close()

    def prepare_all(self, *, dry_run: bool = False, source_id: str | None = None) -> PreparationReport:
        manifest_rows = self.store.list_documents(source_id)
        report = PreparationReport(manifest_documents=len(manifest_rows), dry_run=dry_run, prepared_outputs=[], errors=[])
        extracted = self._load_registered_extractions(manifest_rows, report)
        for manifest, extraction, path in extracted:
            if dry_run:
                report.prepared_outputs.append(str(self._output_path(manifest, extraction, path)))
                report.documents_processed += 1
                continue
            try:
                prepared = self._prepare_one(manifest, extraction, path)
                output = self._output_path(manifest, extraction, path)
                result = self._write_output(output, prepared)
                if result == "SKIPPED_IDEMPOTENT":
                    report.documents_skipped_idempotent += 1
                else:
                    report.documents_processed += 1
                    report.pages_processed += len(prepared["pages"])
                    report.sections += len(prepared["sections"])
                    report.paragraphs += sum(len(page["paragraphs"]) for page in prepared["pages"])
                    report.sentences += sum(len(page["sentences"]) for page in prepared["pages"])
                report.prepared_outputs.append(str(output))
            except Exception as exc:
                report.documents_invalid_extraction += 1
                report.errors.append({"source_id": manifest.get("source_id", ""), "document_id": manifest.get("document_id", ""), "error": f"{type(exc).__name__}: {exc}"})
        return report

    def _load_registered_extractions(
        self, manifest_rows: list[dict[str, Any]], report: PreparationReport,
    ) -> list[tuple[dict[str, Any], dict[str, Any], Path]]:
        by_key = {(row["source_id"], row["document_id"], row.get("checksum")): row for row in manifest_rows}
        found: dict[tuple[str, str, str | None], tuple[dict[str, Any], Path]] = {}
        if self.extraction_root.is_dir():
            for path in sorted(self.extraction_root.rglob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                key = (data.get("source_id"), data.get("document_id"), data.get("sha256"))
                if key in by_key:
                    found[key] = (data, path)
        result = []
        for key, manifest in by_key.items():
            value = found.get(key)
            if not value:
                report.documents_missing_extraction += 1
                report.errors.append({"source_id": manifest["source_id"], "document_id": manifest["document_id"], "error": "No matching extraction_output JSON for this registered manifest document."})
                continue
            result.append((manifest, value[0], value[1]))
        return result

    def _validate_input(self, manifest: dict[str, Any], extraction: dict[str, Any], extraction_path: Path) -> tuple[Path, str]:
        if extraction.get("extraction_status") not in {"SUCCESS", "PARTIAL", "PARTIAL_FAILURE"}:
            raise ValueError(f"Extraction status is not preparable: {extraction.get('extraction_status')}")
        manifest_checksum = manifest.get("checksum")
        extraction_checksum = extraction.get("sha256")
        if not manifest_checksum or extraction_checksum != manifest_checksum:
            raise ValueError("Extraction checksum does not match the registered manifest checksum")
        manifest_path = _relative_or_absolute_path(manifest.get("local_file"))
        extraction_path_value = _relative_or_absolute_path(extraction.get("absolute_source_path") or extraction.get("relative_source_path"))
        if manifest_path is None or extraction_path_value is None or manifest_path != extraction_path_value:
            raise ValueError("Extraction source path does not match the registered manifest local_file")
        if not manifest_path.is_relative_to(self.authoritative_root) or not manifest_path.is_file():
            raise ValueError("Registered source PDF is missing or outside authoritative_documents")
        actual_checksum = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if actual_checksum != manifest_checksum:
            raise ValueError("Source PDF checksum no longer matches the registered manifest")
        return manifest_path, actual_checksum

    def _prepare_one(self, manifest: dict[str, Any], extraction: dict[str, Any], extraction_path: Path) -> dict[str, Any]:
        source_path, actual_checksum = self._validate_input(manifest, extraction, extraction_path)
        extraction_bytes = extraction_path.read_bytes()
        extraction_hash = sha256_bytes(extraction_bytes)
        document_id = manifest["document_id"]
        source_id = manifest["source_id"]
        sections: dict[str, dict[str, Any]] = {}
        pages_out: list[dict[str, Any]] = []
        active_section_id: str | None = None
        active_heading: str | None = None
        section_occurrence = 0
        sentence_total = 0
        paragraph_total = 0

        for page in sorted(extraction.get("pages", []), key=lambda item: item.get("page_number", 0)):
            page_number = page.get("page_number")
            if not isinstance(page_number, int) or page_number < 1:
                raise ValueError("Every extraction page requires a positive page_number")
            raw_page_text = page.get("text")
            if not isinstance(raw_page_text, str):
                raise ValueError(f"Page {page_number} has no raw text string")
            structure = page.get("structure", {})
            headings = _heading_map(raw_page_text, structure.get("headings", []))
            line_offsets: dict[int, int] = {}
            offset = 0
            for line_number, line in enumerate(raw_page_text.splitlines(keepends=True), start=1):
                line_offsets[line_number] = offset
                offset += len(line)
            spans = _raw_paragraph_spans(raw_page_text)
            page_paragraphs: list[dict[str, Any]] = []
            page_sentences: list[dict[str, Any]] = []
            page_parts: list[tuple[str, dict[str, Any] | None]] = []
            page_clean_cursor = 0

            for paragraph_index, (raw_start, raw_end, raw_paragraph) in enumerate(spans):
                first_nonempty_line = next((n for n, line in enumerate(raw_paragraph.splitlines(), start=1) if line.strip()), 1)
                raw_start_line = raw_page_text.count("\n", 0, raw_start) + first_nonempty_line
                heading, heading_line = _find_heading_in_span(
                    raw_start, raw_end, raw_page_text, line_offsets, headings
                )
                raw_lines = raw_paragraph.splitlines()
                body_lines = raw_lines
                if heading and heading_line:
                    local_heading_line = heading_line - raw_start_line
                    body_lines = [line for idx, line in enumerate(raw_lines) if idx != local_heading_line]
                    normalized_heading = normalize_paragraph(heading)
                    if normalized_heading:
                        if active_heading != normalized_heading:
                            section_occurrence += 1
                            active_heading = normalized_heading
                            active_section_id = _stable_id("sec", document_id, str(section_occurrence), normalized_heading)
                            sections.setdefault(active_section_id, {
                                "section_id": active_section_id,
                                "heading": normalized_heading,
                                "page_start": page_number,
                                "page_end": page_number,
                                "paragraph_ids": [],
                                "sentence_ids": [],
                            })
                        page_parts.append((normalized_heading, None))
                    if not any(line.strip() for line in body_lines):
                        paragraph_id = _stable_id("para", document_id, str(page_number), str(paragraph_index), str(raw_start))
                        paragraph_record = {
                            "paragraph_id": paragraph_id,
                            "section_id": active_section_id,
                            "section_heading": active_heading,
                            "page_number": page_number,
                            "paragraph_index": paragraph_index,
                            "raw_start": raw_start,
                            "raw_end": raw_end,
                            "raw_text": raw_paragraph,
                            "cleaned_text": "",
                            "character_count": 0,
                            "is_heading": True,
                            "sentence_ids": [],
                        }
                        page_paragraphs.append(paragraph_record)
                        paragraph_total += 1
                        continue

                cleaned_text = normalize_paragraph("\n".join(body_lines))
                paragraph_id = _stable_id("para", document_id, str(page_number), str(paragraph_index), str(raw_start))
                paragraph_record = {
                    "paragraph_id": paragraph_id,
                    "section_id": active_section_id,
                    "section_heading": active_heading,
                    "page_number": page_number,
                    "paragraph_index": paragraph_index,
                    "raw_start": raw_start,
                    "raw_end": raw_end,
                    "raw_text": raw_paragraph,
                    "cleaned_text": cleaned_text,
                    "character_count": len(cleaned_text),
                    "is_heading": False,
                    "sentence_ids": [],
                }
                page_paragraphs.append(paragraph_record)
                paragraph_total += 1
                if cleaned_text:
                    page_parts.append((cleaned_text, paragraph_record))
                page_clean_cursor = sum(len(part) + 2 for part, _ in page_parts)
                for local_index, (sentence_text, start, end) in enumerate(_sentence_offsets(cleaned_text, self.segmenter), start=1):
                    sentence_id = _stable_id("sent", document_id, str(page_number), paragraph_id, str(local_index), _hash(sentence_text))
                    sentence_record = {
                        "sentence_id": sentence_id,
                        "source_id": source_id,
                        "document_id": document_id,
                        "page_number": page_number,
                        "paragraph_id": paragraph_id,
                        "section_id": active_section_id,
                        "section_heading": active_heading,
                        "sentence_index": sentence_total + 1,
                        "text": sentence_text,
                        "character_start": start,
                        "character_end": end,
                        "offset_basis": "paragraph.cleaned_text",
                    }
                    sentence_total += 1
                    paragraph_record["sentence_ids"].append(sentence_id)
                    page_sentences.append(sentence_record)
                    if active_section_id:
                        sections[active_section_id]["sentence_ids"].append(sentence_id)
                        sections[active_section_id]["paragraph_ids"].append(paragraph_id)
                        sections[active_section_id]["page_end"] = page_number

            cleaned_page_text = "\n\n".join(part for part, _ in page_parts)
            pages_out.append({
                "source_id": source_id,
                "document_id": document_id,
                "page_number": page_number,
                "raw_text": raw_page_text,
                "cleaned_text": cleaned_page_text,
                "has_raw_text": bool(raw_page_text.strip()),
                "paragraphs": page_paragraphs,
                "sentences": page_sentences,
                "extraction_status": page.get("extraction_status", "UNKNOWN"),
                "raw_structure": structure,
            })

        for section in sections.values():
            section["paragraph_ids"] = list(dict.fromkeys(section["paragraph_ids"]))
            section["sentence_ids"] = list(dict.fromkeys(section["sentence_ids"]))
        return {
            "prepared_format_version": PREPARATION_VERSION,
            "prepared_document_id": _stable_id("prep", document_id, actual_checksum, PREPARATION_VERSION, extraction_hash),
            "source_id": source_id,
            "document_id": document_id,
            "manifest_id": document_id,
            "version_id": manifest.get("version_id"),
            "document_checksum": actual_checksum,
            "input_extraction_sha256": extraction_hash,
            "filename": source_path.name,
            "absolute_source_path": str(source_path),
            "relative_source_path": source_path.relative_to(PROJECT_ROOT).as_posix()
            if source_path.is_relative_to(PROJECT_ROOT) else str(source_path),
            "file_type": source_path.suffix.lower(),
            "title": extraction.get("title") or manifest.get("document_title"),
            "document_metadata": extraction.get("document_metadata", {}),
            "manifest_metadata": manifest,
            "source_metadata": extraction.get("source_metadata", {}),
            "extraction_version": extraction.get("extraction_version", extraction.get("schema_version")),
            "extraction_status": extraction.get("extraction_status"),
            "extraction_timestamp": extraction.get("extraction_timestamp"),
            "preparation_version": PREPARATION_VERSION,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "normalization": {
                "unicode_normalization": "NFC",
                "soft_hyphen_removed": True,
                "safe_line_wrap_dehyphenation": True,
                "paragraph_whitespace_normalized": True,
                "repeated_headers_removed": False,
                "notes": "Repeated headers/footers are not removed unless explicit page-level repeated-header metadata is supplied; raw text is retained.",
            },
            "sections": list(sections.values()),
            "pages": pages_out,
            "statistics": {
                "page_count": len(pages_out),
                "section_count": len(sections),
                "paragraph_count": paragraph_total,
                "sentence_count": sentence_total,
                "raw_characters": sum(len(page["raw_text"]) for page in pages_out),
                "cleaned_characters": sum(len(page["cleaned_text"]) for page in pages_out),
            },
        }

    def _output_path(self, manifest: dict[str, Any], extraction: dict[str, Any], extraction_path: Path) -> Path:
        source = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(manifest["source_id"]))
        document = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(manifest["document_id"]))
        raw_hash = sha256_bytes(extraction_path.read_bytes())
        return self.prepared_root / source / f"{document}.{PREPARATION_VERSION}.{raw_hash[:16]}.json"

    def _write_output(self, path: Path, prepared: dict[str, Any]) -> str:
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("prepared_document_id") == prepared.get("prepared_document_id") and \
                    existing.get("document_checksum") == prepared.get("document_checksum") and \
                    existing.get("input_extraction_sha256") == prepared.get("input_extraction_sha256"):
                return "SKIPPED_IDEMPOTENT"
            raise FileExistsError(f"Prepared output exists with different provenance; not overwriting: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write((json.dumps(prepared, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))
        return "WRITTEN"


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{hashlib.sha256(chr(0).join(parts).encode('utf-8')).hexdigest()[:28]}"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_line(line: str) -> str:
    line = unicodedata.normalize("NFC", line).replace("\u00ad", "")
    return _HORIZONTAL_SPACE.sub(" ", line).strip()


def normalize_paragraph(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).replace("\u00ad", "")
    normalized = _HYPHEN_WRAP.sub("", normalized)
    lines = [
        cleaned for raw_line in normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if (cleaned := _clean_line(raw_line))
    ]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    output = lines[0]
    previous_bullet = bool(_BULLET.match(lines[0]))
    for line in lines[1:]:
        if previous_bullet or _BULLET.match(line):
            output += "\n" + line
        else:
            output += " " + line
        previous_bullet = bool(_BULLET.match(line))
    return output.strip()


def _sentence_offsets(text: str, segmenter: pysbd.Segmenter) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    cursor = 0
    for segment in segmenter.segment(text):
        sentence = segment.strip()
        if not sentence:
            continue
        start = text.find(sentence, cursor)
        if start < 0:
            start = cursor
        end = start + len(sentence)
        result.append((sentence, start, end))
        cursor = end
    return result


def _run_from_cli(args: argparse.Namespace) -> dict[str, Any]:
    service = DocumentPreparationService(database_path=args.db, extraction_root=args.input_dir, prepared_root=args.output_dir)
    try:
        return service.prepare_all(dry_run=args.dry_run, source_id=args.source_id).to_dict()
    finally:
        service.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare normalized page/paragraph/sentence JSON from registered extraction output")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-all", help="Prepare extraction JSON matched to manifest documents")
    prepare.add_argument("--db", default=str(DEFAULT_DATABASE))
    prepare.add_argument("--input-dir", default=str(DEFAULT_EXTRACTION_ROOT))
    prepare.add_argument("--output-dir", default=str(DEFAULT_PREPARED_ROOT))
    prepare.add_argument("--source-id")
    prepare.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(_run_from_cli(args), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
