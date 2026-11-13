"""Claim, flag and assumption models (task T019)."""
from decimal import Decimal

import pytest

from axiomate.claims.schema import SCHEMA_VERSION, parse_claim
from axiomate.errors import AxiomateError

DOC = "a" * 64


def base(**changes) -> dict:
    claim = {
        "company_cik": "0001318568", "metric": "revenue", "value_kind": "exact",
        "value_low": "189300000", "value_high": "189300000", "stated_value": "189.3", "stated_scale": "millions",
        "unit": "currency", "currency": "USD", "period_kind": "duration", "fiscal_year": 2024, "fiscal_period": "Q1",
        "period_start": "2024-01-01", "period_end": "2024-03-31", "basis": "reported", "nature": "actual",
        "comparison": "absolute", "baseline_start": None, "baseline_end": None, "polarity": "affirmed",
        "document_id": DOC, "segment_index": 4, "span_start": 10, "span_end": 20, "quote": "0123456789",
        "said_on": "2024-05-08",
    }
    claim.update(changes)
    return claim


def rejected(claim: dict) -> AxiomateError:
    with pytest.raises(AxiomateError) as raised:
        parse_claim(claim)
    return raised.value


def test_well_formed_claim_is_accepted_and_keeps_its_values():
    claim = parse_claim(base())
    assert claim.metric == "revenue" and claim.fiscal_year == 2024
    assert claim.flags == [] and claim.assumptions == [] and claim.status is None
    assert SCHEMA_VERSION


def test_segment_index_status_flags_and_assumptions_are_optional():
    data = base()
    del data["segment_index"]
    assert parse_claim(data).segment_index is None


@pytest.mark.parametrize("given, stored", [
    ("189300000", "189300000"), (189300000, "189300000"), ("1.80", "1.8"), (".71", "0.71"),
    ("-1800000", "-1800000"), (Decimal("28.10"), "28.1"), ("0.0", "0"), ("1000", "1000"),
])
def test_decimals_are_exact_and_stored_in_one_plain_form(given, stored):
    claim = parse_claim(base(value_low=given, value_high=given))
    assert claim.value_low == stored and claim.value_high == stored


@pytest.mark.parametrize("bad", [1.8, "abc", "1e6", "1,800", True, "", " 5", "NaN", "Infinity"])
def test_floats_and_malformed_numbers_are_rejected(bad):
    error = rejected(base(value_low=bad))
    assert (error.code, error.field) == ("schema_invalid", "value_low")


@pytest.mark.parametrize("field", [
    "company_cik", "metric", "value_kind", "value_low", "value_high", "stated_value", "stated_scale", "unit",
    "currency", "period_kind", "fiscal_year", "fiscal_period", "period_start", "period_end", "basis", "nature",
    "comparison", "baseline_start", "baseline_end", "polarity", "document_id", "span_start", "span_end", "quote",
    "said_on",
])
def test_a_missing_field_is_rejected_by_name(field):
    data = base()
    del data[field]
    error = rejected(data)
    assert (error.code, error.field) == ("schema_invalid", field)


@pytest.mark.parametrize("field, value", [
    ("polarity", "maybe"), ("stated_scale", "dozens"), ("value_kind", "roughly"), ("unit", "shares"),
    ("period_kind", "moment"), ("fiscal_period", "Q5"), ("basis", "pro-forma"), ("nature", "rumour"),
    ("comparison", "relative"), ("fiscal_year", "2024"), ("fiscal_year", 1492), ("fiscal_year", True),
    ("period_start", "01/01/2024"), ("period_end", "2024-02-30"), ("said_on", "yesterday"),
    ("company_cik", "1318568"), ("company_cik", 1318568), ("currency", "usd"), ("currency", "DOLLARS"),
    ("document_id", "abc"), ("span_start", -1), ("span_start", "10"), ("span_end", 10), ("quote", ""),
    ("segment_index", -1), ("metric", 7), ("status", "certain"),
])
def test_a_malformed_value_is_rejected_by_name(field, value):
    error = rejected(base(**{field: value}))
    assert (error.code, error.field) == ("schema_invalid", field)


def test_unknown_field_is_rejected():
    error = rejected(base(mood="optimistic"))
    assert (error.code, error.field) == ("schema_invalid", "mood")


def test_input_that_is_not_an_object_is_rejected():
    assert rejected(["not", "a", "claim"]).code == "schema_invalid"


@pytest.mark.parametrize("metric", ["ebitda", "gross_margin", "Revenue", ""])
def test_metric_outside_the_four_is_unknown_metric(metric):
    error = rejected(base(metric=metric))
    assert (error.code, error.field) == ("unknown_metric", "metric")


