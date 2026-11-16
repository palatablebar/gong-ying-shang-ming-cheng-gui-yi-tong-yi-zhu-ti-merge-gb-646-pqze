"""M4 路由：重建候选对、按结论过滤、单对明细。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from ... import store
from ...errors import NotFound
from ...reasons import V_UNKNOWN_PAIR
from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api", tags=["m4-pairs"])


@router.post("/pairs")
def rebuild_pairs():
    run = intake_service.ensure_run()
    stats = service.ensure_pairs(run["run_id"])
    stats["run_id"] = run["run_id"]
    return stats


@router.get("/pairs")
def list_pairs(verdict: str = Query(default="", pattern="^(|auto|review|reject)$"),
               limit: int = 100):
    run = intake_service.ensure_run()
    service.ensure_pairs(run["run_id"])
    items = service.details(run["run_id"], verdict)[:limit]
    return {"run_id": run["run_id"], "stats": service.verdict_stats(run["run_id"]),
            "total": len(items), "items": items}


@router.get("/pairs/stats")
def pair_stats():
    run = intake_service.ensure_run()
    service.ensure_pairs(run["run_id"])
    return service.verdict_stats(run["run_id"])


@router.get("/pairs/{pair_id}")
def pair_detail(pair_id: str):
    run = intake_service.ensure_run()
    service.ensure_pairs(run["run_id"])
    row = store.get_pair(run["run_id"], pair_id)
    if not row:
        raise NotFound(V_UNKNOWN_PAIR, pair_id)
    return row
