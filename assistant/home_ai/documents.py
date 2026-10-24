from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pypdf import Configuration, PdfReader, apply_configuration


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_PAGE_CONTENT_BYTES = 2 * 1024 * 1024
MAX_DOCUMENT_PDF_CONTENT_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 500_000
CHUNK_CHARACTERS = 1_200
CHUNK_OVERLAP = 160

_PDF_CONFIGURATION = Configuration(
    maximum_declared_stream_length=MAX_UPLOAD_BYTES,
    array_based_stream_maximum_output_length=MAX_PAGE_CONTENT_BYTES,
    jbig2_maximum_output_length=MAX_PAGE_CONTENT_BYTES,
    lzw_maximum_output_length=MAX_PAGE_CONTENT_BYTES,
    run_length_maximum_output_length=MAX_PAGE_CONTENT_BYTES,
    zlib_maximum_output_length=MAX_PAGE_CONTENT_BYTES,
    brotli_maximum_output_length=MAX_PAGE_CONTENT_BYTES,
    image_maximum_buffer_size=MAX_PAGE_CONTENT_BYTES,
    stream_decoding_work_maximum_length=MAX_PAGE_CONTENT_BYTES,
    xmp_maximum_input_length=MAX_PAGE_CONTENT_BYTES,
)


class DocumentError(ValueError):
    """A document could not be safely ingested or searched."""


@dataclass(frozen=True)
class DocumentSummary:
    document_id: str
    filename: str
    pages: int
    passages: int


@dataclass(frozen=True)
class Passage:
    passage_id: str
    document_id: str
    filename: str
    page: int
    text: str

    @property
    def citation(self) -> str:
        return f"[{self.filename}, p. {self.page}]"


def _safe_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable() and ch not in "\r\n\t")
    name = name[:120].strip()
    if not name or name in {".", ".."}:
        raise DocumentError("Choose a filename for the document.")
    return name


def _split_text(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + CHUNK_CHARACTERS, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + CHUNK_CHARACTERS // 2, end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def _extract_pdf(data: bytes) -> list[str]:
    try:
        with apply_configuration(_PDF_CONFIGURATION):
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise DocumentError("Encrypted PDFs are not supported.")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise DocumentError(f"PDFs are limited to {MAX_PDF_PAGES} pages.")
            pages: list[str] = []
            total_chars = 0
            total_content_bytes = 0
            for page in reader.pages:
                contents = page.get_contents()
                if contents is not None:
                    content_bytes = len(contents.get_data())
                    if content_bytes > MAX_PAGE_CONTENT_BYTES:
                        raise DocumentError("A PDF page has an oversized content stream.")
                    total_content_bytes += content_bytes
                    if total_content_bytes > MAX_DOCUMENT_PDF_CONTENT_BYTES:
                        raise DocumentError("Decoded PDF content exceeds the document size limit.")
                text = page.extract_text() or ""
                total_chars += len(text)
                if total_chars > MAX_EXTRACTED_CHARACTERS:
                    raise DocumentError("Extracted PDF text exceeds the size limit.")
                pages.append(text)
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("This PDF could not be read. Try an unencrypted text-based PDF.") from exc
    if not any(page.strip() for page in pages):
        raise DocumentError("No selectable text was found. Scanned PDFs and OCR are not supported yet.")
    return pages


class DocumentStore:
    """Small local SQLite FTS5 index with page-aware citations."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        database_string = str(database)
        if database_string != ":memory:":
            database_path = Path(database_string)
            database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name == "posix":
                os.chmod(database_path.parent, 0o700)
                if not database_path.exists():
                    descriptor = os.open(database_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(descriptor)
                os.chmod(database_path, 0o600)
        self._connection = sqlite3.connect(database_string, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        try:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS documents ("
                "document_id TEXT PRIMARY KEY, filename TEXT NOT NULL, pages INTEGER NOT NULL, "
                "created_at TEXT NOT NULL)"
            )
            self._connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5("
                "passage_id UNINDEXED, document_id UNINDEXED, filename UNINDEXED, "
                "page UNINDEXED, text, tokenize='unicode61')"
            )
            self._connection.commit()
        except sqlite3.OperationalError as exc:
            self._connection.close()
            raise RuntimeError("This Python SQLite build must include FTS5.") from exc

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def add_file(self, filename: str, content: bytes) -> DocumentSummary:
        if len(content) > MAX_UPLOAD_BYTES:
            raise DocumentError("Files are limited to 10 MiB.")
        safe_name = _safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix == ".txt":
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise DocumentError("Text files must be UTF-8 encoded.") from exc
            page_text = [text]
        elif suffix == ".pdf":
            page_text = _extract_pdf(content)
        else:
            raise DocumentError("Only .txt and text-based .pdf files are supported.")

        pieces: list[tuple[int, str]] = []
        for page_number, text in enumerate(page_text, start=1):
            pieces.extend((page_number, chunk) for chunk in _split_text(text))
        if not pieces:
            raise DocumentError("The document contains no searchable text.")

        document_id = hashlib.sha256(content).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM passages WHERE document_id = ?", (document_id,))
            self._connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            self._connection.execute(
                "INSERT INTO documents(document_id, filename, pages, created_at) VALUES (?, ?, ?, ?)",
                (document_id, safe_name, len(page_text), created_at),
            )
            rows = [
                (f"{document_id[:16]}-p{page}-c{index}", document_id, safe_name, page, text)
                for index, (page, text) in enumerate(pieces, start=1)
            ]
            self._connection.executemany(
                "INSERT INTO passages(passage_id, document_id, filename, page, text) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return DocumentSummary(document_id, safe_name, len(page_text), len(pieces))

    def list_documents(self) -> list[DocumentSummary]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT d.document_id, d.filename, d.pages, COUNT(p.passage_id) AS passages "
                "FROM documents d LEFT JOIN passages p ON p.document_id = d.document_id "
                "GROUP BY d.document_id, d.filename, d.pages ORDER BY d.created_at DESC"
            ).fetchall()
        return [
            DocumentSummary(row["document_id"], row["filename"], row["pages"], row["passages"])
            for row in rows
        ]

    def delete(self, document_id: str) -> bool:
        if not re.fullmatch(r"[a-f0-9]{64}", document_id):
            return False
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM passages WHERE document_id = ?", (document_id,))
            cursor = self._connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            return cursor.rowcount > 0

    def search(self, query: str, limit: int = 5) -> list[Passage]:
        tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)[:16]
        if not tokens:
            return []
        fts_query = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
        with self._lock:
            rows = self._connection.execute(
                "SELECT passage_id, document_id, filename, page, text "
                "FROM passages WHERE passages MATCH ? ORDER BY bm25(passages) LIMIT ?",
                (fts_query, max(1, min(limit, 10))),
            ).fetchall()
        return [
            Passage(row["passage_id"], row["document_id"], row["filename"], int(row["page"]), row["text"])
            for row in rows
        ]
