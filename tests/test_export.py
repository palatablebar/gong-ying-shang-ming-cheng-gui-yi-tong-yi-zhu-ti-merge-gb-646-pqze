"""M7 主数据导出：CSV 导出规则、分摊守恒、运行清单与响应头。"""
from __future__ import annotations

import csv
import io
import json
from decimal import Decimal

from app import store
from app.modules.m5_clusters import service as cluster_service
from app.modules.m7_export import service
from tests.fixtures import expected as EXP


def _rows(text: str) -> list:
    return list(csv.reader(io.StringIO(text)))


def test_master_csv_rows(run):
    cluster_service.ensure_clusters(run["run_id"])
    rows = _rows(service.master_csv(run["run_id"]))
    assert rows[0][0] == "主体编号"
    assert rows[0][6] == "本年累计(元)"
    assert len(rows) - 1 == EXP.CLUSTERS


def test_master_csv_conflict_row(run):
    cluster_service.ensure_clusters(run["run_id"])
    rows = _rows(service.master_csv(run["run_id"]))
    header = rows[0]
    body = {row[0]: dict(zip(header, row)) for row in rows[1:]}
    target = body[EXP.CONFLICT_CLUSTER_ID]
    assert target["代表供应商号"] == EXP.CONFLICT_CLUSTER_REP
    assert target["本年累计(元)"] == "79200.00"
    assert target["簇状态"] == "税号冲突"
    assert target["成员数"] == "4"


def test_quarantine_csv(run):
    rows = _rows(service.quarantine_csv(run["run_id"]))
    assert rows[0] == ["来源文件", "行号", "原因码", "原因", "详情", "原始内容"]
    assert len(rows) - 1 == EXP.QUARANTINED
    codes = {row[2] for row in rows[1:]}
    assert codes == {"Q_ROW_SHORT", "Q_DUP_ID_SAME"}


def test_conflicts_csv(run):
    rows = _rows(service.conflicts_csv(run["run_id"]))
    assert len(rows) - 1 == EXP.CONFLICTS
    assert rows[1][0] == "S-0060"
    assert rows[1][1] == "city"


def test_manifest_json_fields(run):
    payload = json.loads(service.manifest_json(run["run_id"]))
    assert payload["run_id"] == EXP.RUN_ID
    assert payload["rule_version"]
    assert len(payload["input_sha256"]) == 64
    assert len(payload["files"]) == 6
    assert all(len(item["sha256"]) == 64 for item in payload["files"])
    assert payload["reconcile"]["ok"] is True
    assert payload["counts"]["accepted"] == EXP.ACCEPTED
    assert payload["reason_codes"]


def test_members_shares_conserved(run):
    cluster_service.ensure_clusters(run["run_id"])
    rows = _rows(service.members_csv(run["run_id"]))
    header = rows[0]
    share_index = header.index("分摊(元)")
    cluster_index = header.index("主体编号")
    totals = {row["cluster_id"]: Decimal(row["total_amount"])
              for row in store.list_clusters(run["run_id"])}
    summed = {}
    for row in rows[1:]:
        cluster_id = row[cluster_index]
        summed[cluster_id] = summed.get(cluster_id, Decimal("0")) + Decimal(row[share_index])
    assert summed == totals


def test_csv_response_headers(client):
    response = client.get("/api/export/master.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.startswith("\ufeff主体编号")


def test_all_export_endpoints(client):
    for path in ("/api/export/master.csv", "/api/export/members.csv",
                 "/api/export/quarantine.csv", "/api/export/conflicts.csv",
                 "/api/export/manifest.json"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.content, path
