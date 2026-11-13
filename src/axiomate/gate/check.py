"""The validation gate: deterministic checks between a candidate claim and its quote.

Every candidate gets exactly one outcome:
- `rejected`: the text contradicts the claim. Nothing is stored.
- `flagged`: the text is silent on something the claim asserts and no
  assumption records where it came from, or the claim already carries an
  unresolved flag. The claim is stored as not formalizable.
- `passed`: neither.

Checks run in a fixed order: quote, value, sign, scale, period, metric, hedge.
The first contradiction decides a rejection. Missing evidence is collected, so
a flagged claim carries every flag that applies; `check` and `field` name the
first one.

The figure is read where it stands in its segment, so wording right next to
the quote counts (parentheses, a scale word, "approximately"). The period and
the metric must be in the quote itself (for the metric, the segment also
counts), or be backed by an assumption.

What the gate cannot do: a field backed by an assumption is not compared with
the text. The gate confirms only that the assumption is recorded.
"""
from __future__ import annotations

import re
import sqlite3
import dataclasses
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from axiomate.claims.schema import METRICS, Claim, parse_claim
from axiomate.claims.submit import _ground
from axiomate.errors import AxiomateError
from axiomate.gate.lexicon import approximation_before, hedges_in, metric_evidence
from axiomate.gate.numbers import SCALE_FACTORS, find_figures
from axiomate.gate.periods import find_periods

_PERIOD_FIELDS = ("period_kind", "fiscal_year", "fiscal_period", "period_start", "period_end")
_NEGATIVE_LABEL = re.compile(r"\bloss(?:es)?\b|\bused\s+in\b|\bdeficit\b|\bdecrease\b", re.IGNORECASE)
_EITHER_WAY_LABEL = re.compile(r"\((?:loss|losses|used\s+in|decrease|deficit)\)", re.IGNORECASE)


@dataclass(frozen=True)
class GateResult:
    outcome: str
    check: Optional[str] = None
    field: Optional[str] = None
    message: Optional[str] = None
    flags: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"outcome": self.outcome, "check": self.check, "field": self.field, "message": self.message,
                "flags": self.flags}


class _Rejection(Exception):
    def __init__(self, check: str, field_name: str, message: str) -> None:
        self.result = GateResult("rejected", check, field_name, message)


class _Findings:
    def __init__(self, claim: Claim) -> None:
        self.assumed = {a.field for a in claim.assumptions if a.field}
        self.missing: list[tuple[str, str, str, str]] = []

    def flag(self, check: str, reason: str, field_name: str, note: str) -> None:
        self.missing.append((check, reason, field_name, note))


def check(conn: sqlite3.Connection, data: Any) -> GateResult:
    """Run the gate on one submitted claim. Stores nothing.

    A malformed claim or an unknown document raises AxiomateError; a quote that
    is not at its address is an ordinary rejection by the `quote` check.
    """
    claim = parse_claim(data)
    try:
        index = _ground(conn, claim)
    except AxiomateError as error:
        if error.code == "document_not_found":
            raise
        return GateResult("rejected", "quote", error.field, error.message)
    row = conn.execute(
        "SELECT s.start, s.kind, substr(d.canonical_text, s.start + 1, s.end - s.start) AS text"
        " FROM segment s JOIN document d ON d.id = s.document_id WHERE s.document_id = ? AND s.idx = ?",
        (claim.document_id, index)).fetchone()
    return check_claim(claim, segment_text=row["text"], segment_start=row["start"], segment_kind=row["kind"])


def check_claim(claim: Claim, *, segment_text: str, segment_start: int, segment_kind: str) -> GateResult:
    """Run the checks on a schema-valid claim whose quote is known to be in its segment."""
    findings = _Findings(claim)
    try:
        figures = _value(claim, segment_text, segment_start)
        _sign(claim, figures, segment_text, segment_kind, findings)
        _scale(claim, figures, segment_kind, findings)
        _period(claim, findings)
        _metric(claim, segment_text, findings)
        _hedge(claim, figures, segment_text, findings)
    except _Rejection as rejection:
        return rejection.result
    flags = [{"reason": reason, "field": name, "resolved": False, "note": note} for _, reason, name, note in findings.missing]
    if findings.missing:
        first = findings.missing[0]
        return GateResult("flagged", first[0], first[2], first[3], flags)
    if any(not flag.resolved for flag in claim.flags):
        return GateResult("flagged", None, None, "the claim carries an unresolved flag", [])
    return GateResult("passed")


