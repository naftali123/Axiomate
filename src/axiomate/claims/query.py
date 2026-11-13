"""Reading claims back from the store."""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from axiomate.claims.schema import METRICS
from axiomate.errors import AxiomateError

FISCAL_PERIODS = ("Q1", "Q2", "Q3", "Q4", "H1", "9M", "FY")
# Stable order of query results (plan, design decision 12).
_ORDER = "c.period_end, c.said_on, c.document_id, c.segment_index, c.id, c.version"


def _with_parts(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    claim = dict(row)
    claim["claim_id"] = claim.pop("id")
    key = (claim["claim_id"], claim["version"])
    claim["flags"] = [
        {"reason": r["reason"], "field": r["field"], "resolved": bool(r["resolved"]), "note": r["note"]}
        for r in conn.execute(
            "SELECT reason, field, resolved, note FROM flag WHERE claim_id = ? AND claim_version = ? ORDER BY seq", key)]
    claim["assumptions"] = [
        {"statement": r["statement"], "field": r["field"], "origin": r["origin"]}
        for r in conn.execute(
            "SELECT statement, field, origin FROM assumption WHERE claim_id = ? AND claim_version = ? ORDER BY seq", key)]
    return claim


def get_claim(conn: sqlite3.Connection, claim_id: str, version: Optional[int] = None) -> dict[str, Any]:
    """One claim with its flags and assumptions; the latest version unless one is named."""
    if version is None:
        row = conn.execute("SELECT * FROM claim WHERE id = ? ORDER BY version DESC LIMIT 1", (claim_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM claim WHERE id = ? AND version = ?", (claim_id, version)).fetchone()
    if row is None:
        wanted = f"claim {claim_id}" + (f" version {version}" if version is not None else "")
        raise AxiomateError("not_found", f"no {wanted}", "claim_id")
    return _with_parts(conn, row)


def list_claims(conn: sqlite3.Connection, *, company_cik: Any, metric: Any, fiscal_year: Any,
                fiscal_period: Optional[str] = None, all_versions: bool = False) -> list[dict[str, Any]]:
    """Claims about one company, metric and fiscal year (optionally one period), in the stable order.

    Only the latest version of each claim is considered unless `all_versions`
    is set, so a claim corrected to another period no longer answers for the
    old one.
    """
    cik = "" if company_cik is None else str(company_cik).strip()
    if not (cik.isascii() and cik.isdigit() and len(cik) <= 10):
        raise AxiomateError("schema_invalid", "company_cik must be an SEC Central Index Key of up to ten digits", "company_cik")
    if not isinstance(metric, str) or metric not in METRICS:
        code = "unknown_metric" if isinstance(metric, str) and metric else "schema_invalid"
        raise AxiomateError(code, f"metric must be one of {', '.join(METRICS)}", "metric")
    year = "" if fiscal_year is None or isinstance(fiscal_year, bool) else str(fiscal_year).strip()
    if not (year.isascii() and year.isdigit() and 1900 <= int(year) <= 2100):
        raise AxiomateError("schema_invalid", "fiscal_year must be a year between 1900 and 2100", "fiscal_year")
    if fiscal_period is not None and fiscal_period not in FISCAL_PERIODS:
        raise AxiomateError("schema_invalid", f"fiscal_period must be one of {', '.join(FISCAL_PERIODS)}", "fiscal_period")

    where = ["c.company_cik = ?", "c.metric = ?", "c.fiscal_year = ?"]
    values: list[Any] = [cik.zfill(10), metric, int(year)]
    if fiscal_period is not None:
        where.append("c.fiscal_period = ?")
        values.append(fiscal_period)
    if not all_versions:
        where.append("c.version = (SELECT max(version) FROM claim WHERE id = c.id)")
    rows = conn.execute(f"SELECT c.* FROM claim c WHERE {' AND '.join(where)} ORDER BY {_ORDER}", values).fetchall()
    return [_with_parts(conn, row) for row in rows]


def claim_source(conn: sqlite3.Connection, claim_id: str, version: Optional[int] = None) -> dict[str, Any]:
    """Where a claim comes from: its document, publication date, sentence and exact span."""
    claim = get_claim(conn, claim_id, version)
    row = conn.execute(
        "SELECT d.published_on, substr(d.canonical_text, s.start + 1, s.end - s.start) AS segment_text"
        " FROM document d JOIN segment s ON s.document_id = d.id WHERE d.id = ? AND s.idx = ?",
        (claim["document_id"], claim["segment_index"])).fetchone()
    return {
        "claim_id": claim["claim_id"], "version": claim["version"], "document_id": claim["document_id"],
        "published_on": row["published_on"], "segment_index": claim["segment_index"],
        "segment_text": row["segment_text"], "span_start": claim["span_start"], "span_end": claim["span_end"],
        "quote": claim["quote"],
    }
