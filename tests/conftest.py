"""测试基线：固定时区、每个测试独立 SQLite、样例批次夹具。"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["TZ"] = "UTC"
os.environ.setdefault("MERGE_DB", str(pathlib.Path(tempfile.mkdtemp()) / "session.db"))

import pytest  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("MERGE_DB", str(tmp_path / "merge.db"))
    from app import store
    store.init_db()
    yield store


@pytest.fixture()
def run(db):
    from app.modules.m1_intake import service
    return service.ingest()


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client
