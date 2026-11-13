"""Read the structured figures embedded in HTML filings (inline XBRL).

For each HTML filing in tests/fixtures/documents it writes
tests/fixtures/facts/<name>.json with every tagged figure for the four
first-version metrics that belongs to the company as a whole (no segment or
other dimension). Standard library only; the output is deterministic.

Usage: python tools/read_embedded_figures.py
"""
from __future__ import annotations

import html
import json
import sys
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "tests" / "fixtures" / "documents"
FACTS = ROOT / "tests" / "fixtures" / "facts"

METRICS = {
    "us-gaap:Revenues": "revenue",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "us-gaap:NetIncomeLoss": "net_income",
    "us-gaap:EarningsPerShareDiluted": "earnings_per_share",
    "us-gaap:NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
}
SCALES = {0: "units", 3: "thousands", 6: "millions", 9: "billions"}

CONTEXT = re.compile(r"<xbrli:context\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</xbrli:context>", re.S)
FACT = re.compile(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", re.S)
ATTR = re.compile(r"([\w:-]+)=\"([^\"]*)\"")
TAG = re.compile(r"<[^>]+>")


def contexts(source: str) -> dict[str, dict]:
    found = {}
    for context_id, body in CONTEXT.findall(source):
        if "<xbrli:segment" in body or "<xbrli:scenario" in body:
            continue
        instant = re.search(r"<xbrli:instant>([^<]+)<", body)
        start = re.search(r"<xbrli:startDate>([^<]+)<", body)
        end = re.search(r"<xbrli:endDate>([^<]+)<", body)
        if instant:
            found[context_id] = {"period_kind": "instant", "period_start": instant.group(1).strip(),
                                 "period_end": instant.group(1).strip()}
        elif start and end:
            found[context_id] = {"period_kind": "duration", "period_start": start.group(1).strip(),
                                 "period_end": end.group(1).strip()}
    return found


def parse_number(shown: str, number_format: str) -> Decimal | None:
    text = shown.strip()
    if "zerodash" in number_format or "fixed-zero" in number_format:
        return Decimal(0)
    text = text.replace("(", "").replace(")", "").replace("$", "").replace(" ", "").strip()
    if "comma-decimal" in number_format or "numcommadecimal" in number_format:
        text = text.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        text = text.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return Decimal(text)


def figures(source: str) -> tuple[list[dict], list[dict]]:
    periods = contexts(source)
    facts, skipped = [], []
    for raw_attrs, inner in FACT.findall(source):
        attrs = dict(ATTR.findall(raw_attrs))
        metric = METRICS.get(attrs.get("name", ""))
        if metric is None:
            continue
        period = periods.get(attrs.get("contextRef", ""))
        if period is None:
            continue  # a segment or other breakdown, not the company total
        shown = html.unescape(TAG.sub("", inner)).strip()
        number = parse_number(shown, attrs.get("format", ""))
        if number is None:
            skipped.append({"id": attrs.get("id"), "shown": shown})
            continue
        scale = int(attrs.get("scale", "0") or 0)
        value = number * (Decimal(10) ** scale)
        if attrs.get("sign") == "-":
            value = -value
        facts.append(
            {
                "id": attrs.get("id"),
                "metric": metric,
                "tag": attrs["name"],
                "shown": shown,
                "stated_scale": SCALES.get(scale, f"10^{scale}"),
                "value": format(value.normalize(), "f"),
                "unit": attrs.get("unitRef"),
                **period,
            }
        )
    facts.sort(key=lambda f: (f["metric"], f["period_end"], f["period_start"], f["id"] or ""))
    return facts, skipped


def main() -> int:
    """With two arguments, read filings from the first directory and write facts to the second."""
    docs, facts_dir = (ROOT / sys.argv[1], ROOT / sys.argv[2]) if len(sys.argv) == 3 else (DOCS, FACTS)
    facts_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(docs.glob("*.html")):
        facts, skipped = figures(path.read_text(encoding="utf-8"))
        out = {"document": path.name, "facts": facts, "skipped": skipped}
        (facts_dir / f"{path.stem}.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        counts = {}
        for fact in facts:
            counts[fact["metric"]] = counts.get(fact["metric"], 0) + 1
        print(path.name, counts, "skipped", len(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
