"""Story 2 acceptance scenarios and the stage-5 verification checks (tasks T021, T026)."""
import json
import sqlite3

import pytest

import support
from axiomate.claims.query import get_claim
from axiomate.claims.submit import submit
from axiomate.cli import main
from axiomate.errors import AxiomateError

GOOD = [support.load(p) for p in support.GOOD]
BAD = [support.load(p) for p in support.BAD]
CODES = {"schema_invalid", "unknown_metric", "document_not_found", "span_mismatch", "span_outside_segment",
         "said_on_mismatch", "status_mismatch", "empty_field_without_flag"}


def count(conn, table="claim"):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def rejected(conn, claim, **options) -> AxiomateError:
    with pytest.raises(AxiomateError) as raised:
        submit(conn, claim, **options)
    return raised.value


# Scenario 1 and verification: good claims are accepted, 100%.
@pytest.mark.parametrize("fixture", GOOD, ids=[g["name"] for g in GOOD])
def test_every_good_claim_is_stored_with_its_status(filings, fixture):
    claim = support.submission(filings, fixture)
    result = submit(filings, claim)
    assert result.created is True and result.version == 1 and len(result.claim_id) == 64
    assert result.status == fixture["expected_status"]
    stored = get_claim(filings, result.claim_id)
    assert stored["status"] == fixture["expected_status"] and stored["quote"] == fixture["quote"]
    assert stored["metric"] == fixture["claim"]["metric"] and stored["said_on"] == fixture["claim"]["said_on"]
    assert stored["fiscal_year"] == fixture["claim"]["fiscal_year"] and stored["period_end"] == fixture["claim"]["period_end"]
    assert [f["reason"] for f in stored["flags"]] == [f["reason"] for f in fixture["flags"]]
    assert [a["statement"] for a in stored["assumptions"]] == [a["statement"] for a in fixture["assumptions"]]
    text = filings.execute("SELECT canonical_text FROM document WHERE id = ?", (stored["document_id"],)).fetchone()[0]
    assert text[stored["span_start"]:stored["span_end"]] == stored["quote"]


