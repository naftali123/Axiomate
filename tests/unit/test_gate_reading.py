"""Rules that read figures, periods and terms from a quote (spec 002, tasks T001-T003)."""
from decimal import Decimal

import pytest

from axiomate.gate.lexicon import approximation_before, hedges_in, metric_evidence
from axiomate.gate.numbers import find_figures
from axiomate.gate.periods import find_periods


def figures(text):
    return [(f.text, f.value, f.scale, f.negative) for f in find_figures(text)]


# -- figures ---------------------------------------------------------------
@pytest.mark.parametrize("text, expected", [
    ("Revenues\t$\t189,346", [("189,346", Decimal("189346"), None, False)]),
    ("decreased by $1.8 million during", [("1.8", Decimal("1.8"), "millions", True)]),
    ("to approximately $189.3 million for", [("189.3", Decimal("189.3"), "millions", False)]),
    ("Net income per share was\n$ .71 during", [(".71", Decimal("0.71"), None, False)]),
    ("Net loss\t(8,180)", [("8,180", Decimal("8180"), None, True)]),
    ("was $(1.8) million, compared", [("1.8", Decimal("1.8"), "millions", True)]),
    ("net loss of $4.6 million", [("4.6", Decimal("4.6"), "millions", True)]),
    ("a decrease of $11.1 million, or 6%", [("11.1", Decimal("11.1"), "millions", True), ("6", Decimal("6"), None, False)]),
    ("revenues of $4.2 billion", [("4.2", Decimal("4.2"), "billions", False)]),
    ("totaled $ 608,000 for", [("608,000", Decimal("608000"), None, False)]),
    ("increased by $13.4 million during", [("13.4", Decimal("13.4"), "millions", False)]),
    ("$1,504 thousand", [("1,504", Decimal("1504"), "thousands", False)]),
    ("Net Income                                  $5,520", [("5,520", Decimal("5520"), None, False)]),
])
def test_figures_are_read_with_scale_word_and_sign(text, expected):
    assert figures(text) == expected


def test_a_level_after_a_decrease_is_not_negative():
    found = {f.text: f.negative for f in find_figures(
        "Total revenues decreased by approximately $11.1 million, or 6%, to approximately $189.3 million")}
    assert found == {"11.1": True, "6": False, "189.3": False}


def test_figures_carry_their_position_and_percent_mark():
    text = "grew 5.2% to $4.2 billion"
    first, second = find_figures(text)
    assert text[first.start:first.end] == "5.2" and first.percent and not second.percent


def test_dates_are_read_as_figures_but_words_are_not():
    assert [f.text for f in find_figures("three months ended March 31, 2024")] == ["31", "2024"]
    assert find_figures("Total revenues decreased") == []


# -- periods ---------------------------------------------------------------
@pytest.mark.parametrize("text, expected", [
    ("for the three months ended March 31, 2024", [("2024-01-01", "2024-03-31")]),
    ("during the six months ended June 30, 2021 as compared", [("2021-01-01", "2021-06-30")]),
    ("the nine months\nended September 30, 1996", [("1996-01-01", "1996-09-30")]),
    ("for the three and nine months ended June 30, 2021 was", [("2021-04-01", "2021-06-30"), ("2020-10-01", "2021-06-30")]),
    ("the year ended December 31, 2023", [("2023-01-01", "2023-12-31")]),
    ("twelve months ended September 30, 2021", [("2020-10-01", "2021-09-30")]),
    ("quarter ended June 30, 2021", [("2021-04-01", "2021-06-30")]),
    ("three months ended February 29, 2024", [("2023-12-01", "2024-02-29")]),
])
def test_periods_with_an_end_date_are_read_exactly(text, expected):
    assert [(p.start, p.end) for p in find_periods(text)] == expected


@pytest.mark.parametrize("text, year, label", [
    ("for the first nine months of 1997 was", 1997, "9M"),
    ("during 1997's third quarter", 1997, "Q3"),
    ("for the third quarter of 1997", 1997, "Q3"),
    ("the first six months of 2000", 2000, "H1"),
    ("the first quarter of 2024", 2024, "Q1"),
    ("for fiscal year 2021", 2021, "FY"),
])
def test_periods_named_by_label_and_year_are_read(text, year, label):
    (period,) = find_periods(text)
    assert (period.fiscal_year, period.fiscal_period, period.end) == (year, label, None)


@pytest.mark.parametrize("text", [
    "for the same period in the prior year", "compared to $1,504,000 for the same period in 1995",
    "for the first nine months was $ 1.72", "Total revenues decreased by approximately $11.1 million",
    "March 31, 2024", "Revenues\t$\t189,346",
])
def test_relative_and_incomplete_phrases_are_not_periods(text):
    assert find_periods(text) == []


# -- terms -----------------------------------------------------------------
@pytest.mark.parametrize("text, metric", [
    ("Total revenues decreased by", "revenue"), ("Revenues\t$\t189,346", "revenue"), ("Net sales were", "revenue"),
    ("we had net income of approximately", "net_income"), ("Net loss\t(8,180)", "net_income"),
    ("Net after tax income for the first nine months", "net_income"), ("Net Income (Loss)", "net_income"),
    ("Net cash provided by operating activities decreased", "operating_cash_flow"),
    ("Net cash used in operating activities", "operating_cash_flow"),
    ("Net income per share was $ .71", "earnings_per_share"), ("the 1.64 per share realized", "earnings_per_share"),
    ("Diluted earnings per share", "earnings_per_share"),
])
def test_metric_terms_are_recognized(text, metric):
    assert metric_evidence(text, metric) == "term"


@pytest.mark.parametrize("text, metric", [
    ("Rental revenue for the three months", "revenue"), ("the decline in Games revenues described below", "revenue"),
    ("Gaming operations revenue", "revenue"), ("Interest income", "net_income"),
])
def test_component_of_a_metric_is_not_the_metric(text, metric):
    assert metric_evidence(text, metric) in ("component", None)


def test_per_share_wording_is_not_evidence_for_net_income_itself():
    assert metric_evidence("Net income per share was $ .71", "net_income") is None
    assert metric_evidence("net income of $ 728,000, or $ .71 per share", "net_income") == "term"


def test_absent_terms_give_no_evidence():
    assert metric_evidence("compared to $1,504,000 for the same period in 1995", "net_income") is None
    assert metric_evidence("Total revenues decreased", "operating_cash_flow") is None


def test_approximation_word_counts_only_just_before_the_figure():
    text = "decreased by $11.1 million, or 6%, to approximately $189.3 million"
    eleven, six, level = find_figures(text)
    assert not approximation_before(text, eleven.start) and approximation_before(text, level.start)
    assert approximation_before("about 5%", 6) and approximation_before("roughly $ 4", 10)


@pytest.mark.parametrize("text, kinds", [
    ("we expect revenue of $4.2 billion", {"forward"}), ("revenue is expected to reach", {"forward"}),
    ("our guidance for the year", {"forward"}), ("revenue may decline if demand weakens", {"conditional"}),
    ("according to analysts, revenue was", {"reported"}), ("revenue was $4.2 billion", set()),
    ("net income of approximately $4.6 million", set()), ("Maybank reported revenue", set()),
])
def test_hedging_words_are_found_by_kind(text, kinds):
    assert hedges_in(text) == kinds
