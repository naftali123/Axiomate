"""Interpretation from stored replies: Story 2 of spec 002 (tasks T017, T019, T020). No model is called."""
import json
import sqlite3

import pytest

import support
from axiomate.claims.query import get_claim
from axiomate.cli import main
from axiomate.documents.segment import Segment
from axiomate.errors import AxiomateError
from axiomate.interpret.replies import ReplyStore, reply_key
from axiomate.interpret.run import interpret
from axiomate.interpret.select import request_text, select
from axiomate.store import db

DOC = support.document_ids()["everi_2024q1_10q.html"]
VERSION, MODEL = "test-1", "test-model"

PROSE = {
    "quote": "to approximately $189.3 million for the three months ended March 31, 2024", "metric": "revenue",
    "value_kind": "approximate", "value_low": "189300000", "value_high": "189300000", "stated_value": "189.3",
    "stated_scale": "millions", "unit": "currency", "currency": "USD", "period_kind": "duration", "fiscal_year": 2024,
    "fiscal_period": "Q1", "period_start": "2024-01-01", "period_end": "2024-03-31", "basis": "reported",
    "nature": "actual", "comparison": "absolute", "polarity": "affirmed",
}
CHANGE = PROSE | {
    "quote": "Total revenues decreased by approximately $11.1 million", "value_low": "-11100000", "value_high": "-11100000",
    "stated_value": "11.1", "comparison": "change_vs_period", "baseline_start": "2023-01-01", "baseline_end": "2023-03-31",
    "assumptions": [{"statement": "The period is stated later in the sentence", "field": "period_start"},
                    {"statement": "The prior-year period is the three months ended March 31, 2023", "field": "baseline_start"}],
}
ROW = PROSE | {
    "quote": "189,346", "value_kind": "exact", "value_low": "189346000", "value_high": "189346000", "stated_value": "189346",
    "stated_scale": "thousands",
    "assumptions": [{"statement": "First column is the three months ended March 31, 2024, per the table heading", "field": "period_start"},
                    {"statement": "In thousands, per the table heading", "field": "stated_scale"}],
}
COMPONENT = ROW | {
    "quote": "97,122", "metric": None, "value_low": "97122000", "value_high": "97122000", "stated_value": "97122",
    "flags": [{"reason": "unmapped_metric", "field": "metric", "note": "Revenue of the Games segment, not total revenue"}],
}


def layout(conn):
    text = conn.execute("SELECT canonical_text FROM document WHERE id = ?", (DOC,)).fetchone()[0]
    segments = [Segment(r["start"], r["end"], r["kind"]) for r in conn.execute(
        "SELECT start, end, kind FROM segment WHERE document_id = ? ORDER BY idx", (DOC,))]
    return text, segments, select(text, segments)


def write_replies(conn, directory, candidates_for: dict[str, list], broken: str | None = None) -> ReplyStore:
    """A stored reply for every selected segment: empty unless the segment contains one of the given keys."""
    text, segments, chosen = layout(conn)
    store = ReplyStore(directory)
    used = set()
    for selection in chosen:
        body = text[segments[selection.index].start:segments[selection.index].end]
        request = request_text(text, segments, selection)
        needle = next((n for n in candidates_for if n in body and n not in used), None)
        reply = {"candidates": candidates_for[needle]} if needle else {"candidates": []}
        if needle:
            used.add(needle)
        if broken and broken in body:
            reply = {"oops": True}
        store.write({"key": reply_key(VERSION, MODEL, request), "instruction_version": VERSION, "model": MODEL,
                     "served_model": MODEL, "request_text": request, "reply": reply, "input_tokens": 0, "output_tokens": 0})
    assert used == set(candidates_for), "a test candidate found no selected segment"
    return store


def run(conn, store, **options):
    return interpret(conn, DOC, store, instruction_version=VERSION, model=MODEL, **options)


def outcomes(conn):
    return [(r["outcome"], r["check"], r["field"]) for r in conn.execute(
        "SELECT outcome, \"check\", field FROM candidate_outcome ORDER BY segment_index, seq")]


