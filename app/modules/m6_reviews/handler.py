"""M6 路由：复核队列、决定提交、时间窗历史、批次清单。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api", tags=["m6-reviews"])


class DecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=10)
    expected_version: int = Field(ge=0)
    operator: str = Field(default="采购主数据组", max_length=40)


@router.get("/reviews")
def review_queue(limit: int = 60):
    run = intake_service.ensure_run()
    items = service.queue_items(run["run_id"])
    return {"run_id": run["run_id"], "stats": service.queue_stats(run["run_id"]),
            "total": len(items), "items": items[:limit]}


@router.get("/reviews/stats")
def review_stats():
    run = intake_service.ensure_run()
    return service.queue_stats(run["run_id"])


@router.get("/reviews/history")
def review_history(since: str = Query(default=""), until: str = Query(default="")):
    run = intake_service.ensure_run()
    return service.decide_windows(run["run_id"], since, until)


@router.post("/reviews/{pair_id}/decision")
def submit_decision(pair_id: str, body: DecisionRequest):
    run = intake_service.ensure_run()
    record = service.decide(run["run_id"], pair_id, body.decision, body.expected_version,
                            body.operator)
    return {"run_id": run["run_id"], "decision": record,
            "queue": service.queue_stats(run["run_id"])}


@router.get("/batches")
def batches(limit: int = 20):
    run = intake_service.ensure_run()
    return {"run_id": run["run_id"], "items": service.batch_history(limit)}


@router.get("/batches/{run_id}")
def batch_detail(run_id: str):
    return intake_service.summary(run_id)
