from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pysbd

from .document_ingestion import has_pdf_signature, sha256_file
from .repository import KnowledgeRepository

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[2]
AUTHORITATIVE_ROOT = (MODULE_DIR / "authoritative_documents").resolve()
DEFAULT_DATABASE = MODULE_DIR / "knowledge.sqlite"
DEFAULT_EXTRACTION_ROOT = MODULE_DIR / "extraction_output"
DEFAULT_CHUNKING_VERSION = "hierarchical-semantic-v1"

_WORD_OR_PUNCT = re.compile(r"\w+(?:['’]\w+)*|[^\w\s]", re.UNICODE)
_WORD = re.compile(r"[a-z0-9]+(?:['’][a-z0-9]+)*", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*\u2022\u25cf\u25aa\u2013\u2014]|\d+[.)]|[a-zA-Z][.)])\s+")
_NUMBER_ONLY = re.compile(r"^\s*(?:\d+(?:\.\d+)*[.)]?|[a-zA-Z][.)])\s*$")
_NUMBERED_HEADING = re.compile(r"^\s*\d+(?:\.\d+)*[.)]?\s+\S")
_NESTED_SECTION = re.compile(r"^\s*\d+(?:\.\d+)+[.)]?\s+\S")
_NUMBERED_QUESTION = re.compile(r"^\s*\d+[.)]\s+.+\?$")
_SENTENCE_STARTERS = frozenset({
    "a", "an", "all", "after", "as", "before", "by", "each", "for", "from", "if",
    "in", "it", "once", "the", "these", "this", "those", "under", "when", "where",
    "which", "while", "who", "yes",
})
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for",
    "from", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "there", "this", "to", "was", "were", "will", "with",
})


@dataclass(frozen=True)
class ChunkingConfig:
    chunking_version: str = DEFAULT_CHUNKING_VERSION
    target_child_tokens: int = 400
    max_child_tokens: int = 600
    min_child_tokens: int = 220
    overlap_sentences: int = 1
    parent_target_tokens: int = 1250
    max_parent_tokens: int = 1500
    semantic_similarity_threshold: float = 0.12
    semantic_min_chunk_tokens: int = 180
    token_metric: str = "regex_word_and_punctuation_estimate"

    def __post_init__(self) -> None:
        if not 0 <= self.semantic_similarity_threshold <= 1:
            raise ValueError("semantic_similarity_threshold must be between 0 and 1")
        if self.target_child_tokens <= 0 or self.max_child_tokens < self.target_child_tokens:
            raise ValueError("max_child_tokens must be >= target_child_tokens > 0")
        if self.parent_target_tokens <= 0 or self.max_parent_tokens < self.parent_target_tokens:
            raise ValueError("max_parent_tokens must be >= parent_target_tokens > 0")
        if self.overlap_sentences < 0:
            raise ValueError("overlap_sentences cannot be negative")

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @property
    def configuration_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    return len(_WORD_OR_PUNCT.findall(text))


