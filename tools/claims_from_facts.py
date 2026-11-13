"""Build correct claims mechanically from the figures tagged in the HTML filings.

For every tagged figure of the four metrics that is visible in the stored
text, one claim is written whose quote is the figure as displayed. What the
tag says and the figure does not (period, scale) is recorded as an assumption,
as principle III requires. The metric gets an assumption only when the label
of the row does not name it, judged by the short keyword list below, which is
independent of the gate's own term lists.

No assumption is added for the sign: a negative figure must be recognizable
from how the filing displays it.

Usage: python tools/claims_from_facts.py
Writes tests/fixtures/gate/from_facts.json. Deterministic.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from axiomate.documents.segment import segment  # noqa: E402
from axiomate.evaluate.tagged import locate  # noqa: E402

DOCS = ROOT / "tests" / "fixtures" / "documents"
FACTS = ROOT / "tests" / "fixtures" / "facts"
OUT = ROOT / "tests" / "fixtures" / "gate" / "from_facts.json"

KEYWORDS = {
    "revenue": ("revenue", "sales"),
    "net_income": ("net income", "net loss", "net earnings", "net (loss)"),
    "earnings_per_share": ("per share",),
    "operating_cash_flow": ("operating activities",),
}

def fiscal_label(start: date, end: date, year_end: str) -> tuple[int, str] | None:
    """Fiscal year and period of [start, end] for a fiscal year ending on MMDD `year_end`."""
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    end_month = int(year_end[:2])
    fiscal_year = end.year if end.month <= end_month else end.year + 1
    months_into_year = (end.month - end_month - 1) % 12 + 1
    if months == 12 and months_into_year == 12:
        return fiscal_year, "FY"
    if months == months_into_year and months in (3, 6, 9):
        return fiscal_year, {3: "Q1", 6: "H1", 9: "9M"}[months]
    if months == 3 and months_into_year in (6, 9, 12):
        return fiscal_year, f"Q{months_into_year // 3}"
    return None


def main() -> int:
    manifest = {e["file"]: e for e in json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))}
    claims = []
    skipped = []
    for facts_path in sorted(FACTS.glob("*.json")):
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        entry = manifest[facts["document"]]
        html = (DOCS / entry["file"]).read_text(encoding="utf-8")
        text, spans = locate(html, [f["id"] for f in facts["facts"]])
        segments = segment(text, "html")
        filed = entry["filed_on"]
        for number, fact in enumerate(facts["facts"]):
            name = f"{facts_path.stem}__{number:03d}_{fact['metric']}"
            start, end = spans.get(fact["id"], (None, None))
            if start is None or start == end:
                skipped.append({"name": name, "reason": "not in the visible text"})
                continue
            holder = next((i for i, s in enumerate(segments) if s.start <= start and end <= s.end), None)
            label = fiscal_label(date.fromisoformat(fact["period_start"]), date.fromisoformat(fact["period_end"]), entry["fiscal_year_end"])
            if holder is None or label is None:
                skipped.append({"name": name, "reason": "no single segment" if holder is None else "period is not a fiscal period"})
                continue
            row = text[segments[holder].start:segments[holder].end]
            per_share = fact["metric"] == "earnings_per_share"
            assumptions = [{"statement": f"Period {fact['period_start']} to {fact['period_end']}, per the filing's embedded tag",
                            "field": "period_start", "origin": "context_store"}]
            if not per_share:
                assumptions.append({"statement": f"Figures are in {fact['stated_scale']}, per the filing's embedded tag",
                                    "field": "stated_scale", "origin": "context_store"})
            if not any(word in row.split("\t")[0].lower() for word in KEYWORDS[fact["metric"]]):
                assumptions.append({"statement": f"The metric is {fact['metric']}, per the filing's embedded tag",
                                    "field": "metric", "origin": "context_store"})
            claims.append({
                "name": name, "document": entry["file"], "fact_id": fact["id"], "segment_text": row,
                "claim": {
                    "company_cik": entry["cik"], "metric": fact["metric"], "value_kind": "exact",
                    "value_low": fact["value"], "value_high": fact["value"],
                    "stated_value": text[start:end].replace(",", ""), "stated_scale": fact["stated_scale"],
                    "unit": "currency_per_share" if per_share else "currency", "currency": "USD",
                    "period_kind": "duration", "fiscal_year": label[0], "fiscal_period": label[1],
                    "period_start": fact["period_start"], "period_end": fact["period_end"],
                    "basis": "reported", "nature": "actual", "comparison": "absolute",
                    "baseline_start": None, "baseline_end": None, "polarity": "affirmed",
                    "document_id": entry["sha256"], "segment_index": holder, "span_start": start, "span_end": end,
                    "quote": text[start:end], "said_on": f"{filed[:4]}-{filed[4:6]}-{filed[6:]}",
                    "flags": [], "assumptions": assumptions,
                },
            })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"claims": claims, "skipped": skipped}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(claims)} claims, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
