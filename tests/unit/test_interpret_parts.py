"""Segment selection, the reply model and the reply store (spec 002, tasks T014-T016)."""
import json

import pytest

import support
from axiomate.documents.html_text import canonical_from_html
from axiomate.documents.segment import segment
from axiomate.errors import AxiomateError
from axiomate.interpret.replies import ReplyStore, reply_key
from axiomate.interpret.reply import Reply
from axiomate.interpret.select import request_text, select

TEXT = "\n".join([
    "Results of Operations",                                   # 0 heading
    "(In thousands, except per share amounts)",                # 1
    "\tThree Months Ended March 31,",                          # 2 row
    "\t2024\t2023",                                            # 3 row
    "Total revenues\t189,346\t200,472",                        # 4 row
    "Cost of sales\t50,000\t60,000",                           # 5 row: "sales" is revenue wording
    "Operating expenses\t10,000\t9,000",                       # 6 row: no metric
    "Net income\t4,554\t28,066",                               # 7 row
    "Earnings per share:",                                     # 8
    "Basic\t$\t0.05\t$\t0.32",                                 # 9 row
    "Diluted\t$\t0.05\t$\t0.30",                               # 10 row
    "Overview",                                                # 11 heading
    "We operate in two segments.",                             # 12
    "Our headcount grew by 40 people.",                        # 13 digit, no metric
    "Total revenues decreased by approximately $11.1 million, or 6%.",  # 14
    "Net income improved.",                                    # 15 metric, no digit
])
SEGMENTS = segment(TEXT, "html")


def test_fixture_text_is_segmented_one_line_each():
    assert len(SEGMENTS) == 16


def test_only_segments_with_a_figure_and_a_metric_term_are_selected():
    chosen = [s.index for s in select(TEXT, SEGMENTS)]
    assert chosen == [4, 5, 7, 9, 10, 14]


def test_rows_under_a_per_share_subheading_are_selected_through_it():
    by_index = {s.index: s for s in select(TEXT, SEGMENTS)}
    assert 8 in by_index[9].context and 8 in by_index[10].context


def test_table_row_gets_its_table_heading_and_what_precedes_the_table():
    row = next(s for s in select(TEXT, SEGMENTS) if s.index == 7)
    assert row.context == [0, 1, 2, 3]


def test_sentence_gets_the_nearest_heading_and_the_two_sentences_before_it():
    sentence = next(s for s in select(TEXT, SEGMENTS) if s.index == 14)
    assert sentence.context == [11, 12, 13]


def test_request_text_marks_context_apart_from_the_segment():
    row = next(s for s in select(TEXT, SEGMENTS) if s.index == 7)
    text = request_text(TEXT, SEGMENTS, row)
    context, _, quotable = text.partition("SEGMENT")
    assert "Three Months Ended March 31," in context and "Net income\t4,554\t28,066" in quotable
    assert "Net income" not in context
    assert request_text(TEXT, SEGMENTS, row) == text


def test_selection_never_depends_on_tags():
    html = (support.DOCS / "everi_2024q1_10q.html").read_text(encoding="utf-8")
    text = canonical_from_html(html)
    segments = segment(text, "html")
    chosen = select(text, segments)
    assert 20 < len(chosen) < len(segments) / 2
    assert chosen == select(text, segments)


# -- reply model -------------------------------------------------------------
CANDIDATE = {
    "quote": "4,554", "quote_occurrence": 1, "company_cik": None, "metric": "net_income", "value_kind": "exact",
    "value_low": "4554000", "value_high": "4554000", "stated_value": "4554", "stated_scale": "thousands",
    "unit": "currency", "currency": "USD", "period_kind": "duration", "fiscal_year": 2024, "fiscal_period": "Q1",
    "period_start": "2024-01-01", "period_end": "2024-03-31", "basis": "reported", "nature": "actual",
    "comparison": "absolute", "baseline_start": None, "baseline_end": None, "polarity": "affirmed",
    "flags": [], "assumptions": [{"statement": "Column 1 is the three months ended March 31, 2024", "field": "period_start"}],
}


def test_reply_holds_candidates_and_tolerates_missing_optional_fields():
    reply = Reply.model_validate({"candidates": [CANDIDATE, {"quote": "x", "flags": [{"reason": "opinion", "field": None, "note": None}]}]})
    assert reply.candidates[0].metric == "net_income" and reply.candidates[1].metric is None
    assert reply.candidates[1].quote_occurrence == 1
    assert Reply.model_validate({"candidates": []}).candidates == []


@pytest.mark.parametrize("bad", [{}, {"candidates": [{"metric": "revenue"}]}, {"candidates": "none"}, {"candidates": [{"quote": ""}]}])
def test_malformed_reply_is_refused(bad):
    with pytest.raises(ValueError):
        Reply.model_validate(bad)


# -- reply store -------------------------------------------------------------
def test_key_depends_on_instructions_model_and_text():
    key = reply_key("1", "model-a", "text")
    assert len(key) == 64 and key == reply_key("1", "model-a", "text")
    assert len({key, reply_key("2", "model-a", "text"), reply_key("1", "model-b", "text"), reply_key("1", "model-a", "text ")}) == 4


def test_reply_is_written_once_and_read_back_unchanged(tmp_path):
    store = ReplyStore(tmp_path / "replies")
    key = reply_key("1", "m", "text")
    assert store.read(key) is None
    record = {"key": key, "instruction_version": "1", "model": "m", "served_model": "m", "request_text": "text",
              "reply": {"candidates": [CANDIDATE]}, "input_tokens": 10, "output_tokens": 5}
    store.write(record)
    assert store.read(key) == record
    assert json.loads((tmp_path / "replies" / f"{key}.json").read_text(encoding="utf-8")) == record
    store.write(record)  # identical: nothing happens
    with pytest.raises(AxiomateError) as raised:
        store.write(record | {"reply": {"candidates": []}})
    assert raised.value.code == "reply_exists"
    assert store.read(key) == record


def test_record_whose_key_does_not_match_its_content_is_refused(tmp_path):
    store = ReplyStore(tmp_path)
    with pytest.raises(AxiomateError):
        store.write({"key": "0" * 64, "instruction_version": "1", "model": "m", "served_model": "m",
                     "request_text": "text", "reply": {"candidates": []}, "input_tokens": 1, "output_tokens": 1})
