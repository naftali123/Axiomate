"""The validation gate: Story 1 of spec 002 (tasks T007, T010)."""
import copy
import json

import pytest

import support
from axiomate.cli import main
from axiomate.errors import AxiomateError
from axiomate.gate.check import check

GATE = support.FIXTURES / "gate"
FROM_FACTS = json.loads((GATE / "from_facts.json").read_text(encoding="utf-8"))["claims"]
PROBES = json.loads((GATE / "probes.json").read_text(encoding="utf-8"))
CORRUPTED = json.loads((GATE / "corrupted.json").read_text(encoding="utf-8"))
HAND = [support.load(p) for p in support.GOOD]
KINDS = ("digit", "scale", "sign", "period", "metric", "hedge", "assumption")


def base_claim(conn, base_set: str, name: str) -> dict:
    if base_set == "hand":
        claim = support.submission(conn, support.good(name))
        del claim["status"]
        return claim
    source = FROM_FACTS if base_set == "facts" else PROBES
    return copy.deepcopy(next(item["claim"] for item in source if item["name"] == name))


def corrupt(claim: dict, operations: list[dict]) -> dict:
    for op in operations:
        if op["op"] == "set":
            claim[op["field"]] = op["value"]
        elif op["op"] == "remove_assumption":
            claim["assumptions"] = [a for a in claim["assumptions"] if a["field"] != op["field"]]
        else:
            raise ValueError(op["op"])
    return claim


def hand(conn, name: str, **changes) -> dict:
    return dict(base_claim(conn, "hand", name), **changes)


# Scenario 1: a claim that agrees with its quote passes.
def test_claim_that_agrees_with_its_quote_passes(filings):
    result = check(filings, hand(filings, "everi_2024q1_net_income"))
    assert (result.outcome, result.check, result.flags) == ("passed", None, [])


# Scenario 2: a value that differs from the quote is rejected, naming the field.
@pytest.mark.parametrize("changes, checked, field", [
    ({"stated_value": "5.6", "value_low": "5600000", "value_high": "5600000"}, "value", "stated_value"),
    ({"value_low": "4600", "value_high": "4600"}, "value", "value_low"),
    ({"stated_scale": "thousands", "value_low": "4600", "value_high": "4600"}, "scale", "stated_scale"),
    ({"value_low": "-4600000", "value_high": "-4600000"}, "sign", "value_low"),
])
def test_value_scale_and_sign_that_differ_from_the_quote(filings, changes, checked, field):
    result = check(filings, hand(filings, "everi_2024q1_net_income", **changes))
    assert result.outcome != "passed" and (result.check, result.field) == (checked, field)


def test_decrease_stated_as_an_increase_is_rejected(filings):
    result = check(filings, hand(filings, "cpa18_2021h1_ocf_change", value_low="1800000", value_high="1800000"))
    assert (result.outcome, result.check) == ("rejected", "sign")


# Scenario 3: period or metric with no evidence and no assumption does not pass as formal.
def test_period_that_contradicts_the_quote_is_rejected(filings):
    result = check(filings, hand(filings, "everi_2024q1_net_income", period_start="2023-01-01",
                                 period_end="2023-03-31", fiscal_year=2023))
    assert (result.outcome, result.check, result.field) == ("rejected", "period", "period_end")


def test_period_without_evidence_or_assumption_is_flagged(filings):
    claim = hand(filings, "everi_2023q1_net_income", assumptions=[])
    result = check(filings, claim)
    assert (result.outcome, result.check) == ("flagged", "period")
    assert [(f["reason"], f["field"], f["resolved"]) for f in result.flags] == [("underspecified_time", "period_start", False)]


def test_metric_named_nowhere_is_flagged_and_metric_contradicted_is_rejected(filings):
    claim = copy.deepcopy(PROBES[0]["claim"])
    claim["assumptions"] = [a for a in claim["assumptions"] if a["field"] != "metric"]
    unnamed = check(filings, claim)
    assert (unnamed.outcome, unnamed.check, unnamed.flags[0]["reason"]) == ("flagged", "metric", "unmapped_metric")
    # Named earlier in the same sentence: the segment is evidence, no assumption needed.
    same_sentence = hand(filings, "orrstown_1995_9m_net_income")
    same_sentence["assumptions"] = [a for a in same_sentence["assumptions"] if a["field"] != "metric"]
    assert check(filings, same_sentence).outcome == "passed"
    swapped = check(filings, hand(filings, "southalabama_2000_q1_net_income", metric="revenue"))
    assert (swapped.outcome, swapped.check, swapped.field) == ("rejected", "metric", "metric")


def test_component_of_a_metric_claimed_as_the_metric_is_flagged(filings):
    claim = hand(filings, "geospace_fy2021q3_rental_revenue", metric="revenue", flags=[])
    result = check(filings, claim)
    assert (result.outcome, result.check) == ("flagged", "metric")
    assert result.flags[0]["reason"] == "unmapped_metric"


