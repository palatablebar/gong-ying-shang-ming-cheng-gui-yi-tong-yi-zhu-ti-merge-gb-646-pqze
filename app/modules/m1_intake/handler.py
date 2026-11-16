"""M1 路由：采信触发、采信摘要、名录明细。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ... import store
from ...errors import NotFound
from ...reasons import V_UNKNOWN_RUN
from . import service

router = APIRouter(prefix="/api", tags=["m1-intake"])


class ImportRequest(BaseModel):
    files: list[str] | None = None
    force: bool = False


@router.post("/suppliers/import")
def import_suppliers(body: ImportRequest | None = None):
    payload = body or ImportRequest()
    run = service.ingest(files=payload.files, force=payload.force)
    return service.summary(run["run_id"])


@router.get("/suppliers/import")
def import_status():
    run = service.ensure_run()
    return service.summary(run["run_id"])


@router.get("/suppliers")
def list_suppliers(limit: int = 60, offset: int = 0):
    run = service.ensure_run()
    rows = store.list_records(run["run_id"])
    return {
        "run_id": run["run_id"],
        "total": len(rows),
        "items": rows[offset:offset + limit],
    }


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: str):
    run = service.ensure_run()
    record = store.get_record(run["run_id"], supplier_id)
    if not record:
        raise NotFound(V_UNKNOWN_RUN, supplier_id)
    return record
