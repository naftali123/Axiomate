"""Text normalization and visible-text extraction (task T012)."""
import hashlib
import json
from pathlib import Path

import pytest

from axiomate.documents.html_text import canonical_from_html, canonical_from_text
from axiomate.documents.segment import segment

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
DOCS = FIXTURES / "documents"
GOLDEN = FIXTURES / "golden"
HTML_FILINGS = sorted(p.name for p in DOCS.glob("*.html"))
TEXT_FILINGS = sorted(p.name for p in DOCS.glob("*.txt"))


def canonical(name: str) -> str:
    data = (DOCS / name).read_bytes().decode("utf-8")
    return canonical_from_html(data) if name.endswith(".html") else canonical_from_text(data)


def test_plain_text_gets_unix_line_endings_and_composed_characters():
    assert canonical_from_text("a\r\nb\rc\n") == "a\nb\nc\n"
    assert canonical_from_text("Café") == "Café"


def test_plain_text_is_otherwise_untouched():
    text = "  Net Income      $5,520\n\n\tindented\n"
    assert canonical_from_text(text) == text


def test_small_html_document_matches_its_golden_text():
    html = (GOLDEN / "sample.html").read_text(encoding="utf-8")
    assert canonical_from_html(html) == (GOLDEN / "sample.txt").read_text(encoding="utf-8")


def test_hidden_content_is_left_out():
    text = canonical_from_html((GOLDEN / "sample.html").read_text(encoding="utf-8"))
    for hidden in ("Hidden title", "color: red", "Hidden Co", "var hidden", "not shown"):
        assert hidden not in text


def test_extraction_is_repeatable():
    html = (DOCS / HTML_FILINGS[0]).read_text(encoding="utf-8")
    assert canonical_from_html(html) == canonical_from_html(html)


@pytest.mark.parametrize("name", HTML_FILINGS)
def test_html_text_has_no_markup_left_and_tidy_whitespace(name):
    text = canonical(name)
    assert " " not in text and "  " not in text and "\r" not in text
    assert "<ix:" not in text and "</div>" not in text and "display:none" not in text
    assert all(line == line.strip() and line for line in text.split("\n"))


@pytest.mark.parametrize("name", HTML_FILINGS)
def test_every_embedded_figure_is_in_the_stored_text_inside_one_segment(name):
    """Verification threshold: 100% of tagged figures for the four metrics."""
    text = canonical(name)
    pieces = [text[s.start:s.end] for s in segment(text, "html")]
    facts = json.loads((FIXTURES / "facts" / (Path(name).stem + ".json")).read_text())["facts"]
    assert facts
    missing = [f["id"] for f in facts if not any(f["shown"] in piece for piece in pieces)]
    assert missing == []


@pytest.mark.parametrize("name", HTML_FILINGS + TEXT_FILINGS)
def test_stored_text_of_real_filings_matches_recorded_hash(name):
    """Pins the extraction rules: a change in output must be a deliberate version bump."""
    recorded = json.loads((GOLDEN / "canonical_hashes.json").read_text())
    assert hashlib.sha256(canonical(name).encode("utf-8")).hexdigest() == recorded[name]


@pytest.mark.parametrize("marker", ["•", "(1)", "a.", "2)", "–"])
def test_list_item_laid_out_as_a_table_row_reads_as_ordinary_text(marker):
    html = f"<table><tr><td>{marker}</td><td> </td><td><div>Revenue rose. Costs fell.</div></td></tr></table>"
    assert canonical_from_html(html) == f"{marker} Revenue rose. Costs fell."


def test_two_cell_table_row_of_values_stays_a_row():
    assert canonical_from_html("<table><tr><td>2021</td><td>189,346</td></tr></table>") == "2021\t189,346"
