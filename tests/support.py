"""Shared helpers for tests that need stored filings and claim fixtures."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from axiomate.documents.ingest import ingest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DOCS = FIXTURES / "documents"
MANIFEST = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
GOOD = sorted((FIXTURES / "claims" / "good").glob("*.json"))
BAD = sorted((FIXTURES / "claims" / "bad").glob("*.json"))


def provenance(entry: dict) -> dict:
    filed = entry["filed_on"]
    return {
        "publisher_cik": entry["cik"],
        "document_type": "quarterly_report",
        "published_on": f"{filed[:4]}-{filed[4:6]}-{filed[6:]}",
        "format": entry["format"],
    }


def ingest_all(conn) -> dict[str, str]:
    """Ingest the ten sample filings; return document ids by file name."""
    return {e["file"]: ingest(conn, (DOCS / e["file"]).read_bytes(), **provenance(e)).document_id for e in MANIFEST}


def document_ids() -> dict[str, str]:
    return {e["file"]: e["sha256"] for e in MANIFEST}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def good(name: str) -> dict:
    return load(FIXTURES / "claims" / "good" / f"{name}.json")


def locate(conn, document_id: str, quote: str, occurrence: int = 1) -> tuple[int, int, int]:
    """Offsets of the n-th occurrence of `quote` and the index of the segment holding it."""
    text = conn.execute("SELECT canonical_text FROM document WHERE id = ?", (document_id,)).fetchone()[0]
    start = -1
    for _ in range(occurrence):
        start = text.index(quote, start + 1)
    end = start + len(quote)
    row = conn.execute(
        "SELECT idx FROM segment WHERE document_id = ? AND start <= ? AND end >= ?", (document_id, start, end)).fetchone()
    assert row is not None, "quote does not lie inside one segment"
    return start, end, row[0]


def submission(conn, fixture: dict) -> dict:
    """The flat claim a caller would submit for a good-claim fixture."""
    document_id = document_ids()[fixture["document"]]
    start, end, index = locate(conn, document_id, fixture["quote"], fixture["quote_occurrence"])
    return {
        **copy.deepcopy(fixture["claim"]),
        "document_id": document_id, "segment_index": index, "span_start": start, "span_end": end,
        "quote": fixture["quote"], "status": fixture["expected_status"],
        "flags": copy.deepcopy(fixture["flags"]), "assumptions": copy.deepcopy(fixture["assumptions"]),
    }


def corrupt(conn, claim: dict, operations: list[dict]) -> dict:
    """Apply the operations of a bad-claim fixture to a submission."""
    claim = copy.deepcopy(claim)
    for op in operations:
        kind = op["op"]
        if kind == "set":
            claim[op["path"].removeprefix("claim.")] = op["value"]
        elif kind == "delete":
            del claim[op["path"].removeprefix("claim.")]
        elif kind == "set_document_id":
            claim["document_id"] = op["value"]
        elif kind == "set_quote":
            claim["quote"] = op["value"]
        elif kind == "set_status":
            claim["status"] = op["value"]
        elif kind in ("shift_span", "extend_past_segment"):
            seg_start, seg_end = conn.execute(
                "SELECT start, end FROM segment WHERE document_id = ? AND idx = ?",
                (claim["document_id"], claim["segment_index"])).fetchone()
            if kind == "extend_past_segment":
                claim["span_end"] = seg_end + op["by"]
            else:
                # Shift forward when the span stays inside its segment, otherwise backward.
                by = op["by"] if claim["span_end"] + op["by"] <= seg_end else -op["by"]
                assert claim["span_start"] + by >= seg_start
                claim["span_start"] += by
                claim["span_end"] += by
        else:
            raise ValueError(kind)
    return claim
