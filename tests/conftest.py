import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
# every test run uses its own throwaway database
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.sqlite")

import pytest  # noqa: E402
import db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.init()
    yield
