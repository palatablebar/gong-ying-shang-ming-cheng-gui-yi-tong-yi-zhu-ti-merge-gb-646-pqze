"""M8 付款边界：整簇暂缓、分栏守恒、成员唯一、幂等重跑与导出对账。"""
from __future__ import annotations

import csv
import io
import json
from decimal import Decimal

from app import store
from app.modules.m1_intake import service as intake_service
from app.modules.m5_clusters import service as cluster_service
from app.modules.m6_reviews import service as review_service
from app.modules.m7_export import service as export_service
from app.modules.m8_payment import service as payment_service
from tests.fixtures import expected as EXP


def _decide_all_reviews(run_id: str, decision: str = "keep") -> None:
    cluster_service.ensure_clusters(run_id)
    for pair in store.list_pairs(run_id, "review"):
        review_service.decide(run_id, pair["pair_id"], decision, 0)


def test_boundary_conservation(run):
    result = payment_service.boundary(run["run_id"])
    assert result["ok"] is True
    summary = result["summary"]
    assert Decimal(summary["amount_payable"]) + Decimal(summary["amount_held"]) \
        == Decimal(summary["amount_total"]) == EXP.AMOUNT_TOTAL
    assert summary["clusters"] == EXP.CLUSTERS
    assert summary["payable_clusters"] + summary["held_clusters"] == EXP.CLUSTERS
    assert [check["name"] for check in result["checks"]] \
        == ["付款边界守恒", "成员分栏守恒", "成员金额唯一"]


def test_conflict_cluster_held(run):
    """簇内两个税号：整簇暂缓，暂缓金额留在付款账内。"""
    result = payment_service.boundary(run["run_id"])
    held = {row["cluster_id"]: row for row in result["held"]}
    target = held[EXP.CONFLICT_CLUSTER_ID]
    assert "H_TAX_CONFLICT" in target["hold_reasons"]
    assert Decimal(target["held_amount"]) == EXP.CONFLICT_CLUSTER_TOTAL
    assert Decimal(target["payable_amount"]) == 0
    shares = sum((Decimal(member["share_amount"]) for member in target["members"]),
                 Decimal("0"))
    assert shares == EXP.CONFLICT_CLUSTER_TOTAL


def test_pending_review_pairs_hold_clusters(run):
    """未决待核对触及的簇整簇暂缓，并给出待核对编号作为证据。"""
    cluster_service.ensure_clusters(run["run_id"])
    pairs = store.list_pairs(run["run_id"], "review")
    assert len(pairs) == EXP.PAIRS_REVIEW
    side_ids = {pair["left_id"] for pair in pairs} | {pair["right_id"] for pair in pairs}
    members = store.list_cluster_members(run["run_id"])
    touched = {member["cluster_id"] for member in members
               if member["supplier_id"] in side_ids}
    result = payment_service.boundary(run["run_id"])
    held = {row["cluster_id"]: row for row in result["held"]}
    assert set(held) == touched | {EXP.CONFLICT_CLUSTER_ID}
    for cluster_id in touched:
        assert "H_PENDING_REVIEW" in held[cluster_id]["hold_reasons"]
        assert held[cluster_id]["pending_pairs"]


def test_member_amount_appears_once(run):
    """同一成员金额只能在可付与暂缓之间出现一次。"""
    result = payment_service.boundary(run["run_id"])
    seen = {}
    for row in result["held"] + result["payable"]:
        for member in row["members"]:
            assert member["supplier_id"] not in seen
            assert member["status"] == row["status"]
            seen[member["supplier_id"]] = member["status"]
    assert len(seen) == EXP.ACCEPTED


def test_decisions_release_pending_holds(run):
    """全部待核对判定后暂缓解除；税号冲突簇仍暂缓，金额不变。"""
    _decide_all_reviews(run["run_id"])
    result = payment_service.boundary(run["run_id"])
    assert [row["cluster_id"] for row in result["held"]] == [EXP.CONFLICT_CLUSTER_ID]
    summary = result["summary"]
    assert Decimal(summary["amount_held"]) == EXP.CONFLICT_CLUSTER_TOTAL
    assert Decimal(summary["amount_payable"]) == EXP.AMOUNT_TOTAL - EXP.CONFLICT_CLUSTER_TOTAL
    assert summary["reason_counts"]["H_PENDING_REVIEW"] == 0
    assert summary["reason_counts"]["H_TAX_CONFLICT"] == EXP.CONFLICT_CLUSTERS


