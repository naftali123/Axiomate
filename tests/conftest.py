import shutil

import pytest

import support
from axiomate.store import db


@pytest.fixture(scope="session")
def _filings_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("filings") / "store.db"
    conn = db.connect(path)
    support.ingest_all(conn)
    conn.close()
    return path


@pytest.fixture
def filings(_filings_db, tmp_path):
    """A fresh store holding the ten sample filings and no claims."""
    path = tmp_path / "store.db"
    shutil.copy(_filings_db, path)
    conn = db.connect(path)
    yield conn
    conn.close()
