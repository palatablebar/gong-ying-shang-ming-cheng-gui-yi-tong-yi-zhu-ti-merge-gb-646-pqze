"""M4 相似判定编排：从候选对算分、落库、按结论聚合。"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal

from ... import store
from ...errors import NotFound
from ...reasons import V_UNKNOWN_RUN
from ..m3_blocks import service as block_service
from . import conflict, similarity, threshold


def ensure_pairs(run_id: str) -> dict:
    """每次重建，保证复核决定与新的归一名单立即反映到候选对。"""
    block_service.ensure_blocks(run_id)
    records = {record["supplier_id"]: record for record in store.list_records(run_id)}
    if not records:
        raise NotFound(V_UNKNOWN_RUN, run_id)
    pairs = []
    for item in store.list_block_pairs(run_id):
        left = records.get(item["left_id"])
        right = records.get(item["right_id"])
        if left is None or right is None:
            continue
        scored = similarity.score(left["norm_name"], right["norm_name"])
        verdict = conflict.decide(left, right, scored["score"])
        pairs.append({
            "pair_id": item["pair_id"],
            "left_id": item["left_id"],
            "right_id": item["right_id"],
            "dice": scored["dice"],
            "ratio": scored["ratio"],
            "score": scored["score"],
            "verdict": verdict["verdict"],
            "reason_code": verdict["reason_code"],
            "detail": verdict["detail"],
            "rules": verdict["rules"],
        })
    store.save_pairs(run_id, pairs)
    return verdict_stats(run_id)


def verdict_stats(run_id: str) -> dict:
    pairs = store.list_pairs(run_id)
    counter = Counter(pair["verdict"] for pair in pairs)
    codes = Counter(pair["reason_code"] for pair in pairs)
    scores = [Decimal(pair["score"]) for pair in pairs]
    return {
        "total": len(pairs),
        "auto": counter.get("auto", 0),
        "review": counter.get("review", 0),
        "reject": counter.get("reject", 0),
        "max_score": str(max(scores)) if scores else "0.000000",
        "min_score": str(min(scores)) if scores else "0.000000",
        "reason_codes": [{"code": code, "count": count} for code, count in codes.most_common()],
        "thresholds": threshold.describe(),
    }


def details(run_id: str, verdict: str = "") -> list:
    records = {record["supplier_id"]: record for record in store.list_records(run_id)}
    rows = []
    for pair in store.list_pairs(run_id, verdict):
        left = records.get(pair["left_id"], {})
        right = records.get(pair["right_id"], {})
        rows.append({
            **pair,
            "left_name": left.get("raw_name", ""),
            "right_name": right.get("raw_name", ""),
            "left_norm": left.get("norm_name", ""),
            "right_norm": right.get("norm_name", ""),
            "left_tax": left.get("tax_id", ""),
            "right_tax": right.get("tax_id", ""),
            "left_city": left.get("city", ""),
            "right_city": right.get("city", ""),
        })
    return rows