@pytest.mark.parametrize("changes, field", [
    ({"value_high": "-999999999999"}, "value_high"),
    ({"value_high": "189300001"}, "value_high"),
    ({"period_end": "1900-01-01"}, "period_end"),
    ({"currency": None}, "currency"),
    ({"unit": "percent"}, "currency"),
    ({"baseline_start": "2023-01-01", "baseline_end": "2023-03-31"}, "baseline_start"),
    ({"comparison": "change_vs_period", "baseline_start": "2023-03-31", "baseline_end": "2023-01-01"}, "baseline_end"),
])
def test_fields_that_contradict_each_other_are_rejected(changes, field):
    error = rejected(base(**changes))
    assert (error.code, error.field) == ("schema_invalid", field)


def test_range_bound_and_percent_values_are_accepted():
    assert parse_claim(base(value_kind="range", value_low="100", value_high="200")).value_high == "200"
    assert parse_claim(base(value_kind="at_least")).value_kind == "at_least"
    assert parse_claim(base(unit="percent", currency=None, stated_scale="units")).currency is None
    change = parse_claim(base(comparison="change_vs_period", baseline_start="2023-01-01", baseline_end="2023-03-31"))
    assert change.baseline_end == "2023-03-31"


# FR-017: an empty field needs an unresolved flag that names it.
FLAG = {"reason": "vague_quantity", "field": "value_low", "resolved": False, "note": "no amount stated"}
VALUE_EMPTY = {"value_kind": None, "value_low": None, "value_high": None, "stated_value": None,
               "stated_scale": None, "unit": None}


@pytest.mark.parametrize("field", ["value_low", "metric", "period_start", "stated_value", "unit", "company_cik", "polarity"])
def test_empty_field_without_a_flag_is_rejected(field):
    error = rejected(base(**{field: None}))
    assert (error.code, error.field) == ("empty_field_without_flag", field)


def test_a_flag_on_one_part_of_the_value_covers_the_whole_value():
    claim = parse_claim(base(**VALUE_EMPTY, flags=[FLAG]))
    assert claim.value_low is None and claim.unit is None and claim.flags[0].reason == "vague_quantity"


def test_a_flag_does_not_cover_fields_of_another_group():
    error = rejected(base(**VALUE_EMPTY, period_start=None, flags=[FLAG]))
    assert (error.code, error.field) == ("empty_field_without_flag", "period_start")


def test_a_resolved_flag_does_not_excuse_an_empty_field():
    error = rejected(base(**VALUE_EMPTY, flags=[FLAG | {"resolved": True}]))
    assert error.code == "empty_field_without_flag"


def test_change_claim_without_baseline_needs_a_flag():
    error = rejected(base(comparison="change_vs_period"))
    assert (error.code, error.field) == ("empty_field_without_flag", "baseline_start")
    flag = {"reason": "underspecified_time", "field": "baseline_start", "resolved": False}
    assert parse_claim(base(comparison="change_vs_period", flags=[flag])).baseline_start is None


@pytest.mark.parametrize("flag, field", [
    ({"reason": "boring", "field": "metric", "resolved": False}, "flags[0].reason"),
    ({"reason": "opinion", "field": "mood", "resolved": False}, "flags[0].field"),
    ({"reason": "opinion", "field": "metric", "resolved": "no"}, "flags[0].resolved"),
    ({"reason": "opinion", "field": "metric"}, "flags[0].resolved"),
    ({"reason": "opinion", "resolved": False, "extra": 1}, "flags[0].extra"),
])
def test_malformed_flag_is_rejected_by_name(flag, field):
    error = rejected(base(flags=[flag]))
    assert (error.code, error.field) == ("schema_invalid", field)


@pytest.mark.parametrize("assumption, field", [
    ({"statement": "", "field": "metric", "origin": "human"}, "assumptions[0].statement"),
    ({"statement": "x", "field": "metric", "origin": "guess"}, "assumptions[0].origin"),
    ({"statement": "x", "field": "metric"}, "assumptions[0].origin"),
    ({"statement": "x", "field": "colour", "origin": "model"}, "assumptions[0].field"),
])
def test_malformed_assumption_is_rejected_by_name(assumption, field):
    error = rejected(base(assumptions=[assumption]))
    assert (error.code, error.field) == ("schema_invalid", field)


def test_flag_and_assumption_field_and_note_are_optional():
    claim = parse_claim(base(flags=[{"reason": "opinion", "resolved": True}],
                             assumptions=[{"statement": "x", "origin": "context_store"}]))
    assert claim.flags[0].field is None and claim.flags[0].note is None and claim.assumptions[0].field is None
