"""Story 3 acceptance scenarios (task T027)."""
import json

import pytest

import support
from axiomate.claims.query import claim_source, list_claims
from axiomate.claims.submit import submit
from axiomate.cli import main
from axiomate.errors import AxiomateError

ORRSTOWN = "0000826154"
EVERI = "0001318568"


@pytest.fixture
def stored(filings):
    """A store with every good claim; returns claim ids by fixture name."""
    ids = {}
    for path in support.GOOD:
        fixture = support.load(path)
        ids[fixture["name"]] = submit(filings, support.submission(filings, fixture)).claim_id
    return filings, ids


def ids_of(claims):
    return [c["claim_id"] for c in claims]


# Scenario 1: only matching claims, in a stable order.
def test_query_returns_exactly_the_claims_for_company_metric_and_period(stored):
    conn, ids = stored
    found = list_claims(conn, company_cik=ORRSTOWN, metric="net_income", fiscal_year=1996, fiscal_period="9M")
    assert ids_of(found) == [ids["orrstown_1996_9m_net_income"], ids["orrstown_1996_9m_net_income_restated"]]
    assert [c["said_on"] for c in found] == sorted(c["said_on"] for c in found)
    assert {(c["company_cik"], c["metric"], c["fiscal_year"], c["fiscal_period"]) for c in found} == {
        (ORRSTOWN, "net_income", 1996, "9M")}


def test_query_without_a_period_returns_the_whole_fiscal_year_in_order(stored):
    conn, ids = stored
    found = list_claims(conn, company_cik=ORRSTOWN, metric="net_income", fiscal_year=1996)
    assert set(ids_of(found)) == {ids["orrstown_1996_9m_net_income"], ids["orrstown_1996_9m_net_income_restated"],
                                  ids["orrstown_1996q3_net_income_restated"]}
    keys = [(c["period_end"], c["said_on"], c["document_id"], c["segment_index"], c["claim_id"]) for c in found]
    assert keys == sorted(keys)


def test_query_does_not_mix_companies_metrics_or_years(stored):
    conn, ids = stored
    assert ids_of(list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2024)) == [ids["everi_2024q1_net_income"]]
    assert ids_of(list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2023)) == [ids["everi_2023q1_net_income"]]
    assert list_claims(conn, company_cik=EVERI, metric="earnings_per_share", fiscal_year=2024) == []
    assert list_claims(conn, company_cik="0000000001", metric="revenue", fiscal_year=2024) == []


def test_query_order_does_not_depend_on_the_order_of_submission(filings, tmp_path):
    fixtures = [support.load(p) for p in support.GOOD]
    for fixture in reversed(fixtures):
        submit(filings, support.submission(filings, fixture))
    found = list_claims(filings, company_cik=ORRSTOWN, metric="net_income", fiscal_year=1996)
    keys = [(c["period_end"], c["said_on"], c["document_id"], c["segment_index"], c["claim_id"]) for c in found]
    assert len(found) == 3 and keys == sorted(keys)


def test_query_returns_the_latest_version_unless_all_are_asked_for(stored):
    conn, ids = stored
    claim = support.submission(conn, support.good("everi_2024q1_net_income"))
    corrected = dict(claim, value_kind="exact")
    submit(conn, corrected, supersedes=ids["everi_2024q1_net_income"])
    latest = list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2024)
    assert [(c["version"], c["value_kind"]) for c in latest] == [(2, "exact")]
    every = list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2024, all_versions=True)
    assert [(c["version"], c["value_kind"]) for c in every] == [(1, "approximate"), (2, "exact")]


def test_a_claim_corrected_to_another_period_leaves_the_old_query(stored):
    conn, ids = stored
    claim = support.submission(conn, support.good("everi_2024q1_net_income"))
    moved = dict(claim, fiscal_year=2023, period_start="2023-01-01", period_end="2023-03-31")
    submit(conn, moved, supersedes=ids["everi_2024q1_net_income"])
    assert list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2024) == []
    assert len(list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2024, all_versions=True)) == 1
    assert len(list_claims(conn, company_cik=EVERI, metric="net_income", fiscal_year=2023)) == 2


@pytest.mark.parametrize("arguments, code, field", [
    ({"company_cik": "ACME"}, "schema_invalid", "company_cik"),
    ({"metric": "ebitda"}, "unknown_metric", "metric"),
    ({"fiscal_year": "soon"}, "schema_invalid", "fiscal_year"),
    ({"fiscal_period": "Q5"}, "schema_invalid", "fiscal_period"),
])
def test_malformed_query_is_rejected(filings, arguments, code, field):
    query = {"company_cik": EVERI, "metric": "revenue", "fiscal_year": 2024} | arguments
    with pytest.raises(AxiomateError) as raised:
        list_claims(filings, **query)
    assert (raised.value.code, raised.value.field) == (code, field)


