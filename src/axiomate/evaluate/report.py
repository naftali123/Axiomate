"""The evaluation report: precision, coverage and pass rate for one data set.

The report is computed from the store and the tag files only. Every number is
given with its numerator, its denominator and, where one applies, the
threshold it is compared with (spec 002: SC-001 and SC-002).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any, Optional

from axiomate.errors import AxiomateError
from axiomate.evaluate.tagged import judge, locate
from axiomate.interpret.prompt import INSTRUCTION_VERSION, MODEL

THRESHOLDS = {"precision": "0.98", "coverage": "0.70"}
_CLAIM_FIELDS = ("id", "quote", "span_start", "span_end", "metric", "comparison", "value_low", "value_high",
                 "stated_value", "period_kind", "period_start", "period_end")


def _ratio(numerator: int, denominator: int, threshold: Optional[str] = None) -> dict[str, Any]:
    value = None
    if denominator:
        value = str((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN))
    result: dict[str, Any] = {"numerator": numerator, "denominator": denominator, "value": value}
    if threshold is not None:
        result["threshold"] = threshold
        result["met"] = value is not None and Decimal(value) >= Decimal(threshold)
    return result


def _document(conn: sqlite3.Connection, root: Path, entry: dict[str, str], instruction_version: str, model: str) -> dict[str, Any]:
    manifest = {e["file"]: e for e in json.loads((root / entry["filings"] / "manifest.json").read_text(encoding="utf-8"))}
    document_id = manifest[entry["file"]]["sha256"]
    row = conn.execute("SELECT original FROM document WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise AxiomateError("not_found", f"{entry['file']} is not in the store", "split")
    run_id = hashlib.sha256(f"{document_id}:{instruction_version}:{model}".encode("utf-8")).hexdigest()
    run = conn.execute("SELECT segments_selected, replies_failed FROM interpretation_run WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise AxiomateError("not_found", f"{entry['file']} has no interpretation run for these instructions and model", "split")
    facts = json.loads((root / entry["facts"] / (Path(entry["file"]).stem + ".json")).read_text(encoding="utf-8"))["facts"]
    _, spans = locate(row["original"].decode("utf-8"), [f["id"] for f in facts])
    for fact in facts:
        fact["start"], fact["end"] = spans.get(fact["id"], (None, None))
    claims = [dict(r) for r in conn.execute(
        f"SELECT {', '.join('c.' + f for f in _CLAIM_FIELDS)} FROM candidate_outcome o JOIN claim c ON c.id = o.claim_id"
        " WHERE o.run_id = ? AND o.outcome = 'passed' ORDER BY c.span_start, c.id", (run_id,))]
    outcomes = {r["outcome"]: r["n"] for r in conn.execute(
        "SELECT outcome, count(*) AS n FROM candidate_outcome WHERE run_id = ? GROUP BY outcome", (run_id,))}
    result = judge(claims, facts)
    result.update(file=entry["file"], document_id=document_id, segments_selected=run["segments_selected"],
                  replies_failed=run["replies_failed"], candidates=sum(outcomes.values()),
                  **{name: outcomes.get(name, 0) for name in ("passed", "flagged", "rejected")})
    return result


def build(conn: sqlite3.Connection, split: str, *, splits_path: str | Path = "eval/splits.json",
          instruction_version: Optional[str] = None, model: Optional[str] = None) -> dict[str, Any]:
    """The report for one side of the split file. Paths in the split file are relative to its repository root."""
    instruction_version = instruction_version or INSTRUCTION_VERSION
    model = model or MODEL
    splits_path = Path(splits_path)
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    if split not in splits:
        raise AxiomateError("not_found", f"the split file has no data set named {split}", "split")
    root = splits_path.resolve().parent.parent
    documents = [_document(conn, root, entry, instruction_version, model) for entry in splits[split]]
    total = lambda name: sum(d[name] for d in documents)  # noqa: E731
    precision = _ratio(total("agreeing"), total("citing"), THRESHOLDS["precision"])
    coverage = _ratio(total("covered"), total("tagged_figures"), THRESHOLDS["coverage"])
    return {
        "data_set": split, "filings": [d["file"] for d in documents],
        "instruction_version": instruction_version, "model": model,
        "tagged_figures": total("tagged_figures"), "tagged_not_visible": total("tagged_not_visible"),
        "claims_citing_a_tagged_figure": total("citing"),
        "precision": precision, "coverage": coverage,
        "pass_rate": _ratio(total("passed"), total("candidates")),
        "candidates": {name: total(name) for name in ("candidates", "passed", "flagged", "rejected")},
        "replies_failed": total("replies_failed"),
        "disagreements": [dict(d, file=doc["file"]) for doc in documents for d in doc["disagreements"]],
        "per_filing": [{k: d[k] for k in ("file", "tagged_figures", "citing", "agreeing", "covered", "candidates",
                                           "passed", "flagged", "rejected", "replies_failed")} for d in documents],
        "thresholds_met": bool(precision["met"] and coverage["met"]),
    }