# Scenario 4: a hedge the claim does not reflect is flagged.
def test_approximation_not_reflected_in_the_claim_is_flagged(filings):
    result = check(filings, hand(filings, "everi_2024q1_net_income", value_kind="exact"))
    assert (result.outcome, result.check, result.field) == ("flagged", "hedge", "value_kind")
    assert result.flags[0]["reason"] == "hedged_or_conditional"


# Scenario 5: every outcome carries its reason.
def test_already_flagged_claim_is_reported_as_flagged(filings):
    result = check(filings, hand(filings, "everi_2024q1_revenue_reason"))
    assert result.outcome == "flagged"


def test_quote_that_is_not_in_the_text_is_rejected_by_the_quote_check(filings):
    result = check(filings, hand(filings, "everi_2024q1_net_income", quote="we had net income of approximately $4.7 million"))
    assert (result.outcome, result.check, result.field) == ("rejected", "quote", "quote")


def test_malformed_claim_and_unknown_document_are_errors_not_outcomes(filings):
    claim = hand(filings, "everi_2024q1_net_income")
    with pytest.raises(AxiomateError) as raised:
        check(filings, {k: v for k, v in claim.items() if k != "metric"})
    assert raised.value.code == "schema_invalid"
    with pytest.raises(AxiomateError) as raised:
        check(filings, dict(claim, document_id="0" * 64))
    assert raised.value.code == "document_not_found"


def test_gate_is_deterministic_and_stores_nothing(filings):
    claim = hand(filings, "everi_2024q1_revenue_change")
    assert check(filings, claim) == check(filings, claim)
    assert filings.execute("SELECT count(*) FROM claim").fetchone()[0] == 0


# Verification, SC-004: correct claims pass, at least 98%.
def test_correct_claims_pass_at_least_98_percent(filings):
    results = {}
    for fixture in HAND:
        if fixture["expected_status"] != "not-formalizable":
            results[fixture["name"]] = check(filings, base_claim(filings, "hand", fixture["name"]))
    for item in FROM_FACTS:
        results[item["name"]] = check(filings, copy.deepcopy(item["claim"]))
    failed = {name: (r.outcome, r.check, r.field) for name, r in results.items() if r.outcome != "passed"}
    assert len(results) >= 100
    assert 1 - len(failed) / len(results) >= 0.98, f"{len(results) - len(failed)}/{len(results)} passed\n" + "\n".join(
        f"{name}: {why}" for name, why in sorted(failed.items()))


def test_probes_pass_before_they_are_corrupted(filings):
    outcomes = [check(filings, copy.deepcopy(p["claim"])).outcome for p in PROBES]
    assert outcomes == ["passed"] * len(PROBES)


# Verification, SC-003: every corrupted claim is caught, with the expected check.
@pytest.mark.parametrize("case", CORRUPTED, ids=[c["name"] for c in CORRUPTED])
def test_every_corrupted_claim_is_caught_by_the_expected_check(filings, case):
    claim = corrupt(base_claim(filings, case["base_set"], case["base"]), case["operations"])
    result = check(filings, claim)
    assert result.outcome != "passed", "a corrupted claim passed the gate"
    assert result.check == case["expected_check"]
    if case["expected_outcome"]:
        assert result.outcome == case["expected_outcome"]


def test_at_least_ten_corrupted_claims_of_each_kind():
    counts = {kind: sum(c["kind"] == kind for c in CORRUPTED) for kind in KINDS}
    assert min(counts.values()) >= 10 and set(c["kind"] for c in CORRUPTED) == set(KINDS)


# Command line (contract: contracts/cli.md).
def test_command_line_claim_check(filings, tmp_path, capsys):
    store_path = filings.execute("PRAGMA database_list").fetchone()[2]
    path = tmp_path / "claim.json"
    claim = hand(filings, "everi_2024q1_net_income")
    path.write_text(json.dumps(claim), encoding="utf-8")
    assert main(["--db", store_path, "claim", "check", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"outcome": "passed", "check": None, "field": None, "message": None, "flags": []}

    path.write_text(json.dumps(dict(claim, value_kind="exact")), encoding="utf-8")
    assert main(["--db", store_path, "claim", "check", str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["outcome"] == "flagged" and out["check"] == "hedge" and out["flags"][0]["reason"] == "hedged_or_conditional"

    path.write_text(json.dumps({k: v for k, v in claim.items() if k != "metric"}), encoding="utf-8")
    assert main(["--db", store_path, "claim", "check", str(path)]) != 0
    assert json.loads(capsys.readouterr().out)["error"] == "schema_invalid"
    assert filings.execute("SELECT count(*) FROM claim").fetchone()[0] == 0
