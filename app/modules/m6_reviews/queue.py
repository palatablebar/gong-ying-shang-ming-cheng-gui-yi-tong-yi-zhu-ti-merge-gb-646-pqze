"""复核队列：待人工判定的候选对，以及引用一致性异常清单。"""
from __future__ import annotations

from decimal import Decimal

from ...reasons import (
    X_REF_CYCLE,
    X_REF_NOT_MASTER,
    X_REF_SELF,
    X_REF_UNKNOWN,
)


def build(pairs, records, decisions) -> list:
    by_id = records
    items = []
    for pair in pairs:
        if pair["verdict"] != "review":
            continue
        left = by_id.get(pair["left_id"], {})
        right = by_id.get(pair["right_id"], {})
        decision = decisions.get(pair["pair_id"])
        items.append({
            "pair_id": pair["pair_id"],
            "left_id": pair["left_id"],
            "right_id": pair["right_id"],
            "left_name": left.get("raw_name", ""),
            "right_name": right.get("raw_name", ""),
            "left_norm": left.get("norm_name", ""),
            "right_norm": right.get("norm_name", ""),
            "left_tax": left.get("tax_id", ""),
            "right_tax": right.get("tax_id", ""),
            "left_city": left.get("city", ""),
            "right_city": right.get("city", ""),
            "score": pair["score"],
            "dice": pair["dice"],
            "ratio": pair["ratio"],
            "reason_code": pair["reason_code"],
            "detail": pair["detail"],
            "version": decision["version"] if decision else 0,
            "decision": decision["decision"] if decision else "",
            "suggested": "merge" if Decimal(pair["score"]) >= Decimal("0.86") else "keep",
        })
    return sorted(items, key=lambda item: (-Decimal(item["score"]), item["pair_id"]))


def _walk(index, start: str, goal: str, limit: int) -> bool:
    current = start
    for _ in range(limit):
        node = index.get(current)
        if node is None:
            return False
        target = node["ref_master_id"]
        if not target:
            return False
        if target == goal:
            return True
        current = target
    return False


def reference_issues(records) -> list:
    """双向引用核验：自引、指向不存在、指向非主档、成环。"""
    index = {record["supplier_id"]: record for record in records}
    issues = []
    for supplier_id in sorted(index):
        record = index[supplier_id]
        target = record["ref_master_id"]
        if not target:
            continue
        if target == supplier_id:
            code, detail = X_REF_SELF, target
        elif target not in index:
            code, detail = X_REF_UNKNOWN, target
        elif index[target]["ref_master_id"] and _walk(index, target, supplier_id, len(index) + 1):
            code, detail = X_REF_CYCLE, f"{supplier_id} -> {target} -> {supplier_id}"
        elif index[target]["ref_master_id"]:
            code, detail = X_REF_NOT_MASTER, f"{target} -> {index[target]['ref_master_id']}"
        else:
            continue
        issues.append({
            "supplier_id": supplier_id,
            "ref_master_id": target,
            "reason_code": code,
            "detail": detail,
            "source_file": record["source_file"],
            "line_no": record["line_no"],
        })
    return issues