def test_status_and_segment_index_may_be_left_to_the_store(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    expected_index = claim.pop("segment_index")
    del claim["status"]
    result = submit(filings, claim)
    assert result.status == "formal"
    assert get_claim(filings, result.claim_id)["segment_index"] == expected_index


# Verification: bad claims are rejected with the expected code, 100% (SC-004, task T026).
@pytest.mark.parametrize("fixture", BAD, ids=[b["name"] for b in BAD])
def test_every_corrupted_claim_is_rejected_with_its_code(filings, fixture):
    base = support.submission(filings, support.good(fixture["base"]))
    claim = support.corrupt(filings, base, fixture["operations"])
    error = rejected(filings, claim)
    assert (error.code, error.field) == (fixture["expected_error"], fixture["expected_field"])
    assert count(filings) == 0 and count(filings, "flag") == 0 and count(filings, "assumption") == 0


def test_rejection_rate_on_the_corrupted_set_is_100_percent(filings):
    seen = {}
    for fixture in BAD:
        claim = support.corrupt(filings, support.submission(filings, support.good(fixture["base"])), fixture["operations"])
        try:
            submit(filings, claim)
        except AxiomateError as error:
            seen.setdefault(fixture["expected_error"], []).append(error.code == fixture["expected_error"])
        else:
            seen.setdefault(fixture["expected_error"], []).append(False)
    assert set(seen) == CODES
    assert all(len(results) >= 5 and all(results) for results in seen.values())
    assert count(filings) == 0


# Scenario 2: a quote that is not at the stated address.
def test_quote_that_differs_from_the_text_at_its_address_is_rejected(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    claim["quote"] = claim["quote"].replace("189.3", "198.3")
    error = rejected(filings, claim)
    assert (error.code, error.field) == ("span_mismatch", "quote")


def test_quote_copied_from_elsewhere_in_the_document_is_rejected(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    other = support.submission(filings, support.good("everi_2024q1_net_income"))
    claim["quote"] = other["quote"]
    assert rejected(filings, claim).code == "span_mismatch"


def test_named_segment_must_hold_the_span(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    claim["segment_index"] += 1
    error = rejected(filings, claim)
    assert (error.code, error.field) == ("span_outside_segment", "segment_index")
    claim["segment_index"] = 10**6
    assert rejected(filings, claim).code == "span_outside_segment"


def test_span_running_over_two_sentences_is_rejected(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    del claim["segment_index"]
    text = filings.execute("SELECT canonical_text FROM document WHERE id = ?", (claim["document_id"],)).fetchone()[0]
    seg_end = filings.execute("SELECT end FROM segment WHERE document_id = ? AND start <= ? AND end >= ?",
                              (claim["document_id"], claim["span_start"], claim["span_end"])).fetchone()[0]
    claim["span_end"] = seg_end + 12
    claim["quote"] = text[claim["span_start"]:claim["span_end"]]
    assert rejected(filings, claim).code == "span_outside_segment"


# Scenario 3: a missing required field is named.
def test_claim_without_fiscal_period_is_rejected_naming_it(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    del claim["fiscal_period"]
    error = rejected(filings, claim)
    assert (error.code, error.field) == ("schema_invalid", "fiscal_period")
    assert count(filings) == 0


# Scenario 4: a correction makes a new version and keeps the old one.
def test_correction_creates_a_new_version_and_keeps_the_earlier_one(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    first = submit(filings, claim)
    corrected = dict(claim, basis="adjusted", status="formal-with-assumptions",
                     assumptions=[{"statement": "The figure is on an adjusted basis", "field": "basis", "origin": "human"}])
    second = submit(filings, corrected, supersedes=first.claim_id)
    assert (second.claim_id, second.version, second.created) == (first.claim_id, 2, True)
    assert get_claim(filings, first.claim_id)["version"] == 2
    assert get_claim(filings, first.claim_id)["basis"] == "adjusted"
    old = get_claim(filings, first.claim_id, version=1)
    assert old["basis"] == "reported" and old["status"] == "formal" and old["assumptions"] == []
    assert count(filings) == 2


def test_correction_keeps_its_id_even_when_the_span_changes(filings):
    first = submit(filings, support.submission(filings, support.good("everi_2024q1_revenue")))
    other = support.submission(filings, support.good("everi_2024q1_net_income"))
    second = submit(filings, other, supersedes=first.claim_id)
    assert second.claim_id == first.claim_id and second.version == 2


def test_correcting_a_claim_that_does_not_exist_is_not_found(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    error = rejected(filings, claim, supersedes="f" * 64)
    assert (error.code, error.field) == ("not_found", "supersedes")


def test_same_claim_twice_is_stored_once(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue_change"))
    first = submit(filings, claim)
    again = submit(filings, claim)
    assert (again.claim_id, again.version, again.created) == (first.claim_id, 1, False)
    assert count(filings) == 1 and count(filings, "assumption") == 2
    same = submit(filings, claim, supersedes=first.claim_id)
    assert same.version == 1 and same.created is False


def test_different_claim_at_the_same_address_needs_supersedes(filings):
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    submit(filings, claim)
    error = rejected(filings, dict(claim, basis="adjusted"))
    assert error.code == "claim_exists"
    assert count(filings) == 1


# Scenario 5: what is not literally in the span is a named assumption.
def test_assumption_is_stored_with_its_origin_and_sets_the_status(filings):
    fixture = support.good("southalabama_2000_q1_net_income")
    claim = support.submission(filings, fixture)
    del claim["status"]
    result = submit(filings, claim)
    assert result.status == "formal-with-assumptions"
    stored = get_claim(filings, result.claim_id)["assumptions"]
    assert [(a["field"], a["origin"]) for a in stored] == [("period_start", "human"), ("stated_scale", "human")]
    assert all(a["statement"] for a in stored)


def test_unformalizable_claim_keeps_its_flag_and_empty_fields(filings):
    result = submit(filings, support.submission(filings, support.good("everi_2024q1_revenue_reason")))
    stored = get_claim(filings, result.claim_id)
    assert stored["status"] == "not-formalizable" and stored["value_low"] is None
    assert stored["flags"] == [{"reason": "vague_quantity", "field": "value_low", "resolved": False,
                                "note": "A decline is stated without an amount."}]


def test_stored_claims_cannot_be_altered(filings):
    submit(filings, support.submission(filings, support.good("everi_2024q1_revenue_reason")))
    for statement in ("UPDATE claim SET value_low = '1'", "DELETE FROM claim", "UPDATE flag SET resolved = 1",
                      "DELETE FROM flag", "UPDATE assumption SET origin = 'model'", "DELETE FROM assumption"):
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            filings.execute(statement)


def test_unknown_claim_is_not_found(filings):
    with pytest.raises(AxiomateError) as raised:
        get_claim(filings, "0" * 64)
    assert raised.value.code == "not_found"


# Command line (contract: contracts/cli.md).
def run(capsys, *args):
    code = main(list(args))
    return code, json.loads(capsys.readouterr().out)


def test_command_line_claim_add_and_correction(filings, tmp_path, capsys):
    store_path = filings.execute("PRAGMA database_list").fetchone()[2]
    claim = support.submission(filings, support.good("everi_2024q1_revenue"))
    claim["stated_value"] = 189.3  # a JSON number must be read exactly, not as a float
    path = tmp_path / "claim.json"
    path.write_text(json.dumps(claim), encoding="utf-8")
    code, first = run(capsys, "--db", store_path, "claim", "add", str(path))
    assert code == 0 and first["version"] == 1 and first["status"] == "formal" and first["created"] is True
    assert get_claim(filings, first["claim_id"])["stated_value"] == "189.3"

    path.write_text(json.dumps(dict(claim, nature="guidance")), encoding="utf-8")
    code, second = run(capsys, "--db", store_path, "claim", "add", str(path), "--supersedes", first["claim_id"])
    assert code == 0 and second["claim_id"] == first["claim_id"] and second["version"] == 2

    path.write_text(json.dumps(dict(claim, quote="not in the text")), encoding="utf-8")
    code, out = run(capsys, "--db", store_path, "claim", "add", str(path))
    assert code != 0 and out["error"] == "span_mismatch" and set(out) == {"error", "field", "message"}

    path.write_text("{not json", encoding="utf-8")
    code, out = run(capsys, "--db", store_path, "claim", "add", str(path))
    assert code != 0 and out["error"] == "schema_invalid"
    code, out = run(capsys, "--db", store_path, "claim", "add", str(tmp_path / "missing.json"))
    assert code != 0 and out["error"] == "unreadable_file"
