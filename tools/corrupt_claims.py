"""Generate malformed claims from the hand-written good claims.

Each output file names a good claim (`base`), the operations that corrupt it,
and the rejection code the claim store must answer with. Operations on the
claim itself are applied before submission; operations on the span are applied
after the test has located the quote in the stored document. The generator is
deterministic: the same good claims always give the same files.

Usage: python tools/corrupt_claims.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOOD = ROOT / "tests" / "fixtures" / "claims" / "good"
BAD = ROOT / "tests" / "fixtures" / "claims" / "bad"
PER_CODE = 5


def set_(path, value):
    return {"op": "set", "path": path, "value": value}


def delete(path):
    return {"op": "delete", "path": path}


def swap_digit(text: str) -> str | None:
    for index, char in enumerate(text):
        if char.isdigit():
            return text[:index] + str((int(char) + 1) % 10) + text[index + 1:]
    return None


def variants(code: str, good: dict, index: int):
    """Yield (suffix, field, operations) for one good claim and one rejection code."""
    claim = good["claim"]
    formal = good["expected_status"] != "not-formalizable"
    if code == "schema_invalid" and formal:
        options = [
            ("missing_period_start", "period_start", [delete("claim.period_start")]),
            ("value_not_a_number", "value_low", [set_("claim.value_low", "abc")]),
            ("bad_polarity", "polarity", [set_("claim.polarity", "maybe")]),
            ("period_reversed", "period_end", [set_("claim.period_end", "1900-01-01")]),
            ("range_reversed", "value_high", [set_("claim.value_high", "-999999999999")]),
            ("missing_currency", "currency", [set_("claim.currency", None)]),
            ("bad_scale", "stated_scale", [set_("claim.stated_scale", "dozens")]),
        ]
        yield options[index % len(options)]
    elif code == "unknown_metric" and formal:
        metrics = ["ebitda", "gross_margin", "free_cash_flow", "total_assets", "dividends"]
        yield ("metric_" + metrics[index % len(metrics)], "metric",
               [set_("claim.metric", metrics[index % len(metrics)])])
    elif code == "document_not_found":
        yield ("unknown_document", "document_id",
               [{"op": "set_document_id", "value": format(index + 1, "064x")}])
    elif code == "span_mismatch":
        altered = swap_digit(good["quote"])
        if altered is not None and index % 2 == 0:
            yield ("quote_digit_changed", "quote", [{"op": "set_quote", "value": altered}])
        else:
            yield ("span_shifted", "quote", [{"op": "shift_span", "by": 3 + index}])
    elif code == "span_outside_segment":
        yield ("span_crosses_segment", "span_end", [{"op": "extend_past_segment", "by": 5 + index}])
    elif code == "said_on_mismatch":
        year = int(claim["said_on"][:4]) + 1 + index % 3
        yield ("said_on_changed", "said_on", [set_("claim.said_on", f"{year}{claim['said_on'][4:]}")])
    elif code == "status_mismatch":
        wrong = {"formal": "formal-with-assumptions", "formal-with-assumptions": "formal",
                 "not-formalizable": "formal"}[good["expected_status"]]
        yield ("status_" + wrong.replace("-", "_"), "status", [{"op": "set_status", "value": wrong}])
    elif code == "empty_field_without_flag" and formal:
        fields = ["value_low", "metric", "period_start", "stated_value", "unit"]
        field = fields[index % len(fields)]
        yield ("empty_" + field, field, [set_("claim." + field, None)])


CODES = [
    "schema_invalid", "unknown_metric", "document_not_found", "span_mismatch",
    "span_outside_segment", "said_on_mismatch", "status_mismatch", "empty_field_without_flag",
]


def main() -> int:
    goods = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(GOOD.glob("*.json"))]
    BAD.mkdir(parents=True, exist_ok=True)
    for old in BAD.glob("*.json"):
        old.unlink()
    for code in CODES:
        made = 0
        for index, good in enumerate(goods):
            if made >= PER_CODE:
                break
            for suffix, field, operations in variants(code, good, made):
                name = f"{code}__{good['name']}__{suffix}"
                out = {"name": name, "base": good["name"], "expected_error": code,
                       "expected_field": field, "operations": operations}
                (BAD / f"{name}.json").write_text(
                    json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                made += 1
        if made < PER_CODE:
            raise SystemExit(f"only {made} corrupted claims for {code}")
        print(code, made)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
