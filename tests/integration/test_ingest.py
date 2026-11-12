"""Story 1 acceptance scenarios and the stage-1 verification checks (task T014)."""
import json
import sqlite3
from pathlib import Path

import pytest

from axiomate.cli import main
from axiomate.documents.ingest import get_document, get_original, get_segment, ingest
from axiomate.errors import AxiomateError
from axiomate.store import db

DOCS = Path(__file__).resolve().parent.parent / "fixtures" / "documents"
MANIFEST = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))


def provenance(entry: dict) -> dict:
    filed = entry["filed_on"]
    return {
        "publisher_cik": entry["cik"],
        "document_type": "quarterly_report",
        "published_on": f"{filed[:4]}-{filed[4:6]}-{filed[6:]}",
        "format": entry["format"],
    }


@pytest.fixture
def store(tmp_path):
    conn = db.connect(tmp_path / "store.db")
    yield conn
    conn.close()


@pytest.fixture
def text_entry():
    return next(e for e in MANIFEST if e["format"] == "text")


@pytest.fixture
def html_entry():
    return next(e for e in MANIFEST if e["file"] == "everi_2024q1_10q.html")


# Scenario 1: stored with a content hash; every sentence has a stable address.
def test_ingested_document_has_content_hash_and_addressable_segments(store, html_entry):
    data = (DOCS / html_entry["file"]).read_bytes()
    result = ingest(store, data, fiscal_year=2024, fiscal_period="Q1", **provenance(html_entry))
    assert result.created is True
    assert result.document_id == html_entry["sha256"]
    document = get_document(store, result.document_id)
    assert document["publisher_cik"] == html_entry["cik"]
    assert document["published_on"] == provenance(html_entry)["published_on"]
    assert document["fiscal_year"] == 2024 and document["fiscal_period"] == "Q1"
    assert document["segments"] == result.segments > 100
    assert document["extractor_version"] and document["segmenter_version"]
    for index in (0, 7, result.segments - 1):
        part = get_segment(store, result.document_id, index)
        assert part["index"] == index
        assert part["text"] == document["canonical_text"][part["start"]:part["end"]]
        assert part["kind"] in ("sentence", "table_row", "heading")


@pytest.mark.parametrize("entry", MANIFEST, ids=[e["file"] for e in MANIFEST])
def test_round_trip_and_no_duplicates_for_every_filing(store, entry):
    """Verification: stored text unchanged (100%); three ingestions give one record."""
    data = (DOCS / entry["file"]).read_bytes()
    results = [ingest(store, data, **provenance(entry)) for _ in range(3)]
    assert [r.created for r in results] == [True, False, False]
    assert len({r.document_id for r in results}) == 1 and len({r.segments for r in results}) == 1
    assert get_original(store, results[0].document_id) == data
    assert store.execute("SELECT count(*) FROM document").fetchone()[0] == 1
    assert store.execute("SELECT count(*) FROM segment").fetchone()[0] == results[0].segments


# Scenario 3: missing publisher or publication date is rejected, naming the field.
@pytest.mark.parametrize("field", ["publisher_cik", "published_on"])
@pytest.mark.parametrize("empty", [None, "", "  "])
def test_missing_provenance_is_rejected_naming_the_field(store, text_entry, field, empty):
    args = provenance(text_entry) | {field: empty}
    with pytest.raises(AxiomateError) as raised:
        ingest(store, (DOCS / text_entry["file"]).read_bytes(), **args)
    assert raised.value.code == "missing_provenance" and raised.value.field == field
    assert store.execute("SELECT count(*) FROM document").fetchone()[0] == 0


@pytest.mark.parametrize("change, code, field", [
    ({"published_on": "12/11/2026"}, "invalid_provenance", "published_on"),
    ({"published_on": "2026-02-30"}, "invalid_provenance", "published_on"),
    ({"publisher_cik": "ACME"}, "invalid_provenance", "publisher_cik"),
    ({"document_type": "tweet"}, "invalid_provenance", "document_type"),
    ({"fiscal_period": "Q5"}, "invalid_provenance", "fiscal_period"),
    ({"fiscal_year": "next"}, "invalid_provenance", "fiscal_year"),
    ({"format": "pdf"}, "unsupported_format", "format"),
    ({"language": "he"}, "unsupported_language", "language"),
])
def test_bad_provenance_is_rejected_with_its_code(store, text_entry, change, code, field):
    with pytest.raises(AxiomateError) as raised:
        ingest(store, (DOCS / text_entry["file"]).read_bytes(), **(provenance(text_entry) | change))
    assert (raised.value.code, raised.value.field) == (code, field)


def test_bytes_that_are_not_text_are_rejected(store, text_entry):
    with pytest.raises(AxiomateError) as raised:
        ingest(store, b"\xff\xfe\x00binary", **provenance(text_entry))
    assert raised.value.code == "unsupported_format"


