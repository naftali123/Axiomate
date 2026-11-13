"""Determinism (task T030, SC-005) and the spec's edge cases (task T031)."""
import pytest

import support
from axiomate.claims.query import get_claim, list_claims
from axiomate.claims.submit import submit
from axiomate.errors import AxiomateError
from axiomate.store import db

FIXTURES = [support.load(p) for p in support.GOOD]


def build(path, fixtures):
    """A full run: ingest every filing, submit every claim, correct one."""
    conn = db.connect(path)
    support.ingest_all(conn)
    first = None
    for fixture in fixtures:
        result = submit(conn, support.submission(conn, fixture))
        if fixture["name"] == "everi_2024q1_net_income":
            first = result.claim_id
    correction = dict(support.submission(conn, support.good("everi_2024q1_net_income")), value_kind="exact")
    submit(conn, correction, supersedes=first)
    dump = db.export(conn)
    conn.close()
    return dump


def test_two_fresh_runs_give_identical_exports(tmp_path):
    first = build(tmp_path / "a.db", FIXTURES)
    second = build(tmp_path / "b.db", FIXTURES)
    assert first == second
    assert first.count('"schema_version"') >= 1 + len(FIXTURES)


def test_order_of_submission_does_not_change_the_export(tmp_path):
    assert build(tmp_path / "a.db", FIXTURES) == build(tmp_path / "b.db", list(reversed(FIXTURES)))


def test_running_everything_again_on_the_same_store_changes_nothing(filings):
    for fixture in FIXTURES:
        submit(filings, support.submission(filings, fixture))
    before = db.export(filings)
    assert all(v is False for v in (
        [submit(filings, support.submission(filings, f)).created for f in FIXTURES]))
    support.ingest_all(filings)
    assert db.export(filings) == before


# Edge case: the same figure appears twice in one document (headline and table).
def test_same_figure_in_a_sentence_and_in_a_table_gives_two_claims(filings):
    base = support.submission(filings, support.good("orrstown_1997_9m_net_income"))
    text = filings.execute("SELECT canonical_text FROM document WHERE id = ?", (base["document_id"],)).fetchone()[0]
    spans = []
    position = -1
    while (position := text.find("2,006", position + 1)) >= 0:
        row = filings.execute(
            "SELECT idx, kind FROM segment WHERE document_id = ? AND start <= ? AND end >= ?",
            (base["document_id"], position, position + 5)).fetchone()
        spans.append((position, row["idx"], row["kind"]))
    assert {kind for _, _, kind in spans} >= {"sentence", "table_row"}
    results = []
    for position, index, _ in spans:
        claim = dict(base, span_start=position, span_end=position + 5, quote="2,006", segment_index=index)
        results.append(submit(filings, claim))
    assert len({r.claim_id for r in results}) == len(spans) >= 2
    found = list_claims(filings, company_cik=base["company_cik"], metric="net_income", fiscal_year=1997, fiscal_period="9M")
    assert len(found) == len(spans) and len({c["segment_index"] for c in found}) == len(spans)


# Edge case: a period stated relatively is stored as an explicit period plus a named assumption.
def test_relative_period_is_stored_explicitly_with_its_assumption(filings):
    result = submit(filings, support.submission(filings, support.good("everi_2023q1_net_income")))
    stored = get_claim(filings, result.claim_id)
    assert "the same period in the prior year" in stored["quote"]
    assert (stored["period_start"], stored["period_end"]) == ("2023-01-01", "2023-03-31")
    assert stored["status"] == "formal-with-assumptions" and stored["assumptions"][0]["field"] == "period_start"


# Edge case: a value is a range, a bound or an approximation.
@pytest.mark.parametrize("name, changes", [
    ("everi_2024q1_revenue", {"value_kind": "range", "value_low": "189000000", "value_high": "190000000"}),
    ("orrstown_1997q3_net_income", {"value_kind": "at_least"}),
    ("orrstown_1997_9m_net_income", {"value_kind": "at_most"}),
    ("everi_2024q1_net_income", {"value_kind": "approximate"}),
])
def test_range_bound_and_approximate_values_are_stored_as_such(filings, name, changes):
    result = submit(filings, dict(support.submission(filings, support.good(name)), **changes))
    stored = get_claim(filings, result.claim_id)
    assert stored["value_kind"] == changes["value_kind"]
    if "value_low" in changes:
        assert (stored["value_low"], stored["value_high"]) == (changes["value_low"], changes["value_high"])


def test_a_range_given_the_wrong_way_round_is_rejected(filings):
    claim = dict(support.submission(filings, support.good("everi_2024q1_revenue")),
                 value_kind="range", value_low="190000000", value_high="189000000")
    with pytest.raises(AxiomateError) as raised:
        submit(filings, claim)
    assert raised.value.code == "schema_invalid"


# Edge case: a figure restated in a later document for an earlier period.
def test_restated_figure_is_a_second_claim_for_the_same_period_with_a_later_date(filings):
    for name in ("orrstown_1996_9m_eps", "orrstown_1996_9m_eps_restated"):
        submit(filings, support.submission(filings, support.good(name)))
    found = list_claims(filings, company_cik="0000826154", metric="earnings_per_share", fiscal_year=1996, fiscal_period="9M")
    assert [c["value_low"] for c in found] == ["1.72", "1.64"]
    assert found[0]["said_on"] < found[1]["said_on"] and found[0]["document_id"] != found[1]["document_id"]
    assert found[0]["period_end"] == found[1]["period_end"] == "1996-09-30"


# Edge case: a fiscal year that does not match the calendar year.
def test_non_calendar_fiscal_year_keeps_fiscal_label_and_explicit_dates(filings):
    result = submit(filings, support.submission(filings, support.good("geospace_fy2021q3_rental_revenue")))
    stored = get_claim(filings, result.claim_id)
    assert (stored["fiscal_year"], stored["fiscal_period"]) == (2021, "Q3")
    assert (stored["period_start"], stored["period_end"]) == ("2021-04-01", "2021-06-30")
    assert any(a["origin"] == "context_store" and a["field"] == "fiscal_period" for a in stored["assumptions"])
