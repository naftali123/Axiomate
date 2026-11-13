"""Reads fiscal periods out of a quote by fixed rules.

Two kinds of phrase are read:
- a length and an end date: "three months ended March 31, 2024", "quarter
  ended June 30, 2021", "year ended December 31, 2023". These give exact start
  and end dates. "three and nine months ended ..." gives two periods.
- a label and a year: "the first nine months of 1997", "the third quarter of
  1997", "1997's third quarter", "fiscal year 2021". These give a fiscal period
  and a fiscal year but no dates.

Relative phrases ("the same period in the prior year") are deliberately not
read: what they refer to is not in the quote.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

_MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_abbr) if name})
_MONTH = "(?P<month>" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_DATE = _MONTH + r"\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})"
_COUNT = {"three": 3, "six": 6, "nine": 9, "twelve": 12, "3": 3, "6": 6, "9": 9, "12": 12}
_ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_LABEL_BY_MONTHS = {3: "Q1", 6: "H1", 9: "9M"}

_MONTHS_ENDED = re.compile(
    r"\b(?P<counts>(?:(?:three|six|nine|twelve|3|6|9|12)(?:\s*,\s*|\s+and\s+|\s+))+)months?\s+ended\s+" + _DATE,
    re.IGNORECASE)
_QUARTER_ENDED = re.compile(r"\bquarter\s+ended\s+" + _DATE, re.IGNORECASE)
_YEAR_ENDED = re.compile(r"\byear\s+ended\s+" + _DATE, re.IGNORECASE)
_FIRST_MONTHS_OF = re.compile(r"\bfirst\s+(?P<count>three|six|nine)\s+months\s+of\s+(?P<year>\d{4})\b", re.IGNORECASE)
_QUARTER_OF = re.compile(r"\b(?P<ordinal>first|second|third|fourth)\s+quarter\s+of\s+(?:fiscal\s+)?(?P<year>\d{4})\b", re.IGNORECASE)
_YEARS_QUARTER = re.compile(r"\b(?P<year>\d{4})'s\s+(?P<ordinal>first|second|third|fourth)\s+quarter\b", re.IGNORECASE)
_FISCAL_YEAR = re.compile(r"\bfiscal\s+(?:year\s+)?(?P<year>\d{4})\b", re.IGNORECASE)


@dataclass(frozen=True)
class Period:
    position: int
    start: Optional[str] = None
    end: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None


def _months_back(end: date, months: int) -> date:
    """First day of a period of `months` months that ends on `end`."""
    following = end + timedelta(days=1)
    index = following.year * 12 + following.month - 1 - months
    year, month = divmod(index, 12)
    return date(year, month + 1, min(following.day, calendar.monthrange(year, month + 1)[1]))


def _end_date(match: re.Match) -> Optional[date]:
    try:
        return date(int(match.group("year")), _MONTHS[match.group("month").lower()], int(match.group("day")))
    except ValueError:
        return None


def find_periods(text: str) -> list[Period]:
    """Every period stated in `text`, in order of appearance."""
    found: list[tuple[int, int, Period]] = []

    def dated(match: re.Match, months: int, order: int) -> None:
        end = _end_date(match)
        if end is not None:
            found.append((match.start(), order, Period(
                match.start(), start=_months_back(end, months).isoformat(), end=end.isoformat())))

    for match in _MONTHS_ENDED.finditer(text):
        for order, word in enumerate(re.findall(r"three|six|nine|twelve|12|3|6|9", match.group("counts"), re.IGNORECASE)):
            dated(match, _COUNT[word.lower()], order)
    for match in _QUARTER_ENDED.finditer(text):
        dated(match, 3, 0)
    for match in _YEAR_ENDED.finditer(text):
        dated(match, 12, 0)
    for match in _FIRST_MONTHS_OF.finditer(text):
        label = _LABEL_BY_MONTHS[_COUNT[match.group("count").lower()]]
        found.append((match.start(), 0, Period(match.start(), fiscal_year=int(match.group("year")), fiscal_period=label)))
    for pattern in (_QUARTER_OF, _YEARS_QUARTER):
        for match in pattern.finditer(text):
            label = f"Q{_ORDINAL[match.group('ordinal').lower()]}"
            found.append((match.start(), 0, Period(match.start(), fiscal_year=int(match.group("year")), fiscal_period=label)))
    for match in _FISCAL_YEAR.finditer(text):
        if not any(start <= match.start() < start + 40 and p.fiscal_period for start, _, p in found):
            found.append((match.start(), 0, Period(match.start(), fiscal_year=int(match.group("year")), fiscal_period="FY")))
    return [period for _, _, period in sorted(found, key=lambda item: (item[0], item[1]))]
