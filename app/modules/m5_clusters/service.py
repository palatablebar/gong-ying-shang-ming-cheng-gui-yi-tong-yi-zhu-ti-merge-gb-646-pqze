"""M5 等价类合并：并查集、代表元、簇金额与对账账本。"""
from __future__ import annotations

import json
from decimal import Decimal

from ... import store
from ...errors import NotFound
from ...reasons import C_CLUSTER_CONFLICT, P_TAX_CONFLICT, V_UNKNOWN_RUN
from ..m4_pairs import service as pair_service
from . import allocate, represent, unionfind


def _sum(records) -> Decimal:
    return sum((Decimal(record["ytd_amount"]) for record in records), Decimal("0"))


def ensure_clusters(run_id: str) -> dict:
    """总是重算：复核决定写入后，簇与金额立即一致。"""
    pair_service.ensure_pairs(run_id)
    records = {record["supplier_id"]: record for record in store.list_records(run_id)}
    if not records:
        raise NotFound(V_UNKNOWN_RUN, run_id)
    decisions = {item["pair_id"]: item for item in store.list_decisions(run_id)}
    dsu = unionfind.DisjointSet()
    for supplier_id in records:
        dsu.add(supplier_id)

    for pair in store.list_pairs(run_id):
        decision = decisions.get(pair["pair_id"])
        if decision:
            if decision["decision"] == "keep":
                continue
            if decision["decision"] == "merge" and pair["reason_code"] != P_TAX_CONFLICT:
                dsu.union(pair["left_id"], pair["right_id"])
            continue
        if pair["verdict"] == "auto":
            dsu.union(pair["left_id"], pair["right_id"])

    entries = []
    for members_ids in dsu.groups():
        members = [records[supplier_id] for supplier_id in members_ids]
        rep = represent.choose_representative(members)
        taxes = represent.distinct_taxes(members)
        entries.append({
            "rep_id": rep["supplier_id"],
            "tax_id": rep["tax_id"],
            "city": rep["city"],
            "members": members,
            "member_count": len(members),
            "total_amount": _sum(members),
            "conflict": len(taxes) > 1,
            "taxes": taxes,
        })

    clusters, member_rows = [], []
    for entry in represent.assign_ids(entries):
        weights = [(member["supplier_id"], Decimal(member["ytd_amount"]))
                   for member in sorted(entry["members"], key=lambda item: item["supplier_id"])]
        shares = allocate.allocate(entry["total_amount"], weights)
        clusters.append({
            "cluster_id": entry["cluster_id"],
            "rep_id": entry["rep_id"],
            "tax_id": entry["tax_id"],
            "city": entry["city"],
            "member_count": entry["member_count"],
            "total_amount": entry["total_amount"],
            "conflict": entry["conflict"],
            "taxes": entry["taxes"],
        })
        for supplier_id, share in shares:
            member_rows.append({"cluster_id": entry["cluster_id"],
                                "supplier_id": supplier_id,
                                "share_amount": share})
    store.save_clusters(run_id, clusters, member_rows)
    return summary(run_id)


def summary(run_id: str) -> dict:
    clusters = store.list_clusters(run_id)
    records = store.list_records(run_id)
    totals = sum((Decimal(cluster["total_amount"]) for cluster in clusters), Decimal("0"))
    return {
        "run_id": run_id,
        "clusters": len(clusters),
        "records": len(records),
        "merged_members": len(records) - len(clusters),
        "conflict_clusters": sum(1 for cluster in clusters if cluster["conflict"]),
        "conflict_code": C_CLUSTER_CONFLICT if any(cluster["conflict"] for cluster in clusters)
        else "",
        "singletons": sum(1 for cluster in clusters if cluster["member_count"] == 1),
        "amount_total": str(totals),
        "max_cluster": max((cluster["member_count"] for cluster in clusters), default=0),
    }


def reconcile(run_id: str) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise NotFound(V_UNKNOWN_RUN, run_id)
    counts = json.loads(run["counts_json"] or "{}")
    records = store.list_records(run_id)
    clusters = store.list_clusters(run_id)
    pairs = store.list_pairs(run_id)
    input_rows = counts.get("input_rows", 0)
    accepted = len(records)
    quarantined = len(store.list_quarantine(run_id))
    conflicts = len(store.list_conflicts(run_id))
    subjects = len(clusters)
    merged = accepted - subjects
    amount_records = _sum(records)
    amount_clusters = sum((Decimal(cluster["total_amount"]) for cluster in clusters), Decimal("0"))
    bands = {"auto": 0, "review": 0, "reject": 0}
    for pair in pairs:
        bands[pair["verdict"]] = bands.get(pair["verdict"], 0) + 1
    checks = [
        {"name": "记录守恒", "left": input_rows, "right": accepted + quarantined + conflicts,
         "ok": input_rows == accepted + quarantined + conflicts},
        {"name": "主体拆分", "left": accepted, "right": subjects + merged,
         "ok": accepted == subjects + merged},
        {"name": "金额守恒", "left": str(amount_records), "right": str(amount_clusters),
         "ok": amount_records == amount_clusters},
        {"name": "候选对分档", "left": len(pairs), "right": sum(bands.values()),
         "ok": len(pairs) == sum(bands.values())},
    ]
    return {
        "run_id": run_id,
        "input_rows": input_rows,
        "accepted": accepted,
        "quarantined": quarantined,
        "conflicts": conflicts,
        "subjects": subjects,
        "merged_members": merged,
        "conflict_clusters": sum(1 for cluster in clusters if cluster["conflict"]),
        "conflict_code": C_CLUSTER_CONFLICT if any(cluster["conflict"] for cluster in clusters)
        else "",
        "singletons": sum(1 for cluster in clusters if cluster["member_count"] == 1),
        "amount_records": str(amount_records),
        "amount_clusters": str(amount_clusters),
        "bands": bands,
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
    }
