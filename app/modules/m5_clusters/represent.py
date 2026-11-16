"""代表元与簇标识：税号最小者为代表，无税号取供应商号最小者。"""
from __future__ import annotations


def choose_representative(members) -> dict:
    with_tax = sorted((member["tax_id"], member["supplier_id"])
                      for member in members if member["tax_id"])
    if with_tax:
        target = with_tax[0][1]
    else:
        target = min(member["supplier_id"] for member in members)
    for member in members:
        if member["supplier_id"] == target:
            return member
    return sorted(members, key=lambda member: member["supplier_id"])[0]


def distinct_taxes(members) -> list:
    return sorted({member["tax_id"] for member in members if member["tax_id"]})


def has_conflict(members) -> bool:
    return len(distinct_taxes(members)) > 1


def assign_ids(entries) -> list:
    """簇编号按 (税号, 代表号) 升序分配，与输入顺序无关。"""
    ordered = sorted(entries, key=lambda item: (item["tax_id"] or "\uffff", item["rep_id"]))
    for position, entry in enumerate(ordered, 1):
        entry["cluster_id"] = f"C-{position:04d}"
    return ordered
