"""M8 路由：付款边界查询。"""
from __future__ import annotations

from fastapi import APIRouter

from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api", tags=["m8-payment"])


@router.get("/payment")
def payment_boundary():
    run = intake_service.ensure_run()
    return service.boundary(run["run_id"])


@router.get("/payment/summary")
def payment_summary():
    run = intake_service.ensure_run()
    return service.summary(run["run_id"])