# Scenario 1: candidates are proposed, each with the exact span it rests on.
def test_passed_candidates_become_stored_claims_traceable_to_their_text(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [PROSE, CHANGE]})
    result = run(filings, store)
    assert (result["candidates"], result["passed"], result["flagged"], result["rejected"]) == (2, 2, 0, 0)
    assert result["calls_made"] == 0 and result["replies_reused"] == result["segments_selected"] > 20
    claims = [get_claim(filings, r["claim_id"]) for r in filings.execute("SELECT claim_id FROM candidate_outcome ORDER BY seq")]
    text = layout(filings)[0]
    for claim, candidate in zip(claims, (PROSE, CHANGE)):
        assert text[claim["span_start"]:claim["span_end"]] == candidate["quote"] == claim["quote"]
        assert claim["company_cik"] == "0001318568" and claim["said_on"] == "2024-05-08"
    assert claims[0]["status"] == "formal" and claims[1]["status"] == "formal-with-assumptions"


# Scenario 2: what comes from the table heading is a named assumption with origin "model".
def test_table_row_candidate_carries_its_assumptions_with_origin_model(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues\t189,346": [ROW]})
    assert run(filings, store)["passed"] == 1
    claim = get_claim(filings, filings.execute("SELECT claim_id FROM candidate_outcome").fetchone()[0])
    assert claim["status"] == "formal-with-assumptions"
    assert [(a["field"], a["origin"]) for a in claim["assumptions"]] == [("period_start", "model"), ("stated_scale", "model")]


def test_table_row_candidate_without_its_assumptions_is_flagged_by_the_gate(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues\t189,346": [ROW | {"assumptions": []}]})
    result = run(filings, store)
    assert (result["passed"], result["flagged"]) == (0, 1)
    claim = get_claim(filings, filings.execute("SELECT claim_id FROM candidate_outcome").fetchone()[0])
    assert claim["status"] == "not-formalizable"
    assert {f["reason"] for f in claim["flags"]} == {"missing_background", "underspecified_time"}


# Scenario 3: what cannot be expressed is proposed with a flag, not dropped and not guessed.
def test_figure_for_a_component_of_a_metric_is_stored_with_its_flag(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Games total revenues\t97,122": [COMPONENT]})
    result = run(filings, store)
    assert (result["candidates"], result["flagged"]) == (1, 1)
    claim = get_claim(filings, filings.execute("SELECT claim_id FROM candidate_outcome").fetchone()[0])
    assert claim["status"] == "not-formalizable" and claim["metric"] is None and claim["value_low"] == "97122000"
    assert claim["flags"][0]["reason"] == "unmapped_metric" and claim["flags"][0]["resolved"] is False


@pytest.mark.parametrize("candidate, check, field", [
    (PROSE | {"quote": "to approximately $189.4 million for the three months ended March 31, 2024"}, "quote", "quote"),
    (PROSE | {"quote_occurrence": 2}, "quote", "quote"),
    (PROSE | {"stated_value": "198.3", "value_low": "198300000", "value_high": "198300000"}, "value", "stated_value"),
    (PROSE | {"stated_scale": "thousands", "value_low": "189300", "value_high": "189300"}, "scale", "stated_scale"),
    (PROSE | {"metric": "ebitda"}, "schema", "metric"),
    (PROSE | {"period_end": "31 March 2024"}, "schema", "period_end"),
    (PROSE | {"basis": None}, "schema", "basis"),
    (PROSE | {"flags": [{"reason": "gut feeling"}]}, "schema", "flags[0].reason"),
])
def test_bad_candidates_are_rejected_with_the_check_that_caught_them(filings, tmp_path, candidate, check, field):
    store = write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [candidate]})
    result = run(filings, store)
    assert (result["candidates"], result["rejected"]) == (1, 1)
    assert outcomes(filings) == [("rejected", check, field)]
    assert filings.execute("SELECT count(*) FROM claim").fetchone()[0] == 0


def test_same_candidate_twice_in_a_reply_is_stored_once(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [PROSE, PROSE, PROSE | {"basis": "adjusted"}]})
    result = run(filings, store)
    assert (result["passed"], result["rejected"]) == (1, 2)
    assert [o[:2] for o in outcomes(filings)] == [("passed", None), ("rejected", "duplicate"), ("rejected", "duplicate")]
    assert filings.execute("SELECT count(*) FROM claim").fetchone()[0] == 1


