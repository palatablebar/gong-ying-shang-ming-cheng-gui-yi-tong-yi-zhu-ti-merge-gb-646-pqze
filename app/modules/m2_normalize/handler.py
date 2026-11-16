"""M2 路由：归一结果表与单条预览。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ... import store
from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api", tags=["m2-normalize"])


class PreviewRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


@router.get("/normalize")
def normalize_table(limit: int = 120):
    run = intake_service.ensure_run()
    service.ensure_normalized(run["run_id"])
    rows = store.list_records(run["run_id"])[:limit]
    return {
        "run_id": run["run_id"],
        "summary": service.summary(run["run_id"]),
        "items": [
            {"supplier_id": row["supplier_id"], "raw_name": row["raw_name"],
             "norm_name": row["norm_name"], "codes": row["norm_codes"]}
            for row in rows
        ],
    }


@router.post("/normalize/preview")
def normalize_preview(body: PreviewRequest):
    return service.preview(body.name)
