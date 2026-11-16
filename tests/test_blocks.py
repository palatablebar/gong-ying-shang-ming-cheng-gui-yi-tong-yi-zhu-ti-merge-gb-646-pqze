"""M3 分块候选：bigram 桶、超大桶跳过、候选截断与确定性。"""
from __future__ import annotations

import json

from app import store
from app.modules.m3_blocks import blocking, ngram, service


def _record(supplier_id: str, name: str) -> dict:
    return {"supplier_id": supplier_id, "raw_name": name, "norm_name": name}


def test_bigram_set():
    assert ngram.bigrams("华远物流") == {"华远", "远物", "物流"}
    assert ngram.bigrams("") == set()
    assert ngram.bigrams("甲") == {"甲"}


def test_block_build_shared_pair():
    records = [_record("S-1", "华远物流"), _record("S-2", "华远物流"),
               _record("S-3", "华远物流")]
    result = blocking.build(records)
    assert len(result["pairs"]) == 3
    assert result["pairs"][0]["pair_id"] == "P-00001"
    shared = json.loads(result["pairs"][0]["shared_keys"])
    assert "华远" in shared


def test_pair_appears_once_across_blocks():
    records = [_record("S-1", "华远物流"), _record("S-2", "华远物流服务")]
    result = blocking.build(records)
    assert len(result["pairs"]) == 1
    shared = json.loads(result["pairs"][0]["shared_keys"])
    assert len(shared) >= 2


def test_oversized_block_skipped():
    records = [_record("S-1", "华远物流"), _record("S-2", "华远物流")]
    result = blocking.build(records, max_block_size=1)
    assert result["pairs"] == []
    assert result["skipped"]
    assert result["skipped"][0]["member_count"] == 2


def test_truncated_candidates():
    records = [_record(f"S-{index}", "华远物流") for index in range(4)]
    result = blocking.build(records, max_candidates=2)
    assert len(result["pairs"]) == 2
    assert result["truncated"] == 4


def test_pair_ids_deterministic():
    records = [_record("S-3", "华远物流"), _record("S-1", "华远物流"),
               _record("S-2", "华远物流")]
    first = blocking.build(records)["pairs"]
    second = blocking.build(list(reversed(records)))["pairs"]
    assert first == second
    assert [item["pair_id"] for item in first] == ["P-00001", "P-00002", "P-00003"]


def test_ensure_blocks_idempotent(run):
    first = service.ensure_blocks(run["run_id"])
    second = service.ensure_blocks(run["run_id"])
    assert first["block_count"] == second["block_count"] > 0
    assert first["pair_count"] == second["pair_count"] > 0
    assert len(store.list_blocks(run["run_id"])) == first["block_count"]


def test_blocks_api(client):
    response = client.post("/api/blocks")
    assert response.status_code == 200
    body = response.json()
    assert body["pair_count"] > 0
    assert body["max_block"] <= 120
    listing = client.get("/api/blocks")
    assert listing.status_code == 200
    assert listing.json()["items"]