def test_candidate_about_another_company_is_flagged(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [PROSE | {"company_cik": "0000000001"}]})
    assert run(filings, store)["flagged"] == 1
    claim = get_claim(filings, filings.execute("SELECT claim_id FROM candidate_outcome").fetchone()[0])
    assert claim["company_cik"] == "0000000001" and "implicit_scope" in {f["reason"] for f in claim["flags"]}


# Scenario 4: a second run reuses everything and changes nothing.
def test_second_run_makes_no_call_and_changes_nothing(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [PROSE, CHANGE],
                                              "Total revenues\t189,346": [ROW]})
    def no_calls(text):
        raise AssertionError("the model must not be called")
    first = run(filings, store, client=no_calls)
    before = db.export(filings)
    second = run(filings, store, client=no_calls)
    assert db.export(filings) == before
    assert second == first | {"calls_made": 0, "replies_reused": first["segments_selected"]}
    assert first["candidates"] == first["passed"] + first["flagged"] + first["rejected"] == 3


# Scenario 5: an unreadable reply stores nothing, is reported, and does not stop the rest.
def test_unreadable_reply_is_counted_and_the_rest_is_processed(filings, tmp_path):
    store = write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [PROSE]},
                          broken="Total revenues\t189,346")
    result = run(filings, store)
    assert result["replies_failed"] >= 1 and result["passed"] == 1


def test_missing_reply_without_permission_to_call_is_an_error_and_stores_nothing(filings, tmp_path):
    with pytest.raises(AxiomateError) as raised:
        run(filings, ReplyStore(tmp_path / "empty"))
    assert raised.value.code == "reply_missing"
    assert filings.execute("SELECT count(*) FROM interpretation_run").fetchone()[0] == 0


def test_missing_replies_are_requested_from_the_client_and_stored(filings, tmp_path):
    asked = []

    def client(text):
        asked.append(text)
        return {"reply": {"candidates": []}, "served_model": "test-model-2026", "input_tokens": 11, "output_tokens": 3}

    store = ReplyStore(tmp_path / "new")
    result = run(filings, store, client=client)
    assert result["calls_made"] == len(asked) == result["segments_selected"] and result["replies_reused"] == 0
    record = store.read(reply_key(VERSION, MODEL, asked[0]))
    assert record["request_text"] == asked[0] and record["served_model"] == "test-model-2026" and record["input_tokens"] == 11


def test_call_limit_stops_before_exceeding_and_keeps_what_was_paid_for(filings, tmp_path):
    store = ReplyStore(tmp_path / "limited")
    client = lambda text: {"reply": {"candidates": []}, "served_model": MODEL, "input_tokens": 1, "output_tokens": 1}
    with pytest.raises(AxiomateError) as raised:
        run(filings, store, client=client, max_calls=3)
    assert raised.value.code == "call_limit_reached"
    assert len(list((tmp_path / "limited").glob("*.json"))) == 3
    assert filings.execute("SELECT count(*) FROM interpretation_run").fetchone()[0] == 0


def test_failing_client_counts_as_a_failed_reply(filings, tmp_path):
    def client(text):
        raise AxiomateError("reply_failed", "the model declined", None)
    result = run(filings, ReplyStore(tmp_path / "down"), client=client)
    assert result["replies_failed"] == result["segments_selected"] and result["candidates"] == 0


