"""Draw the prose sample: passed claims from running prose, for a person to judge.

Claims in sentences have no tags to compare with. A fixed rule picks about
`size` of them: all passed claims whose segment is a sentence, in the order of
the split file and then of the text, and from that list every n-th one, where
n is the list length divided by `size`, rounded down, and at least 1. The rule
uses nothing about a claim's content, so the choice cannot favour easy cases.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from axiomate.errors import AxiomateError
from axiomate.interpret.prompt import INSTRUCTION_VERSION, MODEL

_FIELDS = ("metric", "value_kind", "value_low", "value_high", "unit", "currency", "comparison", "period_start",
           "period_end", "baseline_start", "baseline_end", "basis", "nature", "polarity")


def prose_sample(conn: sqlite3.Connection, split: str, *, size: int = 30, splits_path: str | Path = "eval/splits.json",
                 instruction_version: Optional[str] = None, model: Optional[str] = None) -> dict[str, Any]:
    instruction_version = instruction_version or INSTRUCTION_VERSION
    model = model or MODEL
    splits_path = Path(splits_path)
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    if split not in splits:
        raise AxiomateError("not_found", f"the split file has no data set named {split}", "split")
    root = splits_path.resolve().parent.parent
    population: list[dict[str, Any]] = []
    for entry in splits[split]:
        manifest = {e["file"]: e for e in json.loads((root / entry["filings"] / "manifest.json").read_text(encoding="utf-8"))}
        document_id = manifest[entry["file"]]["sha256"]
        run_id = hashlib.sha256(f"{document_id}:{instruction_version}:{model}".encode("utf-8")).hexdigest()
        if conn.execute("SELECT 1 FROM interpretation_run WHERE id = ?", (run_id,)).fetchone() is None:
            raise AxiomateError("not_found", f"{entry['file']} has no interpretation run for these instructions and model", "split")
        text = conn.execute("SELECT canonical_text FROM document WHERE id = ?", (document_id,)).fetchone()[0]
        for row in conn.execute(
                f"SELECT c.id, c.quote, s.start, s.end, {', '.join('c.' + f for f in _FIELDS)}"
                " FROM candidate_outcome o JOIN claim c ON c.id = o.claim_id"
                " JOIN segment s ON s.document_id = c.document_id AND s.idx = c.segment_index"
                " WHERE o.run_id = ? AND o.outcome = 'passed' AND s.kind = 'sentence' ORDER BY c.span_start, c.id", (run_id,)):
            assumptions = [r["statement"] for r in conn.execute(
                "SELECT statement FROM assumption WHERE claim_id = ? ORDER BY claim_version, seq", (row["id"],))]
            population.append({"file": entry["file"], "claim_id": row["id"], "sentence": text[row["start"]:row["end"]],
                               "quote": row["quote"], "reading": {f: row[f] for f in _FIELDS}, "assumptions": assumptions})
    step = max(len(population) // size, 1) if size > 0 else 1
    return {"data_set": split, "population": len(population), "step": step, "sample": population[::step][:size]}
