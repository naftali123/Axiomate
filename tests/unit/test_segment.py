"""Deterministic segmentation (task T013)."""
import re
from pathlib import Path

import pytest

from axiomate.documents.html_text import canonical_from_html, canonical_from_text
from axiomate.documents.segment import segment

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
DOCS = FIXTURES / "documents"
BOUNDARIES = FIXTURES / "boundaries"
FILINGS = sorted(p.name for p in DOCS.iterdir() if p.suffix in (".html", ".txt"))


def pieces(text: str, fmt: str = "text") -> list[str]:
    return [text[s.start:s.end] for s in segment(text, fmt)]


def kinds(text: str, fmt: str = "text") -> list[str]:
    return [s.kind for s in segment(text, fmt)]


def load(name: str) -> tuple[str, str]:
    data = (DOCS / name).read_bytes().decode("utf-8")
    if name.endswith(".html"):
        return canonical_from_html(data), "html"
    return canonical_from_text(data), "text"


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_splits_plain_sentences():
    assert pieces("Revenue rose. Costs fell. Margins improved.") == ["Revenue rose.", "Costs fell.", "Margins improved."]


@pytest.mark.parametrize("text", [
    "Everi Holdings Inc. reported revenue of $189.3 million.",
    "Sales in the U.S. market were flat against 2023.",
    "See Note No. 5 for details of the acquisition.",
    "Earnings were $1.72 per share, up from $.71 a year ago.",
    "Revenue grew 5.2% to $4.2 billion in the quarter.",
    "John A. Smith signed the report on behalf of the registrant.",
    "The bank (e.g. its trust department) earned fees of $ 608,000.",
    "W. P. Carey Inc. is the advisor to the company.",
])
def test_abbreviations_initials_and_decimals_do_not_split(text):
    assert pieces(text) == [text]


def test_splits_after_closing_quote_and_before_opening_quote():
    text = 'It is titled "Reporting on Start-up Activities." This guidance applies. "Quoted" text follows.'
    assert pieces(text) == ['It is titled "Reporting on Start-up Activities."', "This guidance applies.", '"Quoted" text follows.']


def test_splits_after_a_capital_that_is_part_of_a_hyphenated_name():
    assert pieces("We follow Regulation S-X. Accordingly, some notes are omitted.") == [
        "We follow Regulation S-X.", "Accordingly, some notes are omitted."]


def test_sentence_may_run_over_line_breaks_in_plain_text():
    text = "Net income for the first nine months of 1997 was\n$ 2,006,000 compared to\n$ 1,680,000 in 1996.  It rose again.\n"
    assert pieces(text) == [text[: text.index("  It")], "It rose again."]
    assert kinds(text) == ["sentence", "sentence"]


def test_blank_line_ends_a_segment_in_plain_text():
    text = "RESULTS OF OPERATIONS\n\nRevenue rose and\ncosts fell.\n"
    assert pieces(text) == ["RESULTS OF OPERATIONS", "Revenue rose and\ncosts fell."]
    assert kinds(text) == ["heading", "sentence"]


def test_plain_text_table_lines_are_one_row_each():
    text = "Net Income                                  $5,520\nNet Income Per Share                          $.64\n"
    assert pieces(text) == ["Net Income                                  $5,520", "Net Income Per Share                          $.64"]
    assert kinds(text) == ["table_row", "table_row"]


def test_lines_between_table_markers_are_rows():
    text = "<TABLE>\nASSETS\nLoans, Net   359,792\n</TABLE>\nLoans grew. Deposits fell.\n"
    assert kinds(text) == ["table_row", "table_row", "table_row", "table_row", "sentence", "sentence"]


def test_html_line_is_a_block_and_tab_marks_a_table_row():
    text = "Results of Operations\nRevenue was $189.3 million. Net income rose.\nRevenues\t$\t189,346"
    assert pieces(text, "html") == ["Results of Operations", "Revenue was $189.3 million.", "Net income rose.", "Revenues\t$\t189,346"]
    assert kinds(text, "html") == ["heading", "sentence", "sentence", "table_row"]


def test_same_figure_in_headline_and_table_gets_two_addresses():
    text = "Revenue was 189,346 this quarter.\nRevenues\t189,346"
    found = [s for s in segment(text, "html") if "189,346" in text[s.start:s.end]]
    assert len(found) == 2 and found[0].kind == "sentence" and found[1].kind == "table_row"


def test_empty_text_has_no_segments():
    assert segment("", "text") == [] and segment(" \n\n ", "text") == []


@pytest.mark.parametrize("name", FILINGS)
def test_segments_are_ordered_do_not_overlap_and_cover_all_text(name):
    text, fmt = load(name)
    segments = segment(text, fmt)
    assert segments
    position = 0
    for s in segments:
        assert s.start >= position and s.end > s.start
        assert text[position:s.start].strip() == "", "text between segments must be whitespace only"
        piece = text[s.start:s.end]
        assert piece == piece.strip()
        position = s.end
    assert text[position:].strip() == ""
    assert segment(text, fmt) == segments


def test_agreement_with_checked_boundaries_is_at_least_98_percent():
    """Verification threshold for sentence splitting (spec 001, Verification)."""
    total = agreed = 0
    disagreements = []
    for name in FILINGS:
        text, fmt = load(name)
        produced = {squash(text[s.start:s.end]) for s in segment(text, fmt)}
        labels = (BOUNDARIES / (Path(name).stem + ".txt")).read_text(encoding="utf-8")
        for expected in (line for line in labels.split("\n") if line.strip()):
            total += 1
            if squash(expected) in produced:
                agreed += 1
            else:
                disagreements.append(f"{name}: {expected[:90]}")
    assert total >= 200
    assert agreed / total >= 0.98, f"{agreed}/{total}\n" + "\n".join(disagreements)


def test_label_followed_by_a_gap_and_running_text_is_prose_not_a_table_row():
    text = "NOTE A:   The accompanying unaudited consolidated financial statements\n          have been prepared. They are short.\n"
    assert kinds(text) == ["sentence", "sentence"]


def test_justified_prose_line_with_one_wide_gap_is_not_a_table_row():
    text = "month period ended September 30, 2000, the net   unrealized\nloss on these securities decreased by $1.8 million. For the\nnine month period it rose.\n"
    assert kinds(text) == ["sentence", "sentence"]


def test_figure_wrapped_onto_its_own_line_is_a_table_row_not_a_heading():
    text = "Income tax expense                            273\n  231\n\nOther Expenses\n"
    assert kinds(text) == ["table_row", "table_row", "heading"]
