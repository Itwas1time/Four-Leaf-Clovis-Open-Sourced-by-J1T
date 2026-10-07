"""
Document ingestion and chunking for historical text analysis.

Historical documents arrive in many formats — scanned-and-OCR'd PDFs of
19th-century survey reports, plain-text transcriptions of expedition journals,
HTML pages from digital archives, DOCX files from modern researchers. This
module normalizes all of them into clean, chunked text with provenance
metadata so downstream extractors never worry about format.

Chunking preserves paragraph boundaries because spatial references often
span multiple sentences ("We traveled north along the river for two days
and arrived at a large mound complex near the confluence with a smaller
stream flowing from the east"). Splitting mid-paragraph would destroy
these multi-sentence references.
"""

from __future__ import annotations

import hashlib
import html
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocumentMetadata:
    """Source metadata for an ingested document."""

    document_id: str = ""
    title: str = ""
    author: str = ""
    date: str = ""
    source_path: str = ""
    format: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.document_id:
            self.document_id = str(uuid.uuid4())


@dataclass
class TextChunk:
    """A passage of text linked back to its source document."""

    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    word_count: int
    char_offset_start: int
    char_offset_end: int
    metadata: DocumentMetadata | None = None


class DocumentIngestor:
    """
    Ingest documents in PDF, plain text, HTML, and DOCX formats.

    Extracts clean text, attaches source metadata, and chunks into
    ~500-word passages that preserve paragraph boundaries. Uses Python
    builtins where possible; PDF extraction falls back gracefully if
    pymupdf or pdfplumber are unavailable.
    """

    DEFAULT_CHUNK_WORDS: int = 500

    def __init__(self, chunk_words: int = DEFAULT_CHUNK_WORDS) -> None:
        self.chunk_words = chunk_words

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(
        self,
        source: str | Path,
        *,
        title: str = "",
        author: str = "",
        date: str = "",
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """
        Ingest a file or raw text string and return chunked passages.

        Args:
            source: File path (str/Path) or raw text string.
            title: Document title override.
            author: Document author override.
            date: Document date override.
            extra_metadata: Arbitrary extra metadata dict.

        Returns:
            Ordered list of TextChunk objects linked to a common document_id.
        """
        if isinstance(source, Path) or (isinstance(source, str) and Path(source).suffix):
            path = Path(source)
            if path.is_file():
                return self._ingest_file(
                    path, title=title, author=author, date=date,
                    extra_metadata=extra_metadata,
                )

        # Treat as raw text
        meta = DocumentMetadata(
            title=title or "raw_text",
            author=author,
            date=date,
            format="text",
            extra=extra_metadata or {},
        )
        return self._chunk_text(str(source), meta)

    def ingest_text(
        self,
        text: str,
        *,
        title: str = "",
        author: str = "",
        date: str = "",
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk]:
        """Directly ingest a raw text string."""
        meta = DocumentMetadata(
            title=title or "raw_text",
            author=author,
            date=date,
            format="text",
            extra=extra_metadata or {},
        )
        return self._chunk_text(text, meta)

    # ------------------------------------------------------------------
    # File dispatch
    # ------------------------------------------------------------------

    def _ingest_file(
        self,
        path: Path,
        *,
        title: str,
        author: str,
        date: str,
        extra_metadata: dict[str, Any] | None,
    ) -> list[TextChunk]:
        suffix = path.suffix.lower()
        extractors = {
            ".pdf": self._extract_pdf,
            ".txt": self._extract_plaintext,
            ".html": self._extract_html,
            ".htm": self._extract_html,
            ".docx": self._extract_docx,
        }

        extractor = extractors.get(suffix)
        if extractor is None:
            raise ValueError(
                f"Unsupported file format '{suffix}'. "
                f"Supported: {', '.join(extractors.keys())}"
            )

        raw_text = extractor(path)
        meta = DocumentMetadata(
            title=title or path.stem,
            author=author,
            date=date,
            source_path=str(path.resolve()),
            format=suffix.lstrip("."),
            extra=extra_metadata or {},
        )
        return self._chunk_text(raw_text, meta)

    # ------------------------------------------------------------------
    # Format-specific extractors
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_plaintext(path: Path) -> str:
        """Read plain text files with encoding fallback."""
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode {path} with any supported encoding")

    @staticmethod
    def _extract_html(path: Path) -> str:
        """
        Strip HTML to clean text.

        Many digital archive pages (e.g., Smithsonian BAE reports hosted
        online) are saved as HTML. We strip tags but preserve paragraph
        breaks so chunking can respect document structure.
        """
        raw = path.read_text(encoding="utf-8", errors="replace")
        # Remove script/style blocks
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        # Convert block-level tags to newlines
        raw = re.sub(r"<(?:br|p|div|h[1-6]|li|tr)[^>]*>", "\n", raw, flags=re.IGNORECASE)
        # Strip remaining tags
        raw = re.sub(r"<[^>]+>", "", raw)
        # Decode HTML entities
        raw = html.unescape(raw)
        # Collapse whitespace but keep paragraph breaks
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        """
        Extract text from PDF using pymupdf or pdfplumber, with graceful fallback.

        Many critical archaeological sources exist only as scanned PDFs of
        19th/early-20th century reports (BAE bulletins, state survey reports).
        OCR quality varies wildly, but even imperfect text is valuable for
        identifying spatial references.
        """
        # Try pymupdf (fitz) first — fastest and most reliable
        try:
            import fitz  # pymupdf

            doc = fitz.open(str(path))
            pages: list[str] = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            return "\n\n".join(pages)
        except ImportError:
            pass

        # Try pdfplumber as fallback
        try:
            import pdfplumber

            pages = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            pass

        raise ImportError(
            "PDF extraction requires either 'pymupdf' or 'pdfplumber'. "
            "Install one with: pip install pymupdf  OR  pip install pdfplumber"
        )

    @staticmethod
    def _extract_docx(path: Path) -> str:
        """
        Extract text from DOCX by reading the XML directly.

        Uses zipfile and defusedxml to reject unsafe XML declarations.
        DOCX is a ZIP containing XML — we
        pull paragraph text from word/document.xml.
        """
        import zipfile
        import defusedxml.ElementTree as ET

        with zipfile.ZipFile(str(path), "r") as zf:
            if "word/document.xml" not in zf.namelist():
                raise ValueError(f"{path} does not appear to be a valid DOCX file")

            if zf.getinfo("word/document.xml").file_size > 5_000_000:
                raise ValueError("DOCX document XML exceeds the 5 MB ingestion limit")
            xml_content = zf.read("word/document.xml")

        tree = ET.fromstring(xml_content)
        # Word XML namespace
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

        paragraphs: list[str] = []
        for para in tree.iter(f"{{{ns['w']}}}p"):
            texts = [
                node.text
                for node in para.iter(f"{{{ns['w']}}}t")
                if node.text
            ]
            if texts:
                paragraphs.append("".join(texts))

        return "\n\n".join(paragraphs)

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def _chunk_text(self, text: str, meta: DocumentMetadata) -> list[TextChunk]:
        """
        Split text into ~500-word chunks, preserving paragraph boundaries.

        The algorithm groups consecutive paragraphs until the word count
        exceeds the target. This avoids splitting spatial references that
        span multiple sentences within a paragraph.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return []

        chunks: list[TextChunk] = []
        current_paragraphs: list[str] = []
        current_word_count = 0
        char_offset = 0

        for para in paragraphs:
            para_words = len(para.split())

            # If adding this paragraph would exceed target and we already
            # have content, finalize the current chunk first
            if current_word_count + para_words > self.chunk_words and current_paragraphs:
                chunk_text = "\n\n".join(current_paragraphs)
                chunk_id = self._make_chunk_id(meta.document_id, len(chunks))
                chunks.append(TextChunk(
                    chunk_id=chunk_id,
                    document_id=meta.document_id,
                    text=chunk_text,
                    chunk_index=len(chunks),
                    word_count=current_word_count,
                    char_offset_start=char_offset,
                    char_offset_end=char_offset + len(chunk_text),
                    metadata=meta,
                ))
                char_offset += len(chunk_text) + 2  # +2 for paragraph separator
                current_paragraphs = []
                current_word_count = 0

            current_paragraphs.append(para)
            current_word_count += para_words

        # Final chunk
        if current_paragraphs:
            chunk_text = "\n\n".join(current_paragraphs)
            chunk_id = self._make_chunk_id(meta.document_id, len(chunks))
            chunks.append(TextChunk(
                chunk_id=chunk_id,
                document_id=meta.document_id,
                text=chunk_text,
                chunk_index=len(chunks),
                word_count=current_word_count,
                char_offset_start=char_offset,
                char_offset_end=char_offset + len(chunk_text),
                metadata=meta,
            ))

        return chunks

    @staticmethod
    def _make_chunk_id(document_id: str, index: int) -> str:
        """Deterministic chunk ID from document ID and chunk index."""
        raw = f"{document_id}:{index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
