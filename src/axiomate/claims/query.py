"""Reading claims back from the store."""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from axiomate.errors import AxiomateError


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
