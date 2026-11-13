"""Foundation of the store: schema, immutability and the canonical export."""
import json
import sqlite3

import pytest

from axiomate.store import db

DOC_ID = "a" * 64
TABLES = ["document", "segment", "claim", "flag", "assumption"]


def fill(conn):
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO document (id, publisher_cik, document_type, published_on, fiscal_year,"
            " fiscal_period, format, language, original, canonical_text, extractor_version,"
            " segmenter_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (DOC_ID, "0000000001", "quarterly_report", "2025-10-28", 2025, "Q3", "text", "en",
             b"Revenue was $4.2 billion.", "Revenue was $4.2 billion.", "1", "1"),
        )
        conn.execute(
            "INSERT INTO segment (document_id, idx, start, end, kind) VALUES (?,?,?,?,?)",
            (DOC_ID, 0, 0, 25, "sentence"),
        )
        conn.execute(
            "INSERT INTO claim (id, version, schema_version, company_cik, metric, value_kind,"
            " value_low, value_high, stated_value, stated_scale, unit, currency, period_kind,"
            " fiscal_year, fiscal_period, period_start, period_end, basis, nature, comparison,"
            " polarity, document_id, segment_index, span_start, span_end, quote, said_on, status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c" * 64, 1, "1", "0000000001", "revenue", "exact", "4200000000", "4200000000",
             "4.2", "billions", "currency", "USD", "duration", 2025, "Q3", "2025-07-01",
             "2025-09-30", "reported", "actual", "absolute", "affirmed", DOC_ID, 0, 0, 24,
             "Revenue was $4.2 billion", "2025-10-28", "formal-with-assumptions"),
        )
        conn.execute(
            "INSERT INTO flag (claim_id, claim_version, seq, reason, field, resolved, note)"
            " VALUES (?,?,?,?,?,?,?)",
            ("c" * 64, 1, 0, "implicit_scope", "metric", 1, None),
        )
        conn.execute(
            "INSERT INTO assumption (claim_id, claim_version, seq, statement, field, origin)"
            " VALUES (?,?,?,?,?,?)",
            ("c" * 64, 1, 0, "Revenue means total revenue", "metric", "human"),
        )


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "store.sqlite")
    fill(connection)
    yield connection
    connection.close()


def test_a_new_store_has_the_five_tables_and_exports_empty(tmp_path):
    connection = db.connect(tmp_path / "empty.sqlite")
    exported = json.loads(db.export(connection))
    assert set(exported) == {"schema_version", *db.TABLES}
    assert set(db.TABLES) >= set(TABLES)
    assert exported["schema_version"] == db.SCHEMA_VERSION
    assert all(exported[table] == [] for table in db.TABLES)


@pytest.mark.parametrize("table", TABLES)
def test_updates_are_refused_on_every_table(conn, table):
    column = {"document": "language", "segment": "kind", "claim": "polarity",
              "flag": "note", "assumption": "statement"}[table]
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        conn.execute(f"UPDATE {table} SET {column} = {column}")


@pytest.mark.parametrize("table", TABLES)
def test_deletes_are_refused_on_every_table(conn, table):
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        conn.execute(f"DELETE FROM {table}")


def test_values_outside_the_schema_are_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO segment (document_id, idx, start, end, kind) VALUES (?,?,?,?,?)",
                     (DOC_ID, 1, 25, 30, "paragraph"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO segment (document_id, idx, start, end, kind) VALUES (?,?,?,?,?)",
                     ("f" * 64, 0, 0, 5, "sentence"))


def test_a_failed_transaction_leaves_nothing_behind(conn):
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction(conn):
            conn.execute("INSERT INTO segment (document_id, idx, start, end, kind) VALUES (?,?,?,?,?)",
                         (DOC_ID, 1, 25, 30, "sentence"))
            conn.execute("INSERT INTO segment (document_id, idx, start, end, kind) VALUES (?,?,?,?,?)",
                         (DOC_ID, 1, 25, 30, "sentence"))
    assert conn.execute("SELECT count(*) FROM segment").fetchone()[0] == 1


def test_export_is_identical_for_two_independent_stores(tmp_path):
    first, second = db.connect(tmp_path / "one.sqlite"), db.connect(tmp_path / "two.sqlite")
    fill(first)
    fill(second)
    assert db.export(first) == db.export(second)
    exported = json.loads(db.export(first))
    assert exported["document"][0]["original_sha256"] is not None
    assert "original" not in exported["document"][0]
    assert exported["claim"][0]["value_low"] == "4200000000"


def test_reopening_a_store_keeps_its_contents(tmp_path):
    path = tmp_path / "store.sqlite"
    first = db.connect(path)
    fill(first)
    before = db.export(first)
    first.close()
    assert db.export(db.connect(path)) == before
