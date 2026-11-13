"""Compare stored claims with the figures a filing tags itself.

The tags are the company's own machine-readable statement of what each figure
is: metric, value and period. They are independent of everything this project
wrote, so agreement with them needs no person to confirm it.

Definitions (spec 002, Verification):

- A claim *cites* a tagged figure when its quoted span contains the figure as
  displayed. When a span contains several tagged figures, the claim cites the
  one whose displayed digits equal the claim's stated value, or the first one
  when none does.
- A citing claim *agrees* when it states a level (not a change), its metric,
  its normalized value and its period equal the tag's.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from axiomate.documents.html_text import canonical_from_html
from axiomate.errors import AxiomateError

_OPEN, _CLOSE = "", ""
_FIRST = 0xE100


def locate(html: str, fact_ids: list[str]) -> tuple[str, dict[str, tuple[int, int]]]:
    """Canonical text and, for each tagged figure, its offsets in that text.

    Each tag's content is wrapped in private-use marker characters before the
    text is extracted; the markers are then removed and their positions kept.
    The result is checked to equal the text extracted without markers.
    """
    marked = html
    for number, fact_id in enumerate(fact_ids):
        pattern = re.compile(
            r"(<ix:nonFraction\b[^>]*\bid=[\"']" + re.escape(fact_id) + r"[\"'][^>]*>)(.*?)(</ix:nonFraction>)", re.DOTALL)
        marked, count = pattern.subn(
            lambda m: f"{m.group(1)}{_OPEN}{chr(_FIRST + number)}{m.group(2)}{_CLOSE}{m.group(3)}", marked, count=1)
        if count != 1:
            raise AxiomateError("tag_not_found", f"tag {fact_id} is not in the filing exactly once", "facts")
    text = canonical_from_html(marked)
    spans: dict[str, tuple[int, int]] = {}
    plain: list[str] = []
    position = 0
    open_at: dict[int, int] = {}
    stack: list[int] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == _OPEN:
            number = ord(text[index + 1]) - _FIRST
            open_at[number] = position
            stack.append(number)
            index += 2
        elif char == _CLOSE:
            number = stack.pop()
            spans[fact_ids[number]] = (open_at[number], position)
            index += 1
        else:
            plain.append(char)
            position += 1
            index += 1
    result = "".join(plain)
    if result != canonical_from_html(html):
        raise AxiomateError("tag_marking_failed", "marking the figures changed the extracted text", "facts")
    return result, spans


def _digits(text: Optional[str]) -> str:
    return re.sub(r"[^0-9.]", "", text or "")


def _same_number(a: Optional[str], b: Optional[str]) -> bool:
    try:
        return a is not None and b is not None and Decimal(a) == Decimal(b)
    except InvalidOperation:
        return False


def differences(claim: dict[str, Any], fact: dict[str, Any]) -> list[str]:
    """The fields in which a claim disagrees with the tag it cites; empty when it agrees."""
    wrong = []
    if claim["metric"] != fact["metric"]:
        wrong.append("metric")
    if claim["comparison"] != "absolute":
        wrong.append("comparison")
    if not (_same_number(claim["value_low"], fact["value"]) and _same_number(claim["value_high"], fact["value"])):
        wrong.append("value")
    start_differs = fact["period_kind"] == "duration" and claim["period_start"] != fact["period_start"]
    if claim["period_kind"] != fact["period_kind"] or start_differs or claim["period_end"] != fact["period_end"]:
        wrong.append("period")
    return wrong


def judge(claims: list[dict[str, Any]], facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare passed claims with tagged figures of one document.

    Each fact carries `start` and `end`, its offsets in the canonical text, or
    None for both when it is not in the visible text. Returns the counts and
    the lists behind them.
    """
    visible = sorted((f for f in facts if f.get("start") is not None and f["start"] < f["end"]), key=lambda f: f["start"])
    citing = []
    covered: set[str] = set()
    disagreements = []
    for claim in claims:
        inside = [f for f in visible if claim["span_start"] <= f["start"] and f["end"] <= claim["span_end"]]
        if not inside:
            continue
        stated = _digits(claim["stated_value"])
        fact = next((f for f in inside if _digits(f["shown"]) == stated), inside[0])
        wrong = differences(claim, fact)
        citing.append(claim["id"])
        if wrong:
            disagreements.append({
                "claim_id": claim["id"], "quote": claim["quote"], "tag_id": fact["id"], "fields": wrong,
                "claim": {k: claim[k] for k in ("metric", "comparison", "value_low", "value_high", "period_kind", "period_start", "period_end")},
                "tag": {k: fact[k] for k in ("metric", "value", "period_kind", "period_start", "period_end")}})
        else:
            covered.add(fact["id"])
    return {
        "tagged_figures": len(visible), "tagged_not_visible": len(facts) - len(visible),
        "citing": len(citing), "agreeing": len(citing) - len(disagreements), "covered": len(covered),
        "uncited_tags": [f["id"] for f in visible if f["id"] not in covered], "disagreements": disagreements,
    }
