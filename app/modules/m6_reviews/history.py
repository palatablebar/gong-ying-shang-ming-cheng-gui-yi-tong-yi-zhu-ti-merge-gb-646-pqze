"""批次历史与复核时间窗：区间为左闭右开 [since, until)。"""
from __future__ import annotations

import json

from ... import store
from ...errors import DomainError
from ...manifest import parse_utc, utc_iso
from ...reasons import V_BAD_WINDOW


def _canonical(value: str, field: str) -> str:
    if not value:
        return ""
    try:
        moment = parse_utc(value)
    except (ValueError, TypeError):
        raise DomainError(V_BAD_WINDOW, field)
    return utc_iso(moment)


def runs(limit: int = 20) -> list:
    rows = []
    for run in store.list_runs()[:limit]:
        counts = json.loads(run["counts_json"] or "{}")
        rows.append({
            "run_id": run["run_id"],
            "created_at": run["created_at"],
            "rule_version": run["rule_version"],
            "input_sha256": run["input_sha256"],
            "elapsed_ms": run["elapsed_ms"],
            "counts": counts,
        })
    return rows


def decisions(run_id: str, since: str = "", until: str = "") -> list:
    lower = _canonical(since, "since")
    upper = _canonical(until, "until")
    return store.list_decisions(run_id, lower, upper)


def window_summary(run_id: str, since: str = "", until: str = "") -> dict:
    rows = decisions(run_id, since, until)
    merged = sum(1 for row in rows if row["decision"] == "merge")
    return {
        "since": _canonical(since, "since"),
        "until": _canonical(until, "until"),
        "total": len(rows),
        "merge": merged,
        "keep": len(rows) - merged,
        "items": rows,
    }