def _value(claim: Claim, segment_text: str, segment_start: int) -> list:
    """The figures in the quote that equal the stated value; reject if there is none."""
    if claim.stated_value is None:
        return []
    low, high = claim.span_start - segment_start, claim.span_end - segment_start
    stated = Decimal(claim.stated_value)
    figures = [f for f in find_figures(segment_text) if low <= f.start and f.end <= high and f.value == stated]
    if not figures:
        raise _Rejection("value", "stated_value", f"the quote does not contain the figure {claim.stated_value}")
    if claim.value_kind != "range" and claim.value_low is not None and claim.stated_scale is not None:
        expected = stated * SCALE_FACTORS[claim.stated_scale]
        if abs(Decimal(claim.value_low)) != expected:
            raise _Rejection("value", "value_low", f"{claim.stated_value} in {claim.stated_scale} is not {claim.value_low}")
    return figures


def _sign(claim: Claim, figures: list, segment_text: str, segment_kind: str, findings: _Findings) -> None:
    if not figures or claim.value_low is None:
        return
    written_negative = any(f.negative for f in figures)
    claimed_negative = Decimal(claim.value_low) < 0
    if written_negative and not claimed_negative:
        raise _Rejection("sign", "value_low", "the figure is written as negative but the claim's value is not")
    if claimed_negative and not written_negative:
        label = segment_text.split("\t")[0] if segment_kind == "table_row" else ""
        label_says_negative = bool(_NEGATIVE_LABEL.search(_EITHER_WAY_LABEL.sub("", label)))
        if not label_says_negative and not findings.assumed & {"value_low", "value_high"}:
            findings.flag("sign", "missing_background", "value_low", "nothing in the text shows that the figure is negative")


def _scale(claim: Claim, figures: list, segment_kind: str, findings: _Findings) -> None:
    if not figures or claim.stated_scale is None:
        return
    words = {f.scale for f in figures if f.scale}
    if words:
        if claim.stated_scale not in words:
            raise _Rejection("scale", "stated_scale", f"the text says {', '.join(sorted(words))}, the claim says {claim.stated_scale}")
        return
    if "stated_scale" in findings.assumed:
        return
    self_evident = claim.stated_scale == "units" and (
        segment_kind != "table_row" or claim.unit in ("currency_per_share", "percent"))
    if not self_evident:
        findings.flag("scale", "missing_background", "stated_scale", "the scale is not in the text and no assumption records it")


def _period(claim: Claim, findings: _Findings) -> None:
    if claim.period_end is None and claim.fiscal_period is None:
        return
    stated = find_periods(claim.quote)
    if not stated:
        if not findings.assumed & set(_PERIOD_FIELDS):
            findings.flag("period", "underspecified_time", "period_start", "the period is not in the quote and no assumption records it")
        return
    for period in stated:
        if period.end is not None:
            if (period.start, period.end) == (claim.period_start, claim.period_end):
                return
        elif (period.fiscal_year, period.fiscal_period) == (claim.fiscal_year, claim.fiscal_period):
            return
    raise _Rejection("period", "period_end", "the quote states a different period from the claim's")


def _metric(claim: Claim, segment_text: str, findings: _Findings) -> None:
    if claim.metric is None:
        return
    evidence = {metric_evidence(claim.quote, claim.metric), metric_evidence(segment_text, claim.metric)}
    if "term" in evidence:
        return
    if "component" in evidence:
        findings.flag("metric", "unmapped_metric", "metric", "the text names a component of the metric, not the metric")
        return
    if "metric" in findings.assumed:
        return
    others = [m for m in METRICS if m != claim.metric and metric_evidence(segment_text, m) == "term"]
    if others:
        raise _Rejection("metric", "metric", f"the text names {', '.join(others)}, not {claim.metric}")
    findings.flag("metric", "unmapped_metric", "metric", "the metric is not named in the text and no assumption records it")


def _hedge(claim: Claim, figures: list, segment_text: str, findings: _Findings) -> None:
    if figures and claim.value_kind == "exact" and any(approximation_before(segment_text, f.start) for f in figures):
        findings.flag("hedge", "hedged_or_conditional", "value_kind", "the text gives the figure as approximate")
    kinds = hedges_in(claim.quote)
    reasons = {flag.reason for flag in claim.flags}
    if "forward" in kinds and claim.nature == "actual":
        findings.flag("hedge", "hedged_or_conditional", "nature", "the quote is forward-looking but the claim is stated as an actual result")
    if "conditional" in kinds and "hedged_or_conditional" not in reasons:
        findings.flag("hedge", "hedged_or_conditional", "polarity", "the quote is conditional")
    if "reported" in kinds and "reported_speech" not in reasons:
        findings.flag("hedge", "reported_speech", "polarity", "the quote reports what others say")
