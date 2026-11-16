"""M3 路由：重建分块、查看候选对来源桶。"""
from __future__ import annotations

from fastapi import APIRouter

from ... import store
from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api", tags=["m3-blocks"])


@router.post("/blocks")
def rebuild_blocks():
    run = intake_service.ensure_run()
    result = service.rebuild(run["run_id"])
    result["pairs_root"] = "/api/pairs"
    return result


@router.get("/blocks")
def list_blocks(limit: int = 30):
    run = intake_service.ensure_run()
    service.ensure_blocks(run["run_id"])
    return {
        "run_id": run["run_id"],
        "summary": service.summary(run["run_id"]),
        "items": store.list_blocks(run["run_id"])[:limit],
    }
