"""Generate the gate's test cases: probes and corrupted claims.

Probes are mechanical claims on spans of the form "approximately $X million"
found in the development filings, in sentences that name none of the four
metrics. Their metric and period are placeholders backed by assumptions; they exist to test how the gate reads hedged, scaled
figures in running prose, and are not counted as correct claims.

Each corrupted claim names its base claim, the kind of corruption, the
operations to apply, and the check that must catch it. Kinds:

  digit       stated and normalized value changed together; the quote is not
  scale       scale changed, normalized value recomputed; the quote names the scale
  sign        sign of the normalized value flipped
  period      period moved by a year; the quote states the period
  metric      metric replaced; the row label names the original one
  hedge       "approximate" replaced by "exact"; the quote says "approximately"
  assumption  the assumption behind the scale or the period removed

The expected results are fixed here by construction, not by running the gate.
Deterministic: the same inputs always give the same files.

Usage: python tools/claims_from_facts.py && python tools/corrupt_for_gate.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from axiomate.documents.html_text import canonical_from_html  # noqa: E402
from axiomate.documents.segment import segment  # noqa: E402
from claims_from_facts import KEYWORDS, fiscal_label  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
DOCS = FIXTURES / "documents"
GATE = FIXTURES / "gate"
PER_KIND = 12
FACTOR = {"units": Decimal(1), "thousands": Decimal(1000), "millions": Decimal(10) ** 6, "billions": Decimal(10) ** 9}
PROBE = re.compile(r"approximately \$(\d+(?:\.\d+)?) (million|thousand|billion)\b")
NEGATIVE_NEAR = re.compile(r"decreas|declin|loss|lower|reduc|fell|drop|\($", re.IGNORECASE)
PERIOD_IN_QUOTE = re.compile(r"months\s+ended|quarter\s+of|months\s+of\s+\d{4}|\d{4}'s\s+\w+\s+quarter", re.IGNORECASE)


def plain(number: Decimal) -> str:
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def set_(field, value):
    return {"op": "set", "field": field, "value": value}


def shift_year(day: str, by: int) -> str:
    year, rest = int(day[:4]) + by, day[4:]
    return f"{year}{'-02-28' if rest == '-02-29' else rest}"


def build_probes() -> list[dict]:
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    probes = []
    for entry in manifest:
        if entry["format"] != "html":
            continue
        text = canonical_from_html((DOCS / entry["file"]).read_text(encoding="utf-8"))
        end = date(int(entry["period_end"][:4]), int(entry["period_end"][4:6]), int(entry["period_end"][6:]))
        start = date(end.year if end.month > 2 else end.year - 1, (end.month - 3) % 12 + 1, 1)
        label = fiscal_label(start, end, entry["fiscal_year_end"])
        filed = entry["filed_on"]
        taken = 0
        for index, part in enumerate(segment(text, "html")):
            if part.kind != "sentence" or taken >= 4:
                continue
            body = text[part.start:part.end]
            match = PROBE.search(body)
            if not match or NEGATIVE_NEAR.search(body[max(0, match.start() - 30):match.start()]):
                continue
            if any(word in body.lower() for words in KEYWORDS.values() for word in words):
                continue  # the placeholder metric must not collide with a metric the sentence names
            taken += 1
            scale = match.group(2) + "s"
            value = plain(Decimal(match.group(1)) * FACTOR[scale])
            probes.append({
                "name": f"probe__{Path(entry['file']).stem}__{index}",
                "claim": {
                    "company_cik": entry["cik"], "metric": "revenue", "value_kind": "approximate",
                    "value_low": value, "value_high": value, "stated_value": match.group(1), "stated_scale": scale,
                    "unit": "currency", "currency": "USD", "period_kind": "duration",
                    "fiscal_year": label[0], "fiscal_period": label[1],
                    "period_start": start.isoformat(), "period_end": end.isoformat(),
                    "basis": "reported", "nature": "actual", "comparison": "absolute",
                    "baseline_start": None, "baseline_end": None, "polarity": "affirmed",
                    "document_id": entry["sha256"], "segment_index": index,
                    "span_start": part.start + match.start(), "span_end": part.start + match.end(),
                    "quote": match.group(0), "said_on": f"{filed[:4]}-{filed[4:6]}-{filed[6:]}",
                    "flags": [],
                    "assumptions": [
                        {"statement": "Probe: the metric is a placeholder", "field": "metric", "origin": "human"},
                        {"statement": "Probe: the period is a placeholder", "field": "period_start", "origin": "human"},
                    ],
                },
            })
    return probes


def main() -> int:
    facts = json.loads((GATE / "from_facts.json").read_text(encoding="utf-8"))["claims"]
    hand = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FIXTURES / "claims" / "good").glob("*.json"))]
    probes = build_probes()
    (GATE / "probes.json").write_text(json.dumps(probes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cases: list[dict] = []

    def add(kind, base_set, base, check, outcome, operations):
        cases.append({"name": f"{kind}__{base}__{sum(c['kind'] == kind for c in cases):02d}", "kind": kind,
                      "base_set": base_set, "base": base, "expected_check": check, "expected_outcome": outcome,
                      "operations": operations})

    def count(kind):
        return sum(c["kind"] == kind for c in cases)

    # digit: every fourth facts claim, so that all filings and metrics appear
    for item in facts[::4]:
        claim = item["claim"]
        if count("digit") >= PER_KIND:
            break
        stated = claim["stated_value"]
        changed = str(int(stated[0]) % 9 + 1) + stated[1:]
        sign = -1 if claim["value_low"].startswith("-") else 1
        value = plain(sign * Decimal(changed) * FACTOR[claim["stated_scale"]])
        add("digit", "facts", item["name"], "value", "rejected",
            [set_("stated_value", changed), set_("value_low", value), set_("value_high", value)])

    # scale: prose claims whose quote names the scale
    scaled = [("hand", h["name"], h["claim"], h["quote"]) for h in hand] + [("probe", p["name"], p["claim"], p["claim"]["quote"]) for p in probes]
    for base_set, name, claim, quote in scaled:
        if count("scale") >= PER_KIND or claim["stated_scale"] != "millions" or "million" not in quote:
            continue
        sign = -1 if claim["value_low"].startswith("-") else 1
        value = plain(sign * Decimal(claim["stated_value"]) * FACTOR["thousands"])
        add("scale", base_set, name, "scale", "rejected",
            [set_("stated_scale", "thousands"), set_("value_low", value), set_("value_high", value)])

    # sign: half from negative figures, half from positive ones
    negatives = [f for f in facts if f["claim"]["value_low"].startswith("-")][::3][: PER_KIND // 2]
    positives = [f for f in facts if not f["claim"]["value_low"].startswith("-")][::5][: PER_KIND // 2]
    for item in negatives + positives:
        low = item["claim"]["value_low"]
        flipped = low[1:] if low.startswith("-") else "-" + low
        add("sign", "facts", item["name"], "sign", "rejected" if low.startswith("-") else None,
            [set_("value_low", flipped), set_("value_high", flipped)])

    # period: hand claims whose quote states the period, moved one year back and one year forward
    for by in (-1, 1):
        for item in hand:
            claim = item["claim"]
            if count("period") >= PER_KIND or item["expected_status"] == "not-formalizable" or not PERIOD_IN_QUOTE.search(item["quote"]):
                continue
            add("period", "hand", item["name"], "period", "rejected", [
                set_("period_start", shift_year(claim["period_start"], by)), set_("period_end", shift_year(claim["period_end"], by)),
                set_("fiscal_year", claim["fiscal_year"] + by)])

    # metric: rows whose label names the metric, relabelled as a metric the row does not mention
    for item in facts[::3]:
        claim = item["claim"]
        if count("metric") >= PER_KIND or any(a["field"] == "metric" for a in claim["assumptions"]):
            continue
        row = item["segment_text"].lower()
        target = next((m for m in ("revenue", "net_income", "operating_cash_flow")
                       if m != claim["metric"] and not any(word in row for word in KEYWORDS[m])), None)
        if target and claim["metric"] != "earnings_per_share":
            add("metric", "facts", item["name"], "metric", None, [set_("metric", target)])

    # hedge: probes say "approximately"
    for probe in probes[:PER_KIND]:
        add("hedge", "probe", probe["name"], "hedge", "flagged", [set_("value_kind", "exact")])

    # assumption: remove what backs the scale or the period
    backed = [f for f in facts if any(a["field"] == "stated_scale" for a in f["claim"]["assumptions"])][::6]
    for number, item in enumerate(backed[:PER_KIND]):
        field, check = (("stated_scale", "scale"), ("period_start", "period"))[number % 2]
        add("assumption", "facts", item["name"], check, "flagged", [{"op": "remove_assumption", "field": field}])

    (GATE / "corrupted.json").write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kinds = sorted({c["kind"] for c in cases})
    print(len(probes), "probes;", ", ".join(f"{k} {count(k)}" for k in kinds))
    short = [k for k in ("digit", "scale", "sign", "period", "metric", "hedge", "assumption") if count(k) < 10]
    if short:
        raise SystemExit(f"fewer than 10 cases for: {', '.join(short)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