def test_document_without_any_text_is_rejected(store, text_entry):
    with pytest.raises(AxiomateError) as raised:
        ingest(store, b" \n\n", **provenance(text_entry))
    assert raised.value.code == "empty_document"


def test_same_bytes_with_different_provenance_is_a_conflict(store, text_entry):
    data = (DOCS / text_entry["file"]).read_bytes()
    ingest(store, data, **provenance(text_entry))
    with pytest.raises(AxiomateError) as raised:
        ingest(store, data, **(provenance(text_entry) | {"published_on": "2001-01-01"}))
    assert raised.value.code == "provenance_conflict" and raised.value.field == "published_on"
    assert store.execute("SELECT count(*) FROM document").fetchone()[0] == 1


def test_short_cik_is_stored_in_its_ten_digit_form(store, text_entry):
    data = (DOCS / text_entry["file"]).read_bytes()
    short = text_entry["cik"].lstrip("0")
    first = ingest(store, data, **(provenance(text_entry) | {"publisher_cik": short}))
    again = ingest(store, data, **provenance(text_entry))
    assert again.created is False and again.document_id == first.document_id
    assert get_document(store, first.document_id)["publisher_cik"] == text_entry["cik"]


# Scenario 4: stored text cannot be altered.
def test_stored_text_cannot_be_altered(store, text_entry):
    result = ingest(store, (DOCS / text_entry["file"]).read_bytes(), **provenance(text_entry))
    for statement in ("UPDATE document SET canonical_text = 'x'", "DELETE FROM document",
                      "UPDATE segment SET start = 0", "DELETE FROM segment"):
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            store.execute(statement)
    assert get_document(store, result.document_id)["canonical_text"]


# Scenario 5: HTML – visible text stored and addressable, original retrievable.
def test_html_visible_text_is_stored_and_original_is_retrievable(store, html_entry):
    data = (DOCS / html_entry["file"]).read_bytes()
    result = ingest(store, data, **provenance(html_entry))
    document = get_document(store, result.document_id)
    assert document["format"] == "html"
    assert "<div" not in document["canonical_text"] and "Total revenues" in document["canonical_text"]
    assert get_original(store, result.document_id) == data


def test_unknown_document_and_segment_are_not_found(store, text_entry):
    with pytest.raises(AxiomateError) as raised:
        get_document(store, "0" * 64)
    assert raised.value.code == "not_found"
    result = ingest(store, (DOCS / text_entry["file"]).read_bytes(), **provenance(text_entry))
    with pytest.raises(AxiomateError) as raised:
        get_segment(store, result.document_id, result.segments)
    assert raised.value.code == "not_found"


def test_a_failed_ingestion_leaves_nothing_behind(store, text_entry, monkeypatch):
    from axiomate.documents import ingest as module

    def broken(text, fmt):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "segment", broken)
    with pytest.raises(RuntimeError):
        ingest(store, (DOCS / text_entry["file"]).read_bytes(), **provenance(text_entry))
    assert store.execute("SELECT count(*) FROM document").fetchone()[0] == 0


# Command line (contract: contracts/cli.md).
def run(capsys, *args):
    code = main(list(args))
    return code, json.loads(capsys.readouterr().out)


def test_command_line_ingest_and_show(tmp_path, capsys, html_entry):
    store_path = str(tmp_path / "cli.db")
    args = ["--db", store_path, "ingest", str(DOCS / html_entry["file"]), "--publisher-cik", html_entry["cik"],
            "--type", "quarterly_report", "--published-on", "2024-05-08", "--fiscal-year", "2024",
            "--fiscal-period", "Q1", "--format", "html"]
    code, first = run(capsys, *args)
    assert code == 0 and first["created"] is True and first["document_id"] == html_entry["sha256"]
    code, second = run(capsys, *args)
    assert code == 0 and second == first | {"created": False}

    code, shown = run(capsys, "--db", store_path, "document", "show", first["document_id"])
    assert code == 0 and shown["segments"] == first["segments"] and shown["fiscal_period"] == "Q1"
    assert "original" not in shown and shown["canonical_text"]

    code, part = run(capsys, "--db", store_path, "document", "show", first["document_id"], "--segment", "3")
    assert code == 0 and part["index"] == 3
    assert part["text"] == shown["canonical_text"][part["start"]:part["end"]]


def test_command_line_rejections_print_the_error_and_exit_non_zero(tmp_path, capsys, text_entry):
    store_path = str(tmp_path / "cli.db")
    code, out = run(capsys, "--db", store_path, "ingest", str(DOCS / text_entry["file"]),
                    "--type", "quarterly_report", "--published-on", "2000-05-12", "--format", "text")
    assert code != 0 and out["error"] == "missing_provenance" and out["field"] == "publisher_cik"
    assert set(out) == {"error", "field", "message"}
    code, out = run(capsys, "--db", store_path, "document", "show", "0" * 64)
    assert code != 0 and out["error"] == "not_found"
