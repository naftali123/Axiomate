"""The comparison with tagged figures, on hand-built cases (task T026)."""
from axiomate.evaluate.tagged import judge, locate

FACT = {"id": "f1", "metric": "revenue", "shown": "189,346", "value": "189346000", "period_kind": "duration",
        "period_start": "2024-01-01", "period_end": "2024-03-31", "start": 100, "end": 107}
OTHER = FACT | {"id": "f2", "shown": "200,201", "value": "200201000", "period_start": "2023-01-01",
                "period_end": "2023-03-31", "start": 108, "end": 115}
CLAIM = {"id": "c1", "quote": "189,346", "span_start": 100, "span_end": 107, "metric": "revenue", "comparison": "absolute",
         "value_low": "189346000", "value_high": "189346000", "stated_value": "189346", "period_kind": "duration",
         "period_start": "2024-01-01", "period_end": "2024-03-31"}


def counts(result):
    return result["citing"], result["agreeing"], result["covered"]


def test_a_claim_on_the_tagged_figure_that_says_what_the_tag_says_agrees():
    result = judge([CLAIM], [FACT, OTHER])
    assert counts(result) == (1, 1, 1) and result["tagged_figures"] == 2
    assert result["uncited_tags"] == ["f2"] and result["disagreements"] == []


def test_a_claim_elsewhere_in_the_text_cites_nothing():
    assert counts(judge([CLAIM | {"span_start": 300, "span_end": 307}], [FACT])) == (0, 0, 0)


def test_each_kind_of_disagreement_is_named_and_does_not_cover_the_tag():
    cases = {
        "value": {"value_low": "189346", "value_high": "189346"},
        "period": {"period_start": "2023-01-01", "period_end": "2023-03-31"},
        "metric": {"metric": "net_income"},
        "comparison": {"comparison": "change_vs_period"},
    }
    for field, change in cases.items():
        result = judge([CLAIM | change], [FACT])
        assert counts(result) == (1, 0, 0), field
        assert result["disagreements"][0]["fields"] == [field] and result["disagreements"][0]["tag_id"] == "f1"


def test_equal_values_written_differently_agree():
    assert counts(judge([CLAIM | {"value_low": "189346000.00", "value_high": "1.89346E+8"}], [FACT])) == (1, 1, 1)


def test_a_quote_over_several_tagged_figures_cites_the_one_it_states():
    wide = CLAIM | {"span_start": 90, "span_end": 120}
    second = wide | {"id": "c2", "stated_value": "200201", "value_low": "200201000", "value_high": "200201000",
                     "period_start": "2023-01-01", "period_end": "2023-03-31"}
    result = judge([wide, second], [FACT, OTHER])
    assert counts(result) == (2, 2, 2) and result["uncited_tags"] == []


def test_two_claims_on_one_tag_cover_it_once_and_a_hidden_tag_is_not_expected():
    hidden = OTHER | {"start": None, "end": None}
    result = judge([CLAIM, CLAIM | {"id": "c9", "span_start": 95}], [FACT, hidden])
    assert counts(result) == (2, 2, 1) and (result["tagged_figures"], result["tagged_not_visible"]) == (1, 1)


def test_tags_are_located_in_the_extracted_text():
    html = ('<html><body><p>Revenue was $<ix:nonFraction id="a" name="us-gaap:Revenues">189.3</ix:nonFraction> million.</p>'
            '<table><tr><td>Net loss</td><td>(<ix:nonFraction name="us-gaap:NetIncomeLoss" id="b">4,554</ix:nonFraction>)</td></tr></table>'
            '</body></html>')
    text, spans = locate(html, ["a", "b"])
    assert [text[slice(*spans[i])] for i in ("a", "b")] == ["189.3", "4,554"]