# Scenario 2 (SC-006): the source sentence in one lookup.
def test_source_gives_the_exact_span_sentence_document_and_date(stored):
    conn, ids = stored
    fixture = support.good("everi_2024q1_revenue")
    source = claim_source(conn, ids["everi_2024q1_revenue"])
    assert set(source) == {"claim_id", "version", "document_id", "published_on", "segment_index", "segment_text",
                           "span_start", "span_end", "quote"}
    assert source["document_id"] == support.document_ids()["everi_2024q1_10q.html"]
    assert source["published_on"] == "2024-05-08" and source["quote"] == fixture["quote"]
    assert fixture["quote"] in source["segment_text"]
    text = conn.execute("SELECT canonical_text FROM document WHERE id = ?", (source["document_id"],)).fetchone()[0]
    assert text[source["span_start"]:source["span_end"]] == source["quote"]


def test_every_stored_claim_traces_to_its_text(stored):
    """SC-003: 100% of stored claims have a span that matches the stored text."""
    conn, ids = stored
    for claim_id in ids.values():
        source = claim_source(conn, claim_id)
        assert source["quote"] in source["segment_text"]


def test_source_of_an_earlier_version_and_of_an_unknown_claim(stored):
    conn, ids = stored
    other = support.submission(conn, support.good("everi_2024q1_net_income"))
    submit(conn, other, supersedes=ids["everi_2024q1_revenue"])
    assert claim_source(conn, ids["everi_2024q1_revenue"])["quote"] == other["quote"]
    assert claim_source(conn, ids["everi_2024q1_revenue"], version=1)["quote"] == support.good("everi_2024q1_revenue")["quote"]
    for arguments in ({"claim_id": "0" * 64}, {"claim_id": ids["everi_2024q1_revenue"], "version": 9}):
        with pytest.raises(AxiomateError) as raised:
            claim_source(conn, **arguments)
        assert raised.value.code == "not_found"


# Scenario 3: flags and assumptions come back with the claim.
def test_flags_and_assumptions_are_returned_with_the_claim(stored):
    conn, ids = stored
    found = list_claims(conn, company_cik=EVERI, metric="revenue", fiscal_year=2024, fiscal_period="Q1")
    by_id = {c["claim_id"]: c for c in found}
    reason = by_id[ids["everi_2024q1_revenue_reason"]]
    assert reason["status"] == "not-formalizable" and reason["flags"][0]["reason"] == "vague_quantity"
    assert reason["assumptions"][0]["origin"] == "human"
    change = by_id[ids["everi_2024q1_revenue_change"]]
    assert change["status"] == "formal-with-assumptions" and len(change["assumptions"]) == 2 and change["flags"] == []
    assert by_id[ids["everi_2024q1_revenue"]]["flags"] == [] and by_id[ids["everi_2024q1_revenue"]]["assumptions"] == []


# Command line (contract: contracts/cli.md).
def run(capsys, *args):
    code = main(list(args))
    return code, json.loads(capsys.readouterr().out)


def test_command_line_list_source_and_export(stored, capsys):
    conn, ids = stored
    path = conn.execute("PRAGMA database_list").fetchone()[2]
    code, found = run(capsys, "--db", path, "claim", "list", "--company-cik", "826154", "--metric", "net_income",
                      "--fiscal-year", "1996", "--fiscal-period", "9M")
    assert code == 0 and ids_of(found) == [ids["orrstown_1996_9m_net_income"], ids["orrstown_1996_9m_net_income_restated"]]
    assert found[1]["assumptions"]

    code, source = run(capsys, "--db", path, "claim", "source", ids["orrstown_1996_9m_eps"])
    assert code == 0 and "1.72" in source["quote"] and source["published_on"].startswith("1996-")

    code, out = run(capsys, "--db", path, "claim", "source", "0" * 64)
    assert code != 0 and out["error"] == "not_found"
    code, out = run(capsys, "--db", path, "claim", "list", "--company-cik", EVERI, "--metric", "ebitda", "--fiscal-year", "2024")
    assert code != 0 and out["error"] == "unknown_metric"
    code, out = run(capsys, "--db", path, "claim", "list", "--metric", "revenue", "--fiscal-year", "2024")
    assert code != 0 and out["error"] == "schema_invalid" and out["field"] == "company_cik"

    code, dump = run(capsys, "--db", path, "export")
    assert code == 0 and len(dump["claim"]) == len(ids) and len(dump["document"]) == 10
