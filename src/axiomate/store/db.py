"""Connection handling, transactions and the canonical export of the store."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 2
# The script that brings a store from the version before to each version.
_UPGRADES = {1: "schema.sql", 2: "schema_v2.sql"}

# Tables in export order, each with the columns that order its rows.
TABLES: dict[str, tuple[str, ...]] = {
    "document": ("id",),
    "segment": ("document_id", "idx"),
    "claim": ("id", "version"),
    "flag": ("claim_id", "claim_version", "seq"),
    "assumption": ("claim_id", "claim_version", "seq"),
    "interpretation_run": ("id",),
    "candidate_outcome": ("run_id", "segment_index", "seq"),
}


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the store at `path`, creating its schema or upgrading it in place if needed."""
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(f"store has schema version {version}, newer than this program's {SCHEMA_VERSION}")
    # A new store gets every script; an older store gets the ones it lacks. Additions only.
    for target in range(version + 1, SCHEMA_VERSION + 1):
        script = resources.files("axiomate.store").joinpath(_UPGRADES[target]).read_text(encoding="utf-8")
        conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {target};\nCOMMIT;")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block so that either all of its writes are stored or none are."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def export(conn: sqlite3.Connection) -> str:
    """Return a canonical dump of the whole store.

    Two stores built from the same inputs give byte-identical output. The
    original bytes of a document are represented by their SHA-256, recomputed
    from what is stored.
    """
    dump: dict[str, object] = {"schema_version": conn.execute("PRAGMA user_version").fetchone()[0]}
    for table, order in TABLES.items():
        rows = []
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY {', '.join(order)}"):
            record = dict(row)
            if table == "document":
                record["original_sha256"] = hashlib.sha256(record.pop("original")).hexdigest()
            rows.append(record)
        dump[table] = rows
    return export_text(dump)


def export_text(dump: object) -> str:
    """The canonical text form of an export."""
    return json.dumps(dump, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
