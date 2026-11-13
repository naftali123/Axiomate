"""The development / held-out split of spec 002 (task T013)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS = json.loads((ROOT / "eval" / "splits.json").read_text(encoding="utf-8"))
HELD_OUT = json.loads((ROOT / "eval" / "filings" / "manifest.json").read_text(encoding="utf-8"))
DEVELOPMENT = json.loads((ROOT / "tests" / "fixtures" / "documents" / "manifest.json").read_text(encoding="utf-8"))


def test_no_filing_and_no_company_is_on_both_sides():
    development = {item["file"] for item in SPLITS["development"]}
    held_out = {item["file"] for item in SPLITS["held_out"]}
    assert development and held_out and not development & held_out
    assert held_out == {entry["file"] for entry in HELD_OUT}
    assert not {entry["cik"] for entry in HELD_OUT} & {entry["cik"] for entry in DEVELOPMENT}


def test_held_out_set_is_at_least_eight_filings_from_four_companies_with_an_annual_report():
    assert len(HELD_OUT) >= 8 and len({entry["cik"] for entry in HELD_OUT}) >= 4
    assert any(entry["form"] == "10-K" for entry in HELD_OUT)


def test_held_out_filings_are_unchanged_and_have_tagged_figures_for_the_four_metrics():
    metrics = set()
    for entry in HELD_OUT:
        data = (ROOT / "eval" / "filings" / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["file"]
        facts = json.loads((ROOT / "eval" / "facts" / (Path(entry["file"]).stem + ".json")).read_text(encoding="utf-8"))
        assert facts["facts"] and facts["skipped"] == []
        metrics |= {fact["metric"] for fact in facts["facts"]}
    assert metrics == {"revenue", "net_income", "earnings_per_share", "operating_cash_flow"}


def test_held_out_filings_are_sealed_from_tests_and_source():
    """No test and no product code, except the evaluation code, may refer to the held-out data."""
    names = [Path(entry["file"]).stem for entry in HELD_OUT] + ["eval/filings", "eval/facts"]
    allowed = {Path(__file__).resolve(), (ROOT / "src" / "axiomate" / "evaluate").resolve()}
    offenders = []
    for folder in ("src", "tests"):
        for path in (ROOT / folder).rglob("*.py"):
            if path.resolve() in allowed or (ROOT / "src" / "axiomate" / "evaluate").resolve() in path.resolve().parents:
                continue
            text = path.read_text(encoding="utf-8")
            offenders += [f"{path.relative_to(ROOT)}: {name}" for name in names if name in text]
    assert offenders == []
