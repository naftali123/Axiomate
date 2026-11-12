"""Ingestion: provenance checks, hashing, deduplication and storage of a document."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import date

from axiomate.documents.html_text import EXTRACTOR_VERSION, canonical_from_html, canonical_from_text
from axiomate.documents.segment import SEGMENTER_VERSION, segment
from axiomate.errors import AxiomateError
from axiomate.store import db

DOCUMENT_TYPES = ("earnings_release", "annual_report", "quarterly_report", "investor_statement", "other")
FISCAL_PERIODS = ("Q1", "Q2", "Q3", "Q4", "H1", "9M", "FY")
FORMATS = ("text", "html")
LANGUAGES = ("en",)

_PROVENANCE = ("publisher_cik", "document_type", "published_on", "fiscal_year", "fiscal_period", "format", "language")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    segments: int
    created: bool


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _check_provenance(publisher_cik, document_type, published_on, fiscal_year, fiscal_period, format, language) -> dict:
    """Return the provenance in stored form, or raise naming the offending field."""
    for field, value in (("publisher_cik", publisher_cik), ("published_on", published_on), ("document_type", document_type)):
        if _missing(value):
            raise AxiomateError("missing_provenance", f"{field} is required", field)
    if _missing(format) or format not in FORMATS:
        raise AxiomateError("unsupported_format", f"format must be one of {', '.join(FORMATS)}", "format")
    if _missing(language) or language not in LANGUAGES:
        raise AxiomateError("unsupported_language", "only English (en) documents are accepted", "language")

    cik = str(publisher_cik).strip()
    if not (cik.isascii() and cik.isdigit() and len(cik) <= 10):
        raise AxiomateError("invalid_provenance", "publisher_cik must be an SEC Central Index Key of up to ten digits", "publisher_cik")
    if document_type not in DOCUMENT_TYPES:
        raise AxiomateError("invalid_provenance", f"document_type must be one of {', '.join(DOCUMENT_TYPES)}", "document_type")
    if isinstance(published_on, date):
        published = published_on.isoformat()
    else:
        published = str(published_on).strip()
        try:
            if not _ISO_DATE.fullmatch(published):
                raise ValueError
            date.fromisoformat(published)
        except ValueError:
            raise AxiomateError("invalid_provenance", "published_on must be a date written YYYY-MM-DD", "published_on") from None
    year = None
    if not _missing(fiscal_year):
        text = str(fiscal_year).strip()
        if isinstance(fiscal_year, bool) or not (text.isascii() and text.isdigit() and 1900 <= int(text) <= 2100):
            raise AxiomateError("invalid_provenance", "fiscal_year must be a year between 1900 and 2100", "fiscal_year")
        year = int(text)
    period = None
    if not _missing(fiscal_period):
        if fiscal_period not in FISCAL_PERIODS:
            raise AxiomateError("invalid_provenance", f"fiscal_period must be one of {', '.join(FISCAL_PERIODS)}", "fiscal_period")
        period = fiscal_period
    return {
        "publisher_cik": cik.zfill(10), "document_type": document_type, "published_on": published,
        "fiscal_year": year, "fiscal_period": period, "format": format, "language": language,
    }


def ingest(conn: sqlite3.Connection, data: bytes, *, publisher_cik, document_type, published_on, format,
           fiscal_year=None, fiscal_period=None, language="en") -> IngestResult:
    """Store a document unchanged, with its canonical text and segments.

    Identical bytes with identical provenance return the existing record;
    identical bytes with different provenance are refused.
    """
    provenance = _check_provenance(publisher_cik, document_type, published_on, fiscal_year, fiscal_period, format, language)
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        raise AxiomateError("unsupported_format", "the document is not UTF-8 text", "format") from None
    canonical = canonical_from_html(decoded) if provenance["format"] == "html" else canonical_from_text(decoded)
    segments = segment(canonical, provenance["format"])
    if not segments:
        raise AxiomateError("empty_document", "the document contains no text", None)
    document_id = hashlib.sha256(data).hexdigest()

    with db.transaction(conn):
        existing = conn.execute(f"SELECT {', '.join(_PROVENANCE)} FROM document WHERE id = ?", (document_id,)).fetchone()
        if existing is not None:
            for field in _PROVENANCE:
                if existing[field] != provenance[field]:
                    raise AxiomateError(
                        "provenance_conflict",
                        f"this document is already stored with {field} = {existing[field]!r}", field)
            count = conn.execute("SELECT count(*) FROM segment WHERE document_id = ?", (document_id,)).fetchone()[0]
            return IngestResult(document_id, count, created=False)
        conn.execute(
            "INSERT INTO document (id, publisher_cik, document_type, published_on, fiscal_year, fiscal_period,"
            " format, language, original, canonical_text, extractor_version, segmenter_version)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (document_id, *(provenance[f] for f in _PROVENANCE), data, canonical, EXTRACTOR_VERSION, SEGMENTER_VERSION))
        conn.executemany(
            "INSERT INTO segment (document_id, idx, start, end, kind) VALUES (?, ?, ?, ?, ?)",
            [(document_id, index, s.start, s.end, s.kind) for index, s in enumerate(segments)])
    return IngestResult(document_id, len(segments), created=True)


def get_document(conn: sqlite3.Connection, document_id: str) -> dict:
    """Provenance, canonical text and segment count of a stored document."""
    row = conn.execute(
        f"SELECT id, {', '.join(_PROVENANCE)}, canonical_text, extractor_version, segmenter_version"
        " FROM document WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise AxiomateError("not_found", f"no document with id {document_id}", "document_id")
    document = dict(row)
    document["document_id"] = document.pop("id")
    document["segments"] = conn.execute("SELECT count(*) FROM segment WHERE document_id = ?", (document_id,)).fetchone()[0]
    return document


def get_original(conn: sqlite3.Connection, document_id: str) -> bytes:
    """The original bytes of a stored document, exactly as ingested."""
    row = conn.execute("SELECT original FROM document WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise AxiomateError("not_found", f"no document with id {document_id}", "document_id")
    return bytes(row["original"])


def get_segment(conn: sqlite3.Connection, document_id: str, index: int) -> dict:
    """One segment of a stored document, with its offsets and text."""
    row = conn.execute(
        "SELECT s.idx, s.start, s.end, s.kind, substr(d.canonical_text, s.start + 1, s.end - s.start) AS text"
        " FROM segment s JOIN document d ON d.id = s.document_id WHERE s.document_id = ? AND s.idx = ?",
        (document_id, index)).fetchone()
    if row is None:
        get_document(conn, document_id)
        raise AxiomateError("not_found", f"document has no segment {index}", "segment")
    return {"document_id": document_id, "index": row["idx"], "start": row["start"], "end": row["end"],
            "kind": row["kind"], "text": row["text"]}