def test_an_unavailable_service_stops_the_run_and_records_nothing(filings, tmp_path):
    def client(text):
        raise AxiomateError("model_unavailable", "no service", None)
    with pytest.raises(AxiomateError) as raised:
        run(filings, ReplyStore(tmp_path / "down"), client=client)
    assert raised.value.code == "model_unavailable"
    assert filings.execute("SELECT count(*) FROM interpretation_run").fetchone()[0] == 0


def test_unknown_document_is_not_found(filings, tmp_path):
    with pytest.raises(AxiomateError) as raised:
        interpret(filings, "0" * 64, ReplyStore(tmp_path), instruction_version=VERSION, model=MODEL)
    assert raised.value.code == "not_found"


# Schema version 2 (task T017).
def test_run_and_outcome_records_cannot_be_altered(filings, tmp_path):
    run(filings, write_replies(filings, tmp_path, {"Total revenues decreased by approximately $11.1 million": [PROSE]}))
    for table in ("interpretation_run", "candidate_outcome"):
        for statement in (f"UPDATE {table} SET rowid = rowid", f"DELETE FROM {table}"):
            with pytest.raises(sqlite3.DatabaseError, match="immutable"):
                filings.execute(statement)


def test_store_of_schema_version_1_is_upgraded_in_place(tmp_path):
    from importlib import resources
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(resources.files("axiomate.store").joinpath("schema.sql").read_text(encoding="utf-8") + "PRAGMA user_version = 1;")
    old.close()
    conn = db.connect(path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM candidate_outcome").fetchone()[0] == 0
    conn.close()


# Command line (contract: contracts/cli.md).
def test_command_line_interpret_from_stored_replies(filings, tmp_path, capsys, monkeypatch):
    from axiomate.interpret import run as run_module
    monkeypatch.setattr(run_module, "MODEL", MODEL)
    monkeypatch.setattr(run_module, "INSTRUCTION_VERSION", VERSION)
    write_replies(filings, tmp_path / "replies", {"Total revenues decreased by approximately $11.1 million": [PROSE]})
    store_path = filings.execute("PRAGMA database_list").fetchone()[2]
    assert main(["--db", store_path, "interpret", DOC, "--replies", str(tmp_path / "none")]) != 0
    assert json.loads(capsys.readouterr().out)["error"] == "reply_missing"
    assert main(["--db", store_path, "interpret", DOC, "--replies", str(tmp_path / "replies")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["passed"] == 1 and out["calls_made"] == 0 and len(out["run_id"]) == 64


# Evaluation against tagged figures (task T027).
def test_report_states_precision_coverage_and_pass_rate_with_their_thresholds(filings, tmp_path):
    from axiomate.evaluate.report import build
    wrong_period = ROW | {"quote": "200,472", "value_low": "200472000", "value_high": "200472000", "stated_value": "200472"}
    run(filings, write_replies(filings, tmp_path / "replies", {"Total revenues\t189,346": [ROW, wrong_period, COMPONENT]}))
    splits = tmp_path / "eval" / "splits.json"
    splits.parent.mkdir()
    entry = {"file": "everi_2024q1_10q.html", "filings": str(support.DOCS), "facts": str(support.FIXTURES / "facts")}
    splits.write_text(json.dumps({"development": [entry], "held_out": []}), encoding="utf-8")
    report = build(filings, "development", splits_path=splits, instruction_version=VERSION, model=MODEL)
    assert report["precision"] == {"numerator": 1, "denominator": 2, "value": "0.5000", "threshold": "0.98", "met": False}
    assert report["coverage"]["numerator"] == 1 and report["coverage"]["denominator"] == report["tagged_figures"] > 5
    assert report["pass_rate"]["numerator"] == 2 and report["pass_rate"]["denominator"] == 3
    assert [d["fields"] for d in report["disagreements"]] == [["period"]] and report["thresholds_met"] is False
    with pytest.raises(AxiomateError) as raised:
        build(filings, "development", splits_path=splits, instruction_version="other", model=MODEL)
    assert raised.value.code == "not_found"
