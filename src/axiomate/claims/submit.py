"""Claim submission: the only way a claim enters the store.

A claim is stored only if it passes, in this order:
1. the schema (`claims/schema.py`);
2. the status check: a submitted status must equal the derived one;
3. grounding: the document exists, the claim's `said_on` is the document's
   publication date, the span lies inside one segment, and the stored text
   between the offsets equals the quote exactly.

Identity and versions. A claim's id is the SHA-256 of its document id, span
offsets and metric at first submission. Submitting the same content again
returns the stored claim. Different content for an existing id is refused
unless it is sent as a correction (`supersedes`), which adds the next version
under the same id and leaves earlier versions in place.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

from axiomate.claims.schema import CONTENT_FIELDS, SCHEMA_VERSION, Claim, parse_claim
from axiomate.claims.status import derive_status
from axiomate.errors import AxiomateError
from axiomate.store import db

_SOURCE_FIELDS = ("document_id", "segment_index", "span_start", "span_end", "quote", "said_on")
_CLAIM_COLUMNS = ("id", "version", "schema_version", *CONTENT_FIELDS, *_SOURCE_FIELDS, "status")


@dataclass(frozen=True)
class SubmitResult:
    claim_id: str
    version: int
    status: str
    created: bool


def claim_id_for(document_id: str, span_start: int, span_end: int, metric: Optional[str]) -> str:
    return hashlib.sha256(f"{document_id}:{span_start}:{span_end}:{metric or ''}".encode("utf-8")).hexdigest()


def _ground(conn: sqlite3.Connection, claim: Claim) -> int:
    """Check the claim against its source document; return the segment index."""
    document = conn.execute(
        "SELECT published_on, canonical_text FROM document WHERE id = ?", (claim.document_id,)).fetchone()
    if document is None:
        raise AxiomateError("document_not_found", f"no document with id {claim.document_id}", "document_id")
    if claim.said_on != document["published_on"]:
        raise AxiomateError(
            "said_on_mismatch", f"said_on must be the document's publication date, {document['published_on']}", "said_on")
    if claim.segment_index is None:
        row = conn.execute(
            "SELECT idx FROM segment WHERE document_id = ? AND start <= ? AND end > ? ORDER BY idx LIMIT 1",
            (claim.document_id, claim.span_start, claim.span_start)).fetchone()
        if row is None:
            raise AxiomateError("span_outside_segment", "span_start does not lie inside any segment", "span_start")
        index, named = row["idx"], False
    else:
        index, named = claim.segment_index, True
    segment = conn.execute(
        "SELECT start, end FROM segment WHERE document_id = ? AND idx = ?", (claim.document_id, index)).fetchone()
    if segment is None:
        raise AxiomateError("span_outside_segment", f"the document has no segment {index}", "segment_index")
    if claim.span_start < segment["start"] or claim.span_start >= segment["end"]:
        raise AxiomateError(
            "span_outside_segment", f"the span does not start inside segment {index}",
            "segment_index" if named else "span_start")
    if claim.span_end > segment["end"]:
        raise AxiomateError("span_outside_segment", f"the span runs past the end of segment {index}", "span_end")
    if document["canonical_text"][claim.span_start:claim.span_end] != claim.quote:
        raise AxiomateError("span_mismatch", "the stored text at the span is not the quote", "quote")
    return index


def _content(claim: Claim, segment_index: int, status: str) -> dict[str, Any]:
    record = {name: getattr(claim, name) for name in (*CONTENT_FIELDS, *_SOURCE_FIELDS)}
    record["segment_index"] = segment_index
    record["status"] = status
    record["flags"] = [(f.reason, f.field, int(f.resolved), f.note) for f in claim.flags]
    record["assumptions"] = [(a.statement, a.field, a.origin) for a in claim.assumptions]
    return record


def _stored_content(conn: sqlite3.Connection, claim_id: str, version: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM claim WHERE id = ? AND version = ?", (claim_id, version)).fetchone()
    record = {name: row[name] for name in (*CONTENT_FIELDS, *_SOURCE_FIELDS, "status")}
    record["flags"] = [tuple(r) for r in conn.execute(
        "SELECT reason, field, resolved, note FROM flag WHERE claim_id = ? AND claim_version = ? ORDER BY seq",
        (claim_id, version))]
    record["assumptions"] = [tuple(r) for r in conn.execute(
        "SELECT statement, field, origin FROM assumption WHERE claim_id = ? AND claim_version = ? ORDER BY seq",
        (claim_id, version))]
    return record


def submit(conn: sqlite3.Connection, data: Any, *, supersedes: Optional[str] = None) -> SubmitResult:
    """Validate, ground and store one claim, or raise AxiomateError and store nothing."""
    claim = parse_claim(data)
    status = derive_status(claim.flags, claim.assumptions)
    if claim.status is not None and claim.status != status:
        raise AxiomateError(
            "status_mismatch", f"the status follows from the flags and assumptions and is {status}", "status")

    with db.transaction(conn):
        segment_index = _ground(conn, claim)
        content = _content(claim, segment_index, status)
        claim_id = supersedes or claim_id_for(claim.document_id, claim.span_start, claim.span_end, claim.metric)
        latest = conn.execute("SELECT max(version) FROM claim WHERE id = ?", (claim_id,)).fetchone()[0]
        if supersedes is not None and latest is None:
            raise AxiomateError("not_found", f"no claim with id {supersedes} to correct", "supersedes")
        if latest is not None:
            if _stored_content(conn, claim_id, latest) == content:
                return SubmitResult(claim_id, latest, status, created=False)
            if supersedes is None:
                raise AxiomateError(
                    "claim_exists",
                    f"a different claim is already stored for this span and metric; to correct it, supersede {claim_id}",
                    None)
        version = (latest or 0) + 1
        values = {**content, "id": claim_id, "version": version, "schema_version": SCHEMA_VERSION}
        conn.execute(
            f"INSERT INTO claim ({', '.join(_CLAIM_COLUMNS)}) VALUES ({', '.join('?' * len(_CLAIM_COLUMNS))})",
            [values[name] for name in _CLAIM_COLUMNS])
        conn.executemany(
            "INSERT INTO flag (claim_id, claim_version, seq, reason, field, resolved, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(claim_id, version, seq, *flag) for seq, flag in enumerate(content["flags"])])
        conn.executemany(
            "INSERT INTO assumption (claim_id, claim_version, seq, statement, field, origin) VALUES (?, ?, ?, ?, ?, ?)",
            [(claim_id, version, seq, *item) for seq, item in enumerate(content["assumptions"])])
    return SubmitResult(claim_id, version, status, created=True)
