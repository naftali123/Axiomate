"""Which segments are sent to the model, and with what context.

Selection (never looks at embedded tags):
- a sentence or heading is selected when it contains a digit and names one of
  the four metrics, or a component of one;
- a table row is selected when it contains a digit and either its own label
  names a metric, or the nearest row above it in the same table that has no
  digits (a sub-heading such as "Earnings per share:") does.

Context (sent with the segment, marked as not quotable):
- for a table row: the three segments before its table, the heading rows at
  the top of the table (up to four, ending at the first row that has a worded
  label and figures), and the sub-heading row if there is one;
- for a sentence: the nearest heading above it and the two segments before it.

A "table" is a run of consecutive table rows and digit-less lines between them.
"""
from __future__ import annotations

from dataclasses import dataclass

from axiomate.claims.schema import METRICS
from axiomate.documents.segment import Segment
from axiomate.gate.lexicon import metric_evidence

_BEFORE_TABLE = 3
_TABLE_HEAD_ROWS = 4
_SUBHEADING_REACH = 4
_HEADING_REACH = 40


@dataclass(frozen=True)
class Selection:
    index: int
    context: list[int]


def _names_metric(text: str) -> bool:
    return any(metric_evidence(text, metric) for metric in METRICS)


def _has_digit(text: str) -> bool:
    return any(char.isdigit() for char in text)


def _is_data_row(body: str) -> bool:
    """A row with a worded label followed by figures, as opposed to a heading row."""
    label, _, rest = body.partition("\t")
    return any(c.isalpha() for c in label) and _has_digit(rest)


def select(text: str, segments: list[Segment]) -> list[Selection]:
    """The segments worth reading, each with the indexes of its context segments."""
    bodies = [text[s.start:s.end] for s in segments]
    is_row = [s.kind == "table_row" for s in segments]

    def in_table(i: int) -> bool:
        """A row, or a digit-less line directly between rows (a sub-heading)."""
        if is_row[i]:
            return True
        return (not _has_digit(bodies[i]) and 0 < i < len(segments) - 1 and len(bodies[i]) < 80
                and (is_row[i - 1] or (i > 1 and is_row[i - 2])) and is_row[i + 1])

    chosen: list[Selection] = []
    for i, body in enumerate(bodies):
        if not _has_digit(body):
            continue
        if not is_row[i]:
            if _names_metric(body):
                heading = next((j for j in range(i - 1, max(-1, i - _HEADING_REACH), -1) if segments[j].kind == "heading"), None)
                context = sorted({j for j in (heading, i - 2, i - 1) if j is not None and j >= 0})
                chosen.append(Selection(i, context))
            continue
        label = body.split("\t")[0]
        subheading = next((j for j in range(i - 1, max(-1, i - 1 - _SUBHEADING_REACH), -1)
                           if in_table(j) and not _has_digit(bodies[j])), None)
        if subheading is not None and not _names_metric(bodies[subheading]):
            subheading = None
        if not (_names_metric(label) or subheading is not None):
            continue
        first = i
        while first > 0 and in_table(first - 1):
            first -= 1
        context = set(range(max(0, first - _BEFORE_TABLE), first))
        for j in range(first, min(first + _TABLE_HEAD_ROWS, i)):
            if _is_data_row(bodies[j]):
                break
            context.add(j)
        if subheading is not None:
            context.add(subheading)
        chosen.append(Selection(i, sorted(context)))
    return chosen


def request_text(text: str, segments: list[Segment], selection: Selection) -> str:
    """The exact text sent to the model for one selected segment."""
    lines = ["CONTEXT (for understanding only; never quote from it):"]
    lines += [text[segments[j].start:segments[j].end] for j in selection.context] or ["(none)"]
    kind = segments[selection.index].kind
    lines += ["", f"SEGMENT (a {kind.replace('_', ' ')}; every quote must be copied exactly from it):",
              text[segments[selection.index].start:segments[selection.index].end]]
    return "\n".join(lines)
