"""M7 路由：CSV 与运行清单下载。"""
from __future__ import annotations

from fastapi import APIRouter, Response

from ..m1_intake import service as intake_service
from . import service

router = APIRouter(prefix="/api/export", tags=["m7-export"])

CSV_TYPE = "text/csv; charset=utf-8"
JSON_TYPE = "application/json; charset=utf-8"


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content="\ufeff" + content,
        media_type=CSV_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/master.csv")
def export_master():
    run = intake_service.ensure_run()
    return _csv_response(service.master_csv(run["run_id"]),
                         f"master-{run['run_id']}.csv")


@router.get("/members.csv")
def export_members():
    run = intake_service.ensure_run()
    return _csv_response(service.members_csv(run["run_id"]),
                         f"members-{run['run_id']}.csv")


@router.get("/quarantine.csv")
def export_quarantine():
    run = intake_service.ensure_run()
    return _csv_response(service.quarantine_csv(run["run_id"]),
                         f"quarantine-{run['run_id']}.csv")


@router.get("/conflicts.csv")
def export_conflicts():
    run = intake_service.ensure_run()
    return _csv_response(service.conflicts_csv(run["run_id"]),
                         f"conflicts-{run['run_id']}.csv")


@router.get("/manifest.json")
def export_manifest():
    run = intake_service.ensure_run()
    return Response(content=service.manifest_json(run["run_id"]), media_type=JSON_TYPE,
                    headers={"Content-Disposition":
                             f'attachment; filename="manifest-{run["run_id"]}.json"'})
