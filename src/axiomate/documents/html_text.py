"""Canonical text of a document: the text that every offset refers to.

Plain text is normalized only as far as needed to make offsets stable. HTML is
reduced to its visible text by the fixed rules below. Any change that alters
the output for an existing document must raise EXTRACTOR_VERSION.

HTML rules:
1. Content of `head`, `script`, `style`, `title`, `ix:header` and of any element
   styled `display:none` is left out.
2. Every other tag is dropped and its text kept, so a figure wrapped in an
   embedded structured-data tag stays in place.
3. A block element ends the current line. Each table row is one line; its
   non-empty cells are joined by a tab. A row that is only a list marker
   (a bullet, `(1)`, `a.`) and one cell of text is a list item laid out as a
   table: its two cells are joined by a space, so it reads as ordinary text.
4. Inside a line, every run of whitespace (including non-breaking spaces)
   becomes one space, and leading and trailing whitespace is removed.
5. Empty lines are dropped. Lines are joined by a line feed.
6. Text is put in Unicode composed form (NFC).
"""
from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

EXTRACTOR_VERSION = "1"

_SKIPPED = frozenset({"head", "script", "style", "title", "ix:header"})
_VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
_BLOCK = frozenset({
    "address", "article", "aside", "blockquote", "body", "br", "caption", "center", "dd", "div", "dl", "dt",
    "fieldset", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "html", "li",
    "main", "nav", "ol", "p", "pre", "section", "table", "tbody", "tfoot", "thead", "ul",
})
_CELL = frozenset({"td", "th"})
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")
_LIST_MARKER = re.compile(r"[•·●○▪■◦*\-–—]|\(\w{1,4}\)|\w{1,3}[.)]")


def canonical_from_text(text: str) -> str:
    """Canonical form of a plain-text document: NFC, line feeds only."""
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def canonical_from_html(html: str) -> str:
    """Canonical form of an HTML document: its visible text, by the rules above."""
    parser = _VisibleText()
    parser.feed(html)
    parser.close()
    return parser.result()


def _tidy(parts: list[str]) -> str:
    return unicodedata.normalize("NFC", _WHITESPACE.sub(" ", "".join(parts)).strip())


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._lines: list[str] = []
        self._buffer: list[str] = []      # text of the current block or cell
        self._cells: list[str] | None = None  # cells of the current table row
        self._skip_depth = 0

    def result(self) -> str:
        self._end_line()
        return "\n".join(self._lines)

    # -- structure ---------------------------------------------------------
    def _end_cell(self) -> None:
        text = _tidy(self._buffer)
        self._buffer = []
        if text and self._cells is not None:
            self._cells.append(text)

    def _end_line(self) -> None:
        if self._cells is not None:
            self._end_cell()
            if self._cells:
                is_list_item = len(self._cells) == 2 and _LIST_MARKER.fullmatch(self._cells[0])
                self._lines.append((" " if is_list_item else "\t").join(self._cells))
            self._cells = None
            return
        text = _tidy(self._buffer)
        self._buffer = []
        if text:
            self._lines.append(text)

    def _boundary(self, tag: str, opening: bool) -> None:
        if tag == "tr":
            self._end_line()
            if opening:
                self._cells = []
        elif self._cells is not None:
            if tag in _CELL:
                self._end_cell()
            elif tag in _BLOCK:
                self._buffer.append(" ")
        elif tag in _BLOCK or tag in _CELL:
            self._end_line()

    # -- parser events -----------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_depth:
            if tag not in _VOID:
                self._skip_depth += 1
            return
        style = next((value for name, value in attrs if name == "style" and value), "")
        if tag in _SKIPPED or _HIDDEN_STYLE.search(style):
            if tag not in _VOID:
                self._skip_depth = 1
            return
        self._boundary(tag, opening=True)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self._skip_depth:
            self._boundary(tag, opening=True)
            if tag == "tr":
                self._end_line()

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag not in _VOID:
                self._skip_depth -= 1
            return
        self._boundary(tag, opening=False)

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._buffer.append(data)
