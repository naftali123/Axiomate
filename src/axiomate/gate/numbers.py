"""Reads figures out of a quote by fixed rules.

A figure is a number as written (`189,346`, `1.8`, `.71`), with what the
wording around it says: a scale word after it, a percent sign, and whether it
is written as negative. Negative means one of:
- the figure is in parentheses;
- a minus sign stands directly before it;
- a decrease word governs it ("decreased by", "a decline of");
- a loss phrase governs it ("net loss of", "loss was").
A decrease word elsewhere in the sentence does not make a figure negative.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

SCALE_FACTORS = {"units": Decimal(1), "thousands": Decimal(1000), "millions": Decimal(10) ** 6, "billions": Decimal(10) ** 9}

_FIGURE = re.compile(
    r"(?<![\w.,])(?P<open>\(\s*)?(?:\$\s*)?(?P<open2>\(\s*)?"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?![\d,]*\d)"
    r"(?P<close>\s*\))?(?P<pct>\s?%)?(?:\s+(?P<scale>thousand|million|billion)s?\b)?",
    re.IGNORECASE)
_LEAD = r"(?:(?:approximately|about|roughly|nearly|almost|around)\s+|\$\s*|\(\s*)*$"
_DECREASE = re.compile(r"\b(?:decreas\w*|declin\w*|fell|dropped|reduc\w*|lower|down)\s+(?:by|of)\s+" + _LEAD, re.IGNORECASE)
_LOSS = re.compile(r"\bloss(?:es)?\s+(?:of|was|were|totaled|totaling|totalling)\s+" + _LEAD, re.IGNORECASE)
_MINUS = re.compile(r"(?:^|\s)[-−]\s*(?:\$\s*)?$")


@dataclass(frozen=True)
class Figure:
    start: int
    end: int
    text: str
    value: Decimal
    scale: Optional[str]
    percent: bool
    negative: bool


def find_figures(text: str) -> list[Figure]:
    """Every figure in `text`, in order."""
    figures = []
    for match in _FIGURE.finditer(text):
        number = match.group("num")
        in_parentheses = bool((match.group("open") or match.group("open2")) and match.group("close"))
        before = text[:match.start()]
        negative = in_parentheses or bool(_MINUS.search(before) or _DECREASE.search(before) or _LOSS.search(before))
        scale = match.group("scale")
        figures.append(Figure(
            start=match.start("num"), end=match.end("num"), text=number,
            value=Decimal(number.replace(",", "")), scale=scale.lower() + "s" if scale else None,
            percent=bool(match.group("pct")), negative=negative))
    return figures
