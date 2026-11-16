"""M3 分块编排：归一后建桶、落库、给出统计。"""
from __future__ import annotations

from ... import store
from ...errors import NotFound
from ...reasons import V_UNKNOWN_RUN
from ..m2_normalize import service as normalize_service
from . import blocking, stats


def ensure_blocks(run_id: str) -> dict:
    normalize_service.ensure_normalized(run_id)
    records = store.list_records(run_id)
    if not records:
        raise NotFound(V_UNKNOWN_RUN, run_id)
    if store.count(run_id, "blocks") and store.count(run_id, "block_pairs"):
        return summary(run_id)
    return rebuild(run_id)


def rebuild(run_id: str) -> dict:
    normalize_service.ensure_normalized(run_id)
    records = store.list_records(run_id)
    result = blocking.build(records)
    store.save_blocks(run_id, [(item["block_key"], item["member_count"])
                               for item in result["blocks"]])
    store.save_block_pairs(run_id, result["pairs"])
    payload = stats.summarize(result["blocks"], result["pairs"], result["skipped"],
                              result["truncated"])
    payload["skipped"] = result["skipped"][:20]
    payload["run_id"] = run_id
    return payload


def summary(run_id: str) -> dict:
    blocks = store.list_blocks(run_id)
    pairs = store.list_block_pairs(run_id)
    payload = stats.summarize(
        [{"member_count": block["member_count"]} for block in blocks],
        pairs, [], 0)
    payload["run_id"] = run_id
    payload["skipped"] = []
    payload["top_blocks"] = blocks[:10]
    return payload
