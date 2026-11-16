"""复核决定的乐观锁：expected_version 与当前版本不一致即拒绝。"""
from __future__ import annotations

from ... import store
from ...errors import Conflict, DomainError, NotFound
from ...manifest import utc_iso, utc_now
from ...reasons import P_TAX_CONFLICT, V_BAD_DECISION, V_STALE_DECISION, V_UNKNOWN_PAIR

ALLOWED = ("merge", "keep")


def current_version(run_id: str, pair_id: str) -> int:
    decision = store.get_decision(run_id, pair_id)
    return decision["version"] if decision else 0


def decide(run_id: str, pair_id: str, decision: str, expected_version: int,
           operator: str = "采购主数据组") -> dict:
    if decision not in ALLOWED:
        raise DomainError(V_BAD_DECISION, decision)
    pair = store.get_pair(run_id, pair_id)
    if pair is None:
        raise NotFound(V_UNKNOWN_PAIR, pair_id)
    if decision == "merge" and pair["reason_code"] == P_TAX_CONFLICT:
        raise DomainError(V_BAD_DECISION, "税号冲突不可合并")
    current = current_version(run_id, pair_id)
    if expected_version != current:
        raise Conflict(V_STALE_DECISION, f"当前版本 {current}")
    record = {
        "run_id": run_id,
        "pair_id": pair_id,
        "decision": decision,
        "expected_version": expected_version,
        "version": current + 1,
        "operator": operator,
        "decided_at": utc_iso(utc_now()),
    }
    store.save_decision(record)
    return record
