"""应用入口：建表、注册模块路由、健康检查、领域错误映射。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import store
from .config import APP_NAME, RULE_VERSION
from .errors import DomainError
from .manifest import utc_iso, utc_now
from .modules.m1_intake.handler import router as intake_router
from .modules.m2_normalize.handler import router as normalize_router
from .modules.m3_blocks.handler import router as block_router
from .modules.m4_pairs.handler import router as pair_router
from .modules.m5_clusters.handler import router as cluster_router
from .modules.m6_reviews.handler import router as review_router
from .modules.m7_export.handler import router as export_router
from .web import router as page_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    yield


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title=APP_NAME, version=RULE_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
store.init_db()


@app.exception_handler(DomainError)
def handle_domain_error(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status, content=exc.as_body())


@app.get("/api/health")
def health():
    try:
        store.init_db()
        latest = store.latest_run()
        run_id = latest["run_id"] if latest else None
    except Exception:  # pragma: no cover - 数据库不可用时仍返回服务状态
        run_id = None
    return {
        "status": "ok",
        "service": "entitymerge",
        "rule_version": RULE_VERSION,
        "run_id": run_id,
        "utc": utc_iso(utc_now()),
    }


for router in (intake_router, normalize_router, block_router, pair_router,
               cluster_router, review_router, export_router, page_router):
    app.include_router(router)