def test_rerun_same_batch_same_amounts(db):
    """同一批重跑：批次号不变，付款边界金额逐项一致。"""
    first = intake_service.ingest()
    first_summary = payment_service.summary(first["run_id"])
    second = intake_service.ingest(force=True)
    second_summary = payment_service.summary(second["run_id"])
    assert first["run_id"] == second["run_id"] == EXP.RUN_ID
    assert first_summary == second_summary
    assert payment_service.summary(first["run_id"]) == first_summary


def test_payment_csv_member_rows(run):
    """导出与页面同一边界：一个成员一行，按状态汇总等于分栏合计。"""
    rows = list(csv.reader(io.StringIO(export_service.payment_csv(run["run_id"]))))
    assert rows[0] == ["主体编号", "成员供应商号", "成员分摊(元)", "付款状态", "暂缓原因码",
                       "待核候选对"]
    body = rows[1:]
    assert len(body) == EXP.ACCEPTED
    suppliers = [row[1] for row in body]
    assert len(set(suppliers)) == len(suppliers)
    payable = sum((Decimal(row[2]) for row in body if row[3] == "可付"), Decimal("0"))
    held = sum((Decimal(row[2]) for row in body if row[3] == "暂缓"), Decimal("0"))
    summary = payment_service.summary(run["run_id"])
    assert payable == Decimal(summary["amount_payable"])
    assert held == Decimal(summary["amount_held"])
    assert payable + held == EXP.AMOUNT_TOTAL


def test_manifest_carries_payment(run):
    payload = json.loads(export_service.manifest_json(run["run_id"]))
    payment = payload["payment"]
    assert payment["run_id"] == EXP.RUN_ID
    assert payment["ok"] is True
    assert Decimal(payment["amount_total"]) == EXP.AMOUNT_TOTAL
    assert Decimal(payment["amount_payable"]) + Decimal(payment["amount_held"]) \
        == EXP.AMOUNT_TOTAL


def test_payment_api(client):
    client.post("/api/suppliers/import", json={})
    boundary = client.get("/api/payment").json()
    assert boundary["ok"] is True
    assert boundary["summary"]["amount_total"] == str(EXP.AMOUNT_TOTAL)
    summary = client.get("/api/payment/summary").json()
    assert summary["amount_payable"] == boundary["summary"]["amount_payable"]
    assert summary["amount_held"] == boundary["summary"]["amount_held"]


def test_reviews_api_and_decision_carry_payment(client):
    """复核记录与页面按同一付款边界对账：判定响应里的口径与查询一致。"""
    client.post("/api/suppliers/import", json={})
    queue = client.get("/api/reviews").json()
    assert queue["payment"]["amount_total"] == str(EXP.AMOUNT_TOTAL)
    assert queue["payment"]["held_clusters"] >= 1
    target = queue["items"][0]
    response = client.post(f"/api/reviews/{target['pair_id']}/decision",
                           json={"decision": "keep",
                                 "expected_version": target["version"]})
    assert response.status_code == 200
    body = response.json()
    assert body["payment"] == client.get("/api/payment/summary").json()


def test_payment_csv_endpoint(client):
    client.post("/api/suppliers/import", json={})
    response = client.get("/api/export/payment.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.text.startswith("﻿主体编号")
    rows = list(csv.reader(io.StringIO(response.text.lstrip("﻿"))))
    assert len(rows) - 1 == EXP.ACCEPTED


def test_pages_share_payment_boundary(client):
    reviews = client.get("/reviews")
    assert reviews.status_code == 200
    assert "付款边界" in reviews.text
    assert "簇内税号冲突暂缓" in reviews.text
    assert EXP.CONFLICT_CLUSTER_ID in reviews.text
    clusters = client.get("/clusters")
    assert "付款状态" in clusters.text
    assert "暂缓" in clusters.text
    export = client.get("/export")
    assert "/api/export/payment.csv" in export.text
    assert "付款边界" in export.text
