"""M8 付款边界：整簇暂缓，暂缓金额留在付款账内分栏对账。

付款边界 = 主体簇。簇内出现两个及以上税号（H_TAX_CONFLICT）或成员牵涉
未决待核对（H_PENDING_REVIEW）时，付款对象不确定，整簇暂缓；暂缓金额
不从付款账删除，而是与可付分栏，可付 + 暂缓 = 簇金额合计，逐分守恒。
每个成员只属于一个簇，每个簇非可付即暂缓，因此同一成员金额在两栏之间
只出现一次。全部金额由簇表与复核决定确定性重算，同批重跑金额一致。
"""
from __future__ import annotations

from decimal import Decimal

from ... import store
from ...errors import NotFound
from ...reasons import H_PENDING_REVIEW, H_TAX_CONFLICT, V_UNKNOWN_RUN
from ..m5_clusters import service as cluster_service

PAYABLE = "可付"
HELD = "暂缓"


def _pending_pairs_by_supplier(run_id: str) -> dict:
    """未决待核对：判定为复核且尚无决定的候选对，按两侧供应商号索引。"""
    decided = {item["pair_id"] for item in store.list_decisions(run_id)}
    index = {}
    for pair in store.list_pairs(run_id, "review"):
        if pair["pair_id"] in decided:
            continue
        for side in (pair["left_id"], pair["right_id"]):
            index.setdefault(side, []).append(pair["pair_id"])
    return index


def _raw_rows(run_id: str) -> list:
    """逐簇判定：金额保持 Decimal，排序与合计完成后再字符串化。"""
    clusters = store.list_clusters(run_id)
    members = store.list_cluster_members(run_id)
    pending = _pending_pairs_by_supplier(run_id)

    members_by_cluster = {}
    for member in members:
        members_by_cluster.setdefault(member["cluster_id"], []).append(member)

    rows = []
    for cluster in clusters:
        cluster_members = members_by_cluster.get(cluster["cluster_id"], [])
        pair_ids = sorted({
            pair_id
            for member in cluster_members
            for pair_id in pending.get(member["supplier_id"], [])
        })
        reasons = []
        if cluster["conflict"]:
            reasons.append(H_TAX_CONFLICT)
        if pair_ids:
            reasons.append(H_PENDING_REVIEW)
        held = bool(reasons)
        total = Decimal(cluster["total_amount"])
        rows.append({
            "cluster_id": cluster["cluster_id"],
            "rep_id": cluster["rep_id"],
            "member_count": cluster["member_count"],
            "total_amount": total,
            "status": HELD if held else PAYABLE,
            "hold_reasons": reasons,
            "pending_pairs": pair_ids,
            "payable_amount": Decimal("0") if held else total,
            "held_amount": total if held else Decimal("0"),
            "members": [
                {"supplier_id": member["supplier_id"],
                 "share_amount": Decimal(member["share_amount"]),
                 "status": HELD if held else PAYABLE}
                for member in cluster_members
            ],
        })
    return rows


def _stringify(row: dict) -> dict:
    return {
        **row,
        "total_amount": str(row["total_amount"]),
        "payable_amount": str(row["payable_amount"]),
        "held_amount": str(row["held_amount"]),
        "members": [{**member, "share_amount": str(member["share_amount"])}
                    for member in row["members"]],
    }


def boundary(run_id: str) -> dict:
    """付款边界全量：逐簇状态、暂缓原因、成员金额与对账检查。"""
    if not store.get_run(run_id):
        raise NotFound(V_UNKNOWN_RUN, run_id)
    cluster_service.ensure_clusters(run_id)
    rows = _raw_rows(run_id)

    amount_total = sum((row["total_amount"] for row in rows), Decimal("0"))
    amount_payable = sum((row["payable_amount"] for row in rows), Decimal("0"))
    amount_held = sum((row["held_amount"] for row in rows), Decimal("0"))
    member_rows = [member for row in rows for member in row["members"]]
    member_payable = sum((member["share_amount"] for member in member_rows
                          if member["status"] == PAYABLE), Decimal("0"))
    member_held = sum((member["share_amount"] for member in member_rows
                       if member["status"] == HELD), Decimal("0"))
    member_ids = [member["supplier_id"] for member in member_rows]

    checks = [
        {"name": "付款边界守恒", "left": str(amount_total),
         "right": f"{amount_payable} + {amount_held}",
         "ok": amount_total == amount_payable + amount_held},
        {"name": "成员分栏守恒", "left": str(amount_total),
         "right": f"{member_payable} + {member_held}",
         "ok": amount_total == member_payable + member_held
         and amount_payable == member_payable and amount_held == member_held},
        {"name": "成员金额唯一", "left": len(member_ids), "right": len(set(member_ids)),
         "ok": len(member_ids) == len(set(member_ids))},
    ]
    held_rows = sorted((row for row in rows if row["status"] == HELD),
                       key=lambda row: (-row["held_amount"], row["cluster_id"]))
    payable_rows = sorted((row for row in rows if row["status"] == PAYABLE),
                          key=lambda row: (-row["payable_amount"], row["cluster_id"]))
    reason_counts = {
        H_TAX_CONFLICT: sum(1 for row in rows if H_TAX_CONFLICT in row["hold_reasons"]),
        H_PENDING_REVIEW: sum(1 for row in rows if H_PENDING_REVIEW in row["hold_reasons"]),
    }
    return {
        "run_id": run_id,
        "summary": {
            "amount_total": str(amount_total),
            "amount_payable": str(amount_payable),
            "amount_held": str(amount_held),
            "clusters": len(rows),
            "payable_clusters": len(payable_rows),
            "held_clusters": len(held_rows),
            "held_members": sum(row["member_count"] for row in held_rows),
            "reason_counts": reason_counts,
        },
        "held": [_stringify(row) for row in held_rows],
        "payable": [_stringify(row) for row in payable_rows],
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
    }


def summary(run_id: str) -> dict:
    """汇总视图：复核接口与导出清单共用的同一付款边界口径。"""
    result = boundary(run_id)
    return {**result["summary"], "run_id": result["run_id"], "ok": result["ok"]}


def status_map(run_id: str) -> dict:
    """簇号 -> 付款状态与暂缓原因，供簇列表页标注。"""
    result = boundary(run_id)
    return {row["cluster_id"]: {"status": row["status"], "hold_reasons": row["hold_reasons"],
                                "pending_pairs": row["pending_pairs"]}
            for row in result["held"] + result["payable"]}
