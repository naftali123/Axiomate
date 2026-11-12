"""Deterministic segmentation of canonical text into addressable pieces.

The result is a pure function of the canonical text and the document format.
Any change that alters the output for an existing document must raise
SEGMENTER_VERSION.

Blocks
- HTML text: each line is a block. A line containing a tab is a table row.
- Plain text: a blank line ends a block. A line between `<TABLE>` and
  `</TABLE>` markers is a table row on its own. So is a line that looks like
  columns: it has a gap of three or more spaces, at most four words follow
  the last gap, and either there are two or more gaps, or a digit follows
  the last gap, or at most four words precede the first gap. (A label
  followed by a gap and running text, as in `NOTE A:   The accompanying ...`,
  and a justified line of prose with one wide gap, are prose.) Other
  consecutive lines form one prose block.

Sentences (inside a prose block)
A sentence ends at `.`, `!` or `?`, plus any closing quotes or brackets, when
followed by whitespace and then a capital letter (optionally after an opening
quote or bracket). A full stop does not end a sentence after:
- a listed abbreviation (`Inc.`, `No.`, `vs.` ...);
- letters separated by full stops (`U.S.`, `e.g.`);
- a single capital letter standing alone (`John A. Smith`, `PART I.`);
- the number or letter of a numbered heading (`Item 2.`, `Note 3.`, or a
  number that opens the block).
When in doubt the rules do not split: an over-long segment still contains the
whole sentence, while a wrong split would cut one in two.

Kinds
A table row is `table_row`; so is a prose block with no letters in it (a
figure that the source wrapped onto its own line). A prose block that was not split, is at most 150
characters long and does not end in `.`, `!`, `?`, `;`, `:` or `,` is a
`heading`. Everything else is a `sentence`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SEGMENTER_VERSION = "1"

ABBREVIATIONS = frozenset({
    "inc", "corp", "co", "ltd", "llc", "plc", "bros", "no", "nos", "mr", "mrs", "ms", "dr", "messrs", "jr", "sr",
    "st", "vs", "etc", "approx", "fig", "dept", "ave", "blvd", "cf", "viz", "ca", "est", "jan", "feb", "mar", "apr",
    "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
})
_NUMBERED = frozenset({"item", "items", "note", "notes", "part", "section", "article", "exhibit", "rule", "schedule"})
_HEADING_MAX = 150

_CANDIDATE = re.compile(r"""[.!?]["'”’)\]]*(?=\s+["'“‘(\[]?[A-Z])""")
_DOTTED = re.compile(r"(?:[A-Za-z]\.)+[A-Za-z]")
_ENUMERATOR = re.compile(r"\(?(?:\d{1,2}|[A-Za-z]|[IVXivx]{1,5})\)?")
_TABLE_GAP = re.compile(r"(?<=\S) {3,}(?=\S)")
_ROW_TAIL_MAX_WORDS = 4
_TABLE_OPEN = re.compile(r"\s*<TABLE>", re.IGNORECASE)
_TABLE_CLOSE = re.compile(r"\s*</TABLE>", re.IGNORECASE)
_OPENERS = "\"'“‘(["
_CLOSERS = "\"'”’)]"


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    kind: str


def segment(text: str, fmt: str) -> list[Segment]:
    """Split canonical text into ordered, non-overlapping segments."""
    if fmt == "html":
        blocks = _html_blocks(text)
    elif fmt == "text":
        blocks = _text_blocks(text)
    else:
        raise ValueError(f"unknown format: {fmt}")
    segments: list[Segment] = []
    for start, end, is_row in blocks:
        start, end = _trim(text, start, end)
        if start >= end:
            continue
        if is_row:
            segments.append(Segment(start, end, "table_row"))
        else:
            segments.extend(_prose(text, start, end))
    return segments


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _lines(text: str):
    position = 0
    for line in text.split("\n"):
        yield position, position + len(line), line
        position += len(line) + 1


def _html_blocks(text: str):
    for start, end, line in _lines(text):
        yield start, end, "\t" in line


def _text_blocks(text: str):
    in_table = False
    prose_start = prose_end = None
    for start, end, line in _lines(text):
        opens = bool(_TABLE_OPEN.match(line))
        closes = bool(_TABLE_CLOSE.match(line))
        blank = not line.strip()
        is_row = not blank and (in_table or opens or closes or _has_columns(line.strip()))
        if (blank or is_row) and prose_start is not None:
            yield prose_start, prose_end, False
            prose_start = None
        if is_row:
            yield start, end, True
        elif not blank:
            if prose_start is None:
                prose_start = start
            prose_end = end
        if opens:
            in_table = True
        if closes:
            in_table = False
    if prose_start is not None:
        yield prose_start, prose_end, False


def _has_columns(line: str) -> bool:
    gaps = list(_TABLE_GAP.finditer(line))
    if not gaps:
        return False
    tail = line[gaps[-1].end():]
    if len(tail.split()) > _ROW_TAIL_MAX_WORDS:
        return False
    head_words = len(line[:gaps[0].start()].split())
    return len(gaps) >= 2 or any(c.isdigit() for c in tail) or head_words <= _ROW_TAIL_MAX_WORDS


def _prose(text: str, start: int, end: int) -> list[Segment]:
    block = text[start:end]
    cuts = [m.end() for m in _CANDIDATE.finditer(block) if _ends_sentence(block, m.start())]
    if not cuts and not any(c.isalpha() for c in block):
        return [Segment(start, end, "table_row")]
    if not cuts:
        last = block.rstrip(_CLOSERS)[-1:]
        kind = "heading" if len(block) <= _HEADING_MAX and last not in ".!?;:," else "sentence"
        return [Segment(start, end, kind)]
    segments = []
    position = 0
    for cut in cuts + [len(block)]:
        s, e = _trim(text, start + position, start + cut)
        if s < e:
            segments.append(Segment(s, e, "sentence"))
        position = cut
    return segments


def _ends_sentence(block: str, mark: int) -> bool:
    """Whether the punctuation mark at `mark` really ends a sentence."""
    if block[mark] != ".":
        return True
    before = block[:mark]
    words = before.split()
    if not words or before[-1].isspace():
        return True
    word = words[-1].lstrip(_OPENERS)
    if word.lower() in ABBREVIATIONS or _DOTTED.fullmatch(word):
        return False
    if len(word) == 1 and word.isupper():
        return False
    if _ENUMERATOR.fullmatch(word):
        previous = words[-2].lower().rstrip(":") if len(words) > 1 else None
        if previous is None or previous in _NUMBERED:
            return False
    return True
