"""M6 编排：复核队列、决定写入、引用异常、批次历史。"""
from __future__ import annotations

from ... import store
from ..m4_pairs import service as pair_service
from ..m5_clusters import service as cluster_service
from . import history, queue, version


def prepare(run_id: str) -> dict:
    pair_service.ensure_pairs(run_id)
    records = {record["supplier_id"]: record for record in store.list_records(run_id)}
    decisions = {item["pair_id"]: item for item in store.list_decisions(run_id)}
    return {"records": records, "decisions": decisions}


def queue_items(run_id: str) -> list:
    prepared = prepare(run_id)
    pairs = store.list_pairs(run_id, "review")
    return queue.build(pairs, prepared["records"], prepared["decisions"])


def queue_stats(run_id: str) -> dict:
    items = queue_items(run_id)
    decided = sum(1 for item in items if item["decision"])
    references = queue.reference_issues(list(prepare(run_id)["records"].values()))
    return {
        "pending": len(items) - decided,
        "decided": decided,
        "total": len(items),
        "references": len(references),
        "reference_codes": sorted({item["reason_code"] for item in references}),
    }


def reference_issues(run_id: str) -> list:
    return queue.reference_issues(store.list_records(run_id))


def decide(run_id: str, pair_id: str, decision: str, expected_version: int,
           operator: str = "采购主数据组") -> dict:
    pair_service.ensure_pairs(run_id)
    record = version.decide(run_id, pair_id, decision, expected_version, operator)
    cluster_service.ensure_clusters(run_id)
    return record


def decide_windows(run_id: str, since: str = "", until: str = "") -> dict:
    return history.window_summary(run_id, since, until)


def batch_history(limit: int = 20) -> list:
    return history.runs(limit)