def _merge_number_prefixes(sentences: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0
    while index < len(sentences):
        sentence = sentences[index].strip()
        if _NUMBER_ONLY.fullmatch(sentence) and index + 1 < len(sentences):
            merged.append(f"{sentence} {sentences[index + 1].strip()}".strip())
            index += 2
        else:
            if sentence:
                merged.append(sentence)
            index += 1
    return merged


def split_sentences(text: str, *, segmenter: pysbd.Segmenter | None = None) -> list[str]:
    """Split paragraphs with a rule-based sentence segmenter, retaining list starts."""
    active = segmenter or pysbd.Segmenter(language="en", clean=False)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    groups: list[str] = []
    pending: list[str] = []
    for line in lines or [text.strip()]:
        if _BULLET.match(line):
            if pending:
                groups.extend(active.segment(" ".join(pending)))
                pending = []
            groups.extend(active.segment(line))
        else:
            pending.append(line)
    if pending:
        groups.extend(active.segment(" ".join(pending)))
    return _merge_number_prefixes([part.strip() for part in groups if part.strip()])


def _semantic_terms(text: str) -> list[str]:
    words = [word.casefold() for word in _WORD.findall(text) if word.casefold() not in _STOPWORDS]
    return words + [f"{left}_{right}" for left, right in zip(words, words[1:])]


def _idf_weights(texts: list[str]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for text in texts:
        document_frequency.update(set(_semantic_terms(text)))
    count = max(1, len(texts))
    return {term: math.log((count + 1) / (frequency + 1)) + 1.0 for term, frequency in document_frequency.items()}


def _tfidf(text: str, idf: dict[str, float]) -> dict[str, float]:
    frequencies = Counter(_semantic_terms(text))
    return {term: frequency * idf.get(term, 1.0) for term, frequency in frequencies.items()}


def cosine_similarity(left: str, right: str, idf: dict[str, float] | None = None) -> float:
    active_idf = idf or _idf_weights([left, right])
    left_vector, right_vector = _tfidf(left, active_idf), _tfidf(right, active_idf)
    denominator = math.sqrt(sum(value * value for value in left_vector.values())) * math.sqrt(
        sum(value * value for value in right_vector.values())
    )
    if denominator == 0:
        return 0.0
    return sum(left_vector.get(term, 0.0) * right_vector.get(term, 0.0)
               for term in left_vector.keys() & right_vector.keys()) / denominator


@dataclass(frozen=True)
class SentenceRecord:
    sentence_index: int
    text: str
    page_number: int
    paragraph_index: int
    section_heading: str | None


def _paragraphs(text: str) -> list[list[tuple[int, str]]]:
    paragraphs: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            current.append((line_number, line.strip()))
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _heading_map(text: str, detected: list[dict[str, Any]]) -> dict[int, str]:
    lines = text.splitlines()
    paragraph_starts: set[int] = set()
    at_paragraph_start = True
    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            if at_paragraph_start:
                paragraph_starts.add(line_number)
            at_paragraph_start = False
        else:
            at_paragraph_start = True
    headings: dict[int, str] = {}
    for item in detected:
        line_number = item.get("line_number")
        heading = str(item.get("text", "")).strip()
        if not isinstance(line_number, int) or line_number not in paragraph_starts or not heading or _BULLET.match(heading):
            continue
        alpha_words = re.findall(r"[A-Za-z]+", heading)
        uppercase = (
            len(alpha_words) >= 2
            and any(char.isalpha() for char in heading)
            and heading == heading.upper()
            and len(heading) <= 140
            and not re.search(r"\d|[%=<>]", heading)
        )
        nested_title = bool(_NESTED_SECTION.match(heading)) and not re.search(r"\s\d+\s*$", heading)
        numbered_question = bool(_NUMBERED_QUESTION.match(heading))
        words = heading.split()
        title_case = (
            2 <= len(words) <= 7
            and len(heading) <= 80
            and not re.search(r"\d|[%=<>]", heading)
            and not re.search(r"[.!?;:]$", heading)
            and words[0].casefold() not in _SENTENCE_STARTERS
            and sum(word[:1].isupper() for word in words if word[:1].isalpha()) >= max(2, len(words) - 1)
        )
        if uppercase or nested_title or numbered_question or title_case:
            headings[line_number] = heading
    return headings


def _sentences_from_extraction(extraction: dict[str, Any], segmenter: pysbd.Segmenter) -> list[SentenceRecord]:
    result: list[SentenceRecord] = []
    sentence_index = 0
    paragraph_index = 0
    active_heading: str | None = None
    for page in sorted(extraction.get("pages", []), key=lambda item: item.get("page_number", 0)):
        page_number = page.get("page_number")
        if not isinstance(page_number, int) or page_number < 1:
            raise ValueError("Every extracted page requires a positive page_number")
        text = page.get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        detected = _heading_map(text, page.get("structure", {}).get("headings", []))
        for paragraph in _paragraphs(text):
            body_lines: list[str] = []
            for line_number, line in paragraph:
                heading = detected.get(line_number)
                if heading:
                    if body_lines:
                        for sentence in split_sentences("\n".join(body_lines), segmenter=segmenter):
                            sentence_index += 1
                            result.append(SentenceRecord(sentence_index, sentence, page_number, paragraph_index, active_heading))
                        paragraph_index += 1
                        body_lines = []
                    active_heading = heading
                else:
                    body_lines.append(line)
            if body_lines:
                for sentence in split_sentences("\n".join(body_lines), segmenter=segmenter):
                    sentence_index += 1
                    result.append(SentenceRecord(sentence_index, sentence, page_number, paragraph_index, active_heading))
                paragraph_index += 1
    return result


def _render(sentences: list[SentenceRecord], section_heading: str | None) -> str:
    paragraphs: list[list[str]] = []
    current_paragraph: int | None = None
    for sentence in sentences:
        if sentence.paragraph_index != current_paragraph:
            paragraphs.append([])
            current_paragraph = sentence.paragraph_index
        paragraphs[-1].append(sentence.text)
    body = "\n\n".join(" ".join(group) for group in paragraphs)
    return f"{section_heading}\n\n{body}" if section_heading else body


def _make_parents(sentences: list[SentenceRecord], config: ChunkingConfig) -> list[dict[str, Any]]:
    sections: list[list[SentenceRecord]] = []
    current_section: list[SentenceRecord] = []
    section_heading: str | None = None
    for sentence in sentences:
        if current_section and sentence.section_heading != section_heading:
            sections.append(current_section)
            current_section = []
        if not current_section:
            section_heading = sentence.section_heading
        current_section.append(sentence)
    if current_section:
        sections.append(current_section)

    parents: list[dict[str, Any]] = []
    for section in sections:
        heading = section[0].section_heading
        heading_tokens = estimate_tokens(heading) if heading else 0
        group: list[SentenceRecord] = []
        size = heading_tokens
        for sentence in section:
            sentence_tokens = estimate_tokens(sentence.text)
            paragraph_boundary = bool(group and group[-1].paragraph_index != sentence.paragraph_index)
            if group and size + sentence_tokens > config.max_parent_tokens:
                parents.append({"sentences": group, "section_heading": heading, "boundary_reason": "parent_max_size"})
                group, size = [], heading_tokens
            elif group and size >= config.parent_target_tokens and paragraph_boundary:
                parents.append({"sentences": group, "section_heading": heading, "boundary_reason": "paragraph_boundary"})
                group, size = [], heading_tokens
            group.append(sentence)
            size += sentence_tokens
        if group:
            parents.append({"sentences": group, "section_heading": heading, "boundary_reason": "section_end"})
    return parents


def _make_child_groups(sentences: list[SentenceRecord], heading: str | None, config: ChunkingConfig) -> list[dict[str, Any]]:
    idf = _idf_weights([sentence.text for sentence in sentences])
    heading_tokens = estimate_tokens(heading) if heading else 0
    groups: list[dict[str, Any]] = []
    current: list[SentenceRecord] = []
    current_size = heading_tokens
    previous_main: list[SentenceRecord] = []

    for sentence in sentences:
        sentence_size = estimate_tokens(sentence.text)
        overlap = previous_main[-config.overlap_sentences:] if config.overlap_sentences else []
        base_size = heading_tokens + sum(estimate_tokens(item.text) for item in overlap)
        if not current:
            current_size = base_size
        reason: str | None = None
        if current:
            if current_size + sentence_size > config.max_child_tokens:
                reason = "child_max_size"
            elif current_size >= config.target_child_tokens and current[-1].paragraph_index != sentence.paragraph_index:
                reason = "paragraph_boundary"
            elif current_size >= config.semantic_min_chunk_tokens and current_size >= config.min_child_tokens:
                context = " ".join(item.text for item in current[-3:])
                if cosine_similarity(context, sentence.text, idf) < config.semantic_similarity_threshold:
                    reason = "semantic_similarity_drop"
        if reason:
            groups.append({"sentences": current, "boundary_reason": reason})
            previous_main = current
            current = []
            current_size = heading_tokens + sum(
                estimate_tokens(item.text)
                for item in (previous_main[-config.overlap_sentences:] if config.overlap_sentences else [])
            )
        current.append(sentence)
        current_size += sentence_size
    if current:
        groups.append({"sentences": current, "boundary_reason": "parent_end"})
    return groups


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _document_key(extraction: dict[str, Any]) -> tuple[str, str, str]:
    source_id = extraction.get("source_id")
    document_id = extraction.get("document_id")
    checksum = extraction.get("sha256")
    if not source_id or not document_id or not checksum:
        raise ValueError("Extraction input requires source_id, document_id, and sha256 provenance")
    return str(source_id), str(document_id), str(checksum)


def _deterministic_id(prefix: str, *parts: str) -> str:
    return prefix + hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:32]


def _chunk_row(
    *, run_id: str, config: ChunkingConfig, source_id: str, document_id: str,
    document_checksum: str, source_status: str, chunk_id: str, chunk_type: str,
    parent_chunk_id: str | None, index: int, heading: str | None,
    sentences: list[SentenceRecord], text: str, overlap: list[SentenceRecord],
    boundary_reason: str, overlap_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "run_id": run_id,
        "chunk_type": chunk_type,
        "parent_chunk_id": parent_chunk_id,
        "source_id": source_id,
        "document_id": document_id,
        "document_checksum": document_checksum,
        "source_validation_status": source_status,
        "page_start": min(item.page_number for item in sentences),
        "page_end": max(item.page_number for item in sentences),
        "section_heading": heading,
        "chunk_index": index,
        "text": text,
        "sentence_start": min(item.sentence_index for item in sentences),
        "sentence_end": max(item.sentence_index for item in sentences),
        "token_count": estimate_tokens(text),
        "overlap_sentence_count": len(overlap),
        "overlap_metadata": json.dumps(overlap_metadata or {}, ensure_ascii=False),
        "boundary_reason": boundary_reason,
        "chunking_version": config.chunking_version,
        "content_hash": _hash_text(text),
    }


def _build_chunks(extraction: dict[str, Any], config: ChunkingConfig) -> dict[str, Any]:
    source_id, document_id, checksum = _document_key(extraction)
    if extraction.get("extraction_status") not in {"SUCCESS", "PARTIAL", "PARTIAL_FAILURE"}:
        raise ValueError(f"Extraction status is not chunkable: {extraction.get('extraction_status')}")
    sentences = _sentences_from_extraction(extraction, pysbd.Segmenter(language="en", clean=False))
    if not sentences:
        raise ValueError("No non-empty extracted sentences are available")
    config_hash = config.configuration_hash
    run_id = _deterministic_id("run_", source_id, document_id, checksum, config.chunking_version, config_hash)
    parents = _make_parents(sentences, config)
    parent_rows: list[dict[str, Any]] = []
    child_rows: list[dict[str, Any]] = []
    pages: set[int] = set()
    child_index = 0

    for parent_index, parent in enumerate(parents):
        parent_sentences = parent["sentences"]
        parent_text = _render(parent_sentences, parent["section_heading"])
        parent_hash = _hash_text(parent_text)
        parent_id = _deterministic_id("parent_", run_id, str(parent_index), parent_hash)
        parent_rows.append(_chunk_row(
            run_id=run_id, config=config, source_id=source_id, document_id=document_id,
            document_checksum=checksum,
            source_status=str(extraction.get("source_metadata", {}).get("validation_status", "UNKNOWN")),
            chunk_id=parent_id, chunk_type="PARENT", parent_chunk_id=None, index=parent_index,
            heading=parent["section_heading"], sentences=parent_sentences, text=parent_text,
            overlap=[], boundary_reason=parent["boundary_reason"],
        ))
        child_groups = _make_child_groups(parent_sentences, parent["section_heading"], config)
        previous_main: list[SentenceRecord] = []
        previous_child_id: str | None = None
        for child in child_groups:
            overlap = previous_main[-config.overlap_sentences:] if config.overlap_sentences else []
            included = overlap + child["sentences"]
            child_text = _render(included, parent["section_heading"])
            child_hash = _hash_text(child_text)
            child_id = _deterministic_id("child_", run_id, str(child_index), child_hash)
            metadata = {
                "overlap_sentence_count": len(overlap),
                "overlap_sentence_indices": [item.sentence_index for item in overlap],
                "overlap_from_child_chunk_id": previous_child_id,
                "overlap_text": [item.text for item in overlap],
            }
            child_rows.append(_chunk_row(
                run_id=run_id, config=config, source_id=source_id, document_id=document_id,
                document_checksum=checksum,
                source_status=str(extraction.get("source_metadata", {}).get("validation_status", "UNKNOWN")),
                chunk_id=child_id, chunk_type="CHILD", parent_chunk_id=parent_id, index=child_index,
                heading=parent["section_heading"], sentences=included, text=child_text,
                overlap=overlap, boundary_reason=child["boundary_reason"], overlap_metadata=metadata,
            ))
            pages.update(item.page_number for item in included)
            previous_main = child["sentences"]
            previous_child_id = child_id
            child_index += 1

    return {
        "run_id": run_id,
        "source_id": source_id,
        "document_id": document_id,
        "document_checksum": checksum,
        "chunking_version": config.chunking_version,
        "configuration_hash": config_hash,
        "configuration_json": config.canonical_json(),
        "parent_rows": parent_rows,
        "child_rows": child_rows,
        "pages_covered": sorted(pages),
    }


class HierarchicalChunker:
    """Reusable deterministic chunk generator independent of persistence."""

    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

    def chunk_document(self, extraction: dict[str, Any]) -> dict[str, Any]:
        return _build_chunks(extraction, self.config)


class ChunkingService:
    def __init__(self, *, database_path: str | Path = DEFAULT_DATABASE,
                 input_root: str | Path = DEFAULT_EXTRACTION_ROOT,
                 authoritative_root: str | Path = AUTHORITATIVE_ROOT,
                 config: ChunkingConfig | None = None):
        self.database_path = Path(database_path).resolve()
        self.input_root = Path(input_root).resolve()
        self.authoritative_root = Path(authoritative_root).resolve()
        self.config = config or ChunkingConfig()
        self.repository = KnowledgeRepository.from_path(self.database_path)
        self.chunker = HierarchicalChunker(self.config)

    def close(self) -> None:
        self.repository.close()

    def run(self, *, source_id: str | None = None, debug: bool = False) -> dict[str, Any]:
        report: dict[str, Any] = {
            "documents_seen": 0, "documents_processed": 0, "documents_skipped_idempotent": 0,
            "documents_failed": 0, "parent_chunks": 0, "child_chunks": 0, "documents": [],
        }
        if not self.input_root.is_dir():
            return report
        for path in sorted(self.input_root.rglob("*.json")):
            try:
                extraction = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if source_id and extraction.get("source_id") != source_id:
                continue
            report["documents_seen"] += 1
            try:
                self._validate_extraction(extraction)
                result = self.chunker.chunk_document(extraction)
                saved = self._persist(path, extraction, result)
                report["documents"].append(saved)
                if saved["status"] == "SKIPPED_IDEMPOTENT":
                    report["documents_skipped_idempotent"] += 1
                else:
                    report["documents_processed"] += 1
                    report["parent_chunks"] += len(result["parent_rows"])
                    report["child_chunks"] += len(result["child_rows"])
            except Exception as exc:
                report["documents_failed"] += 1
                report["documents"].append({"source_id": extraction.get("source_id"),"document_id": extraction.get("document_id"),"status":"FAILED","error":f"{type(exc).__name__}: {exc}","input_extraction_path":str(path)})
        if debug:
            report["sample_chunks"] = self._sample_chunks(source_id=source_id)
        return report

    def _validate_extraction(self, extraction: dict[str, Any]) -> None:
        source_id, _, checksum = _document_key(extraction)
        source = self.repository.connection.execute("SELECT validation_status FROM source_registry WHERE source_id=?", (source_id,)).fetchone()
        if not source:
            raise ValueError(f"source_id is not in source_registry: {source_id}")
        raw_path = extraction.get("absolute_source_path") or extraction.get("relative_source_path")
        if not raw_path:
            raise ValueError("Extraction is missing original PDF path provenance")
        stored_path = Path(raw_path)
        pdf_path = (PROJECT_ROOT / stored_path).resolve() if not stored_path.is_absolute() else stored_path.resolve()
        if not pdf_path.is_relative_to(self.authoritative_root):
            raise ValueError(f"Extraction source PDF is outside authoritative_documents: {pdf_path}")
        if not pdf_path.is_file():
            raise FileNotFoundError(f"Extraction source PDF is missing: {pdf_path}")
        if not has_pdf_signature(pdf_path):
            raise ValueError(f"Extraction source is not a PDF: {pdf_path}")
        actual = sha256_file(pdf_path)
        if actual.lower() != checksum.lower():
            raise ValueError(f"Extraction checksum no longer matches source PDF: {pdf_path}")
        extraction["source_metadata"] = {"validation_status": source["validation_status"]}

    def _persist(self, input_path: Path, extraction: dict[str, Any], chunked: dict[str, Any]) -> dict[str, Any]:
        connection = self.repository.connection
        existing = connection.execute(
            """SELECT run_id,parent_chunk_count,child_chunk_count FROM chunking_runs
               WHERE source_id=? AND document_id=? AND document_checksum=? AND chunking_version=? AND configuration_hash=?""",
            (chunked["source_id"],chunked["document_id"],chunked["document_checksum"],chunked["chunking_version"],chunked["configuration_hash"]),
        ).fetchone()
        if existing:
            return {"source_id":chunked["source_id"],"document_id":chunked["document_id"],"run_id":existing["run_id"],"status":"SKIPPED_IDEMPOTENT","parent_chunks":existing["parent_chunk_count"],"child_chunks":existing["child_chunk_count"]}
        source_status = extraction.get("source_metadata", {}).get("validation_status", "UNKNOWN")
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO chunking_runs
                (run_id,source_id,document_id,document_checksum,chunking_version,configuration_hash,configuration_json,input_extraction_path,source_validation_status,status,parent_chunk_count,child_chunk_count,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,'COMPLETED',?,?,?)""",
                (chunked["run_id"],chunked["source_id"],chunked["document_id"],chunked["document_checksum"],chunked["chunking_version"],chunked["configuration_hash"],chunked["configuration_json"],str(input_path.resolve()),source_status,len(chunked["parent_rows"]),len(chunked["child_rows"]),datetime.now(timezone.utc).isoformat()),
            )
            columns = "chunk_id,run_id,chunk_type,parent_chunk_id,source_id,document_id,document_checksum,source_validation_status,page_start,page_end,section_heading,chunk_index,text,sentence_start,sentence_end,token_count,overlap_sentence_count,overlap_metadata,boundary_reason,chunking_version,content_hash"
            insert = f"INSERT INTO hierarchical_chunks ({columns}) VALUES ({','.join('?' for _ in range(21))})"
            names = columns.split(",")
            for row in chunked["parent_rows"] + chunked["child_rows"]:
                connection.execute(insert, tuple(row[name] for name in names))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {"source_id":chunked["source_id"],"document_id":chunked["document_id"],"run_id":chunked["run_id"],"status":"PROCESSED","parent_chunks":len(chunked["parent_rows"]),"child_chunks":len(chunked["child_rows"]),"pages_covered":chunked["pages_covered"]}

    def _sample_chunks(self, *, source_id: str | None = None, limit: int = 6) -> list[dict[str, Any]]:
        query = "SELECT * FROM hierarchical_chunks"
        params: tuple[Any, ...] = ()
        if source_id:
            query += " WHERE source_id=?"
            params = (source_id,)
        query += " ORDER BY source_id,document_id,chunk_type,chunk_index LIMIT ?"
        rows = self.repository.connection.execute(query, (*params, limit)).fetchall()
        return [{**dict(row),"overlap_metadata":json.loads(row["overlap_metadata"])} for row in rows]


def build_report(database_path: str | Path, *, debug: bool = False, sample_limit: int = 6) -> dict[str, Any]:
    path = Path(database_path).resolve()
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "hierarchical_chunks" not in tables:
            chunks: list[sqlite3.Row] = []
            runs: list[sqlite3.Row] = []
        else:
            chunks = connection.execute("SELECT c.*,r.configuration_json FROM hierarchical_chunks c JOIN chunking_runs r ON r.run_id=c.run_id").fetchall()
            runs = connection.execute("SELECT * FROM chunking_runs WHERE status='COMPLETED'").fetchall()
        parents = [row for row in chunks if row["chunk_type"] == "PARENT"]
        children = [row for row in chunks if row["chunk_type"] == "CHILD"]
        sizes = [row["token_count"] for row in children]
        pages: set[tuple[str,str,int]] = set()
        for row in children:
            pages.update((row["source_id"],row["document_id"],p) for p in range(row["page_start"],row["page_end"]+1))
        missing = sum(not row["source_id"] or not row["document_id"] or not row["page_start"] or not row["page_end"] for row in chunks)
        over = 0
        for row in chunks:
            config = json.loads(row["configuration_json"])
            limit = config["max_parent_tokens"] if row["chunk_type"] == "PARENT" else config["max_child_tokens"]
            over += row["token_count"] > limit
        report = {
            "documents_processed": len(runs),
            "parent_chunks": len(parents),
            "child_chunks": len(children),
            "average_child_tokens": sum(sizes)/len(sizes) if sizes else 0,
            "min_child_tokens": min(sizes) if sizes else 0,
            "max_child_tokens": max(sizes) if sizes else 0,
            "average_overlap": sum(row["overlap_sentence_count"] for row in children)/len(children) if children else 0,
            "pages_covered": len(pages),
            "chunks_without_provenance": missing,
            "chunks_over_limit": over,
        }
        if debug:
            sample = connection.execute("SELECT source_id,document_id,page_start,page_end,section_heading,chunk_type,chunk_id,parent_chunk_id,text,overlap_sentence_count,overlap_metadata FROM hierarchical_chunks ORDER BY source_id,document_id,chunk_type,chunk_index LIMIT ?", (sample_limit,)).fetchall() if chunks else []
            report["sample_chunks"] = [{**dict(row),"overlap_metadata":json.loads(row["overlap_metadata"])} for row in sample]
        return report
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic sentence-based hierarchical chunking; no embeddings/retrieval")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Generate parent/child chunks from Phase 1 extraction JSON")
    run.add_argument("--db", default=str(DEFAULT_DATABASE))
    run.add_argument("--input-dir", default=str(DEFAULT_EXTRACTION_ROOT))
    run.add_argument("--source-id")
    run.add_argument("--debug", action="store_true")
    report = commands.add_parser("report", help="Report persisted hierarchical chunk statistics")
    report.add_argument("--db", default=str(DEFAULT_DATABASE))
    report.add_argument("--debug", action="store_true")
    report.add_argument("--sample-limit", type=int, default=6)
    args = parser.parse_args()
    if args.command == "report":
        result = build_report(args.db, debug=args.debug, sample_limit=args.sample_limit)
    else:
        service = ChunkingService(database_path=args.db, input_root=args.input_dir)
        try:
            result = service.run(source_id=args.source_id, debug=args.debug)
        finally:
            service.close()
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
