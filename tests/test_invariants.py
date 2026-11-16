"""不变量：行数守恒、金额守恒、幂等重跑、簇划分完整、版本单调。"""
from __future__ import annotations

from decimal import Decimal

from app import store
from app.modules.m1_intake import service as intake_service
from app.modules.m5_clusters import service as cluster_service
from app.modules.m6_reviews import service as review_service
from tests.fixtures import expected as EXP


def test_row_conservation(run):
    counts = intake_service.summary(run["run_id"])["counts"]
    assert counts["input_rows"] == (counts["accepted"] + counts["quarantined"]
                                    + counts["conflicts"])
    assert counts["accepted"] == store.count(run["run_id"], "records")
    assert counts["quarantined"] == store.count(run["run_id"], "quarantine")
    assert counts["conflicts"] == store.count(run["run_id"], "conflicts")


def test_amount_conservation(run):
    """记录级金额合计必须等于簇级合计（Decimal 逐分相等）。"""
    cluster_service.ensure_clusters(run["run_id"])
    records_total = sum((Decimal(row["ytd_amount"])
                         for row in store.list_records(run["run_id"])), Decimal("0"))
    clusters_total = sum((Decimal(row["total_amount"])
                          for row in store.list_clusters(run["run_id"])), Decimal("0"))
    shares_total = sum((Decimal(row["share_amount"])
                        for row in store.list_cluster_members(run["run_id"])), Decimal("0"))
    assert records_total == clusters_total == shares_total == EXP.AMOUNT_TOTAL


def test_idempotent_rerun(db):
    first = intake_service.ingest()
    second = intake_service.ingest()
    assert first["run_id"] == second["run_id"]
    assert first["counts_json"] == second["counts_json"]
    assert store.count(first["run_id"], "records") == EXP.ACCEPTED
    cluster_service.ensure_clusters(first["run_id"])
    first_total = cluster_service.summary(first["run_id"])["amount_total"]
    cluster_service.ensure_clusters(second["run_id"])
    second_total = cluster_service.summary(second["run_id"])["amount_total"]
    assert first_total == second_total == str(EXP.AMOUNT_TOTAL)


def test_cluster_partition_complete(run):
    cluster_service.ensure_clusters(run["run_id"])
    members = store.list_cluster_members(run["run_id"])
    supplier_ids = [row["supplier_id"] for row in members]
    assert len(supplier_ids) == len(set(supplier_ids)) == EXP.ACCEPTED
    clusters = store.list_clusters(run["run_id"])
    assert sum(row["member_count"] for row in clusters) == EXP.ACCEPTED
    assert len(clusters) == EXP.CLUSTERS


def test_decision_version_monotonic(run):
    first = review_service.decide(run["run_id"], EXP.PAIR_CITY_MISMATCH, "merge", 0)
    second = review_service.decide(run["run_id"], EXP.PAIR_CITY_MISMATCH, "keep", 1)
    assert first["version"] == 1
    assert second["version"] == 2
    assert second["expected_version"] == 1
