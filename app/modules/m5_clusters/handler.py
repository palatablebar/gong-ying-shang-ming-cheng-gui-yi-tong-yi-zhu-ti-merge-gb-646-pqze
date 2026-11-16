"""M5 路由：合并簇重建、簇明细、对账账本。"""
from __future__ import annotations

from fastapi import APIRouter

from ... import store
from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api", tags=["m5-clusters"])


@router.post("/clusters")
def rebuild_clusters():
    run = intake_service.ensure_run()
    return service.ensure_clusters(run["run_id"])


@router.get("/clusters")
def list_clusters(limit: int = 60):
    run = intake_service.ensure_run()
    summary = service.ensure_clusters(run["run_id"])
    clusters = store.list_clusters(run["run_id"])[:limit]
    members = store.list_cluster_members(run["run_id"])
    return {
        "run_id": run["run_id"],
        "summary": summary,
        "items": clusters,
        "members": members[:400],
    }


@router.get("/reconcile")
def reconcile():
    run = intake_service.ensure_run()
    service.ensure_clusters(run["run_id"])
    return service.reconcile(run["run_id"])
