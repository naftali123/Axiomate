"""Fixed word lists: terms for each metric, and hedging words.

`metric_evidence` says whether a text names a metric:
- "term": the metric itself is named ("total revenues", "net income");
- "component": only a part of it is named ("rental revenue", "Games revenues");
- None: nothing relevant.

Rules:
- Revenue: "revenue(s)" or "sales". The word before it decides: an ordinary
  word ("total", "net", "our", "the", "in", "of" ...) or nothing gives a term;
  any other word names a part. "X total revenues" with a capitalized X also
  names a part.
- Net income: "net income", "net loss", "net earnings" and variants. Wording
  that turns it into a per-share figure before any number is not net income.
- Earnings per share: "per share", "earnings per", "EPS".
- Operating cash flow: "operating activities", "cash flow(s) from operations",
  "operating cash flow".
"""
from __future__ import annotations

import re
from typing import Optional

_REVENUE = re.compile(r"\b(?:revenues?|sales)\b", re.IGNORECASE)
_PLAIN_BEFORE_REVENUE = frozenset({
    "total", "net", "consolidated", "our", "the", "in", "of", "and", "its", "their", "quarterly", "annual", "had",
    "with", "to", "for", "on", "that", "as", "while", "aggregate", "overall",
})
_NET_INCOME = re.compile(
    r"\bnet\s+(?:after[- ]tax\s+)?(?:\(loss\)\s+income|income\s+\(loss\)|income|loss|earnings)\b", re.IGNORECASE)
_PER_SHARE = re.compile(r"\bper\s+(?:common\s+|diluted\s+|basic\s+)?share\b|\bearnings\s+per\b|\bEPS\b", re.IGNORECASE)
_OPERATING_CASH = re.compile(r"\boperating\s+activities\b|\bcash\s+flows?\s+from\s+operations\b|\boperating\s+cash\s+flows?\b", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")

_APPROXIMATION = frozenset({"approximately", "about", "roughly", "nearly", "almost", "around", "approx", "approx.", "~"})
_FORWARD = re.compile(
    r"\b(?:expects?|expected|anticipates?|anticipated|guidance|forecasts?|forecasted|outlook|projects|projected|"
    r"targets?|will)\b", re.IGNORECASE)
_CONDITIONAL = re.compile(r"\b(?:may|might|could|if|unless|should)\b|\b[Ss]ubject\s+to\b")
_REPORTED = re.compile(r"\baccording\s+to\b|\breportedly\b|\banalysts?\b", re.IGNORECASE)


def _revenue_evidence(text: str) -> Optional[str]:
    best = None
    for match in _REVENUE.finditer(text):
        words = _WORD.findall(text[:match.start()].split("\t")[-1])
        before = words[-1] if words else ""
        if before.lower() == "total" and len(words) > 1 and words[-2][0].isupper() and words[-2].lower() not in _PLAIN_BEFORE_REVENUE:
            best = best or "component"
        elif before == "" or before.lower() in _PLAIN_BEFORE_REVENUE:
            return "term"
        else:
            best = best or "component"
    return best


def _net_income_evidence(text: str) -> Optional[str]:
    for match in _NET_INCOME.finditer(text):
        rest = text[match.end():]
        until_number = re.split(r"\d", rest, maxsplit=1)[0]
        if not _PER_SHARE.search(until_number):
            return "term"
    return None


def metric_evidence(text: str, metric: str) -> Optional[str]:
    """Whether `text` names `metric`: "term", "component" or None."""
    text = " ".join(text.replace("\t", " \t ").split(" "))
    if metric == "revenue":
        return _revenue_evidence(text)
    if metric == "net_income":
        return _net_income_evidence(text)
    if metric == "earnings_per_share":
        return "term" if _PER_SHARE.search(text) else None
    if metric == "operating_cash_flow":
        return "term" if _OPERATING_CASH.search(text) else None
    raise ValueError(f"unknown metric: {metric}")


def approximation_before(text: str, position: int) -> bool:
    """Whether an approximation word stands directly before the figure at `position`."""
    words = text[:position].replace("$", " ").replace("(", " ").split()
    return bool(words) and words[-1].lower() in _APPROXIMATION


def hedges_in(text: str) -> set[str]:
    """Kinds of hedging wording in `text`: "forward", "conditional", "reported"."""
    kinds = set()
    if _FORWARD.search(text):
        kinds.add("forward")
    if _CONDITIONAL.search(text):
        kinds.add("conditional")
    if _REPORTED.search(text):
        kinds.add("reported")
    return kinds
