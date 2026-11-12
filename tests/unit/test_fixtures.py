"""Integrity of the verification data collected in the setup phase."""
import hashlib
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
DOCS = FIXTURES / "documents"
METRICS = {"revenue", "net_income", "earnings_per_share", "operating_cash_flow"}
STATUSES = {"formal", "formal-with-assumptions", "not-formalizable"}


def manifest():
    return json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))


def good_claims():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FIXTURES / "claims" / "good").glob("*.json"))]


def test_ten_filings_from_five_companies_match_their_hashes():
    entries = manifest()
    assert len(entries) == 10
    assert len({entry["cik"] for entry in entries}) == 5
    assert sum(entry["format"] == "text" for entry in entries) >= 3
    assert sum(entry["format"] == "html" for entry in entries) >= 5
    for entry in entries:
        data = (DOCS / entry["file"]).read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["file"]


def test_every_html_filing_has_embedded_figures():
    for entry in manifest():
        if entry["format"] != "html":
            continue
        facts = json.loads((FIXTURES / "facts" / (Path(entry["file"]).stem + ".json")).read_text())
        assert facts["skipped"] == []
        assert {fact["metric"] for fact in facts["facts"]} >= {"revenue", "net_income", "operating_cash_flow"}


def test_good_claims_are_well_formed_and_quote_plain_text_filings_verbatim():
    claims = good_claims()
    assert len(claims) >= 20
    files = {entry["file"] for entry in manifest()}
    for item in claims:
        assert item["document"] in files
        assert item["expected_status"] in STATUSES
        metric = item["claim"]["metric"]
        assert metric in METRICS or (metric is None and item["flags"])
        if item["document"].endswith(".txt"):
            text = (DOCS / item["document"]).read_text(encoding="utf-8")
            assert item["quote"] in text, item["name"]


def test_each_rejection_code_has_at_least_five_corrupted_claims():
    names = {item["name"] for item in good_claims()}
    counts = {}
    for path in (FIXTURES / "claims" / "bad").glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        assert item["base"] in names
        counts[item["expected_error"]] = counts.get(item["expected_error"], 0) + 1
    assert len(counts) == 8
    assert min(counts.values()) >= 5


def test_boundary_labels_cover_every_filing_with_at_least_200_segments():
    total = 0
    for entry in manifest():
        labels = FIXTURES / "boundaries" / (Path(entry["file"]).stem + ".txt")
        total += sum(1 for line in labels.read_text(encoding="utf-8").splitlines() if line.strip())
    assert total >= 200


def test_every_boundary_label_is_confirmed_by_the_cross_check_or_by_a_person():
    """specs/verification.md: a label counts once an independent tool agrees, or a person decides."""
    boundaries = FIXTURES / "boundaries"
    check = json.loads((boundaries / "cross_check.json").read_text(encoding="utf-8"))
    files = sorted(boundaries.glob("*.txt"))
    assert [entry["file"] for entry in check["files"]] == [p.name for p in files]
    for entry, path in zip(check["files"], files):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"{path.name} changed after the cross-check"
    assert check["labels"] >= 200
    disputed_labels = sum(len(d["labelled"]) for d in check["disputed"])
    assert check["tool_agrees"] + disputed_labels == check["labels"]
    for dispute in check["disputed"]:
        assert dispute["decision"] and dispute["decision"]["label_stands"] is True, dispute["file"]
