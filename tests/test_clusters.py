"""M5 等价类合并：代表元、传递冲突、顺序无关、最大余额分摊与对账。"""
from __future__ import annotations

from decimal import Decimal

from app import store
from app.modules.m5_clusters import allocate, represent, service
from app.modules.m6_reviews import service as review_service
from tests.fixtures import expected as EXP


def _members(run_id: str, cluster_id: str) -> dict:
    return {row["supplier_id"]: Decimal(row["share_amount"])
            for row in store.list_cluster_members(run_id, cluster_id)}


def test_decimal_total_exact(run):
    """TRAP-10 浮点累加：簇合计必须逐分精确，等于成员 Decimal 之和。"""
    service.ensure_clusters(run["run_id"])
    cluster = {row["cluster_id"]: row for row in store.list_clusters(run["run_id"])}
    target = cluster[EXP.CONFLICT_CLUSTER_ID]
    assert Decimal(target["total_amount"]) == EXP.CONFLICT_CLUSTER_TOTAL
    members = _members(run["run_id"], EXP.CONFLICT_CLUSTER_ID)
    assert sum(members.values(), Decimal("0")) == EXP.CONFLICT_CLUSTER_TOTAL
    assert members == dict(EXP.CONFLICT_CLUSTER_SHARES)
    assert target["total_amount"] == "79200.00"


def test_representative_min_tax(run):
    service.ensure_clusters(run["run_id"])
    clusters = {row["cluster_id"]: row for row in store.list_clusters(run["run_id"])}
    assert clusters[EXP.CONFLICT_CLUSTER_ID]["rep_id"] == EXP.CONFLICT_CLUSTER_REP
    assert clusters[EXP.CONFLICT_CLUSTER_ID]["city"] == "南京"


def test_representative_without_tax():
    members = [
        {"supplier_id": "S-9", "tax_id": ""},
        {"supplier_id": "S-2", "tax_id": ""},
        {"supplier_id": "S-5", "tax_id": ""},
    ]
    assert represent.choose_representative(members)["supplier_id"] == "S-2"


def test_cluster_conflict_transitive(run):
    """空税号记录把两个不同税号的主体连成一个簇，必须标冲突并交复核。"""
    summary = service.ensure_clusters(run["run_id"])
    assert summary["clusters"] == EXP.CLUSTERS
    assert summary["conflict_clusters"] == EXP.CONFLICT_CLUSTERS
    cluster = {row["cluster_id"]: row for row in store.list_clusters(run["run_id"])}
    target = cluster[EXP.CONFLICT_CLUSTER_ID]
    assert target["conflict"] == 1
    assert target["member_count"] == 4
    taxes = represent.distinct_taxes([
        {"tax_id": "91320105MA1N2P3Q4"}, {"tax_id": ""},
        {"tax_id": "91320105MA9Z8Y7X6"}, {"tax_id": ""},
    ])
    assert taxes == ["91320105MA1N2P3Q4", "91320105MA9Z8Y7X6"]


def test_merge_order_independent(run, monkeypatch):
    """TRAP-22 同一主体多别名：打乱候选对顺序，簇划分与代表元不变。"""
    service.ensure_clusters(run["run_id"])
    baseline = {row["rep_id"]: row["member_count"]
                for row in store.list_clusters(run["run_id"])}
    baseline_map = {row["supplier_id"]: row["cluster_id"]
                    for row in store.list_cluster_members(run["run_id"])}

    original = store.list_pairs
    monkeypatch.setattr(store, "list_pairs",
                        lambda *args, **kwargs: list(reversed(original(*args, **kwargs))))
    service.ensure_clusters(run["run_id"])
    again_map = {row["supplier_id"]: row["cluster_id"]
                 for row in store.list_cluster_members(run["run_id"])}
    assert again_map == baseline_map
    again = {row["rep_id"]: row["member_count"] for row in store.list_clusters(run["run_id"])}
    assert again == baseline


def test_share_largest_remainder():
    """TRAP-24 舍入尾差：分到 0.01 后合计仍等于总额。"""
    shares = allocate.allocate(Decimal("100.00"), [("a", 1), ("b", 1), ("c", 1)])
    assert [value for _, value in shares] == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert sum(value for _, value in shares) == Decimal("100.00")

    weighted = allocate.allocate(Decimal("10.00"), [("x", 1), ("y", 2)])
    assert sum(value for _, value in weighted) == Decimal("10.00")
    assert dict(weighted) == {"x": Decimal("3.33"), "y": Decimal("6.67")}


def test_allocate_degenerate():
    assert allocate.allocate(Decimal("0.00"), [("a", 1), ("b", 3)]) == [
        ("a", Decimal("0.00")), ("b", Decimal("0.00"))]
    assert allocate.allocate(Decimal("0.00"), []) == []
    negative = allocate.allocate(Decimal("-1.00"), [("a", 1), ("b", 1)])
    assert sum(value for _, value in negative) == Decimal("-1.00")


def test_singleton_cluster(run):
    service.ensure_clusters(run["run_id"])
    members = {row["supplier_id"]: row["cluster_id"]
               for row in store.list_cluster_members(run["run_id"])}
    cluster = {row["cluster_id"]: row for row in store.list_clusters(run["run_id"])}
    assert cluster[members["S-0020"]]["member_count"] == 1
    summary = service.summary(run["run_id"])
    assert summary["singletons"] == EXP.SINGLETONS
    assert summary["merged_members"] == EXP.MERGED_MEMBERS


def test_reconcile_balances(run):
    service.ensure_clusters(run["run_id"])
    ledger = service.reconcile(run["run_id"])
    assert ledger["ok"] is True
    assert ledger["input_rows"] == EXP.INPUT_ROWS
    assert ledger["accepted"] == EXP.ACCEPTED
    assert ledger["subjects"] == EXP.CLUSTERS
    assert ledger["merged_members"] == EXP.MERGED_MEMBERS
    assert Decimal(ledger["amount_records"]) == EXP.AMOUNT_TOTAL
    assert ledger["amount_records"] == ledger["amount_clusters"]
    names = {check["name"] for check in ledger["checks"]}
    assert names == {"记录守恒", "主体拆分", "金额守恒", "候选对分档"}


def test_decision_merge_changes_clusters(run):
    service.ensure_clusters(run["run_id"])
    before = len(store.list_clusters(run["run_id"]))
    review_service.decide(run["run_id"], EXP.PAIR_CITY_MISMATCH, "merge", 0)
    after = len(store.list_clusters(run["run_id"]))
    assert after == before - 1
    members = {row["supplier_id"]: row["cluster_id"]
               for row in store.list_cluster_members(run["run_id"])}
    assert members["S-0078"] == members["S-0013"]


def test_clusters_api(client):
    response = client.get("/api/clusters")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["clusters"] == EXP.CLUSTERS
    assert body["items"]
    reconcile = client.get("/api/reconcile")
    assert reconcile.status_code == 200
    assert reconcile.json()["ok"] is True
