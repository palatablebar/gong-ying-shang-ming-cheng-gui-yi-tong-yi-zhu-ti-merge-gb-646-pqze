"""端到端：脏样例 → 采信 → 归一 → 候选对 → 合并 → 复核 → 导出。"""
from __future__ import annotations

import csv
import io
import json

from tests.fixtures import expected as EXP

PAGES = (
    ("/", "台账总览"),
    ("/normalize", "名称归一"),
    ("/pairs", "候选对"),
    ("/clusters", "合并簇"),
    ("/reviews", "复核队列"),
    ("/export", "主数据导出"),
)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["rule_version"]


def test_main_flow_from_dirty_samples(client):
    imported = client.post("/api/suppliers/import", json={})
    assert imported.status_code == 200
    body = imported.json()
    assert body["run_id"] == EXP.RUN_ID
    assert body["counts"]["accepted"] == EXP.ACCEPTED
    assert body["counts"]["quarantined"] == EXP.QUARANTINED

    for path, marker in PAGES:
        page = client.get(path)
        assert page.status_code == 200, path
        assert marker in page.text, path
        assert "suppliers" not in path

    master = client.get("/api/export/master.csv")
    rows = list(csv.reader(io.StringIO(master.text.lstrip("\ufeff"))))
    assert len(rows) - 1 == EXP.CLUSTERS

    manifest = client.get("/api/export/manifest.json")
    payload = json.loads(manifest.text)
    assert payload["reconcile"]["ok"] is True
    assert payload["run_id"] == EXP.RUN_ID


def test_rerun_same_input_same_numbers(client):
    first = client.post("/api/suppliers/import", json={"force": True}).json()
    second = client.post("/api/suppliers/import", json={"force": True}).json()
    assert first["run_id"] == second["run_id"] == EXP.RUN_ID
    assert first["counts"] == second["counts"]

    clusters_first = client.get("/api/clusters").json()["summary"]
    clusters_second = client.get("/api/clusters").json()["summary"]
    assert clusters_first["clusters"] == clusters_second["clusters"] == EXP.CLUSTERS
    assert clusters_first["amount_total"] == clusters_second["amount_total"] == str(EXP.AMOUNT_TOTAL)


def test_pages_show_signoff_and_batch_stamp(client):
    page = client.get("/clusters")
    assert page.status_code == 200
    text = page.text
    assert "制表 集团采购中心" in text
    assert EXP.RUN_ID in text
    assert "UTC+08:00" in text
    assert "<table" in text
