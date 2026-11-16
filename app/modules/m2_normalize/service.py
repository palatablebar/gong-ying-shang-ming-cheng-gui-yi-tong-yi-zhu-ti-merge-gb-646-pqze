"""M2 名称归一编排：批量归一、规则命中统计、单条预览。"""
from __future__ import annotations

import json
from collections import Counter

from ... import store
from ...errors import NotFound
from ...reasons import V_UNKNOWN_RUN
from . import rules


def ensure_normalized(run_id: str) -> dict:
    records = store.list_records(run_id)
    if not records:
        raise NotFound(V_UNKNOWN_RUN, run_id)
    pending = [record for record in records if not record["norm_name"]]
    for record in pending:
        result = rules.normalize(record["raw_name"])
        store.update_norm(run_id, record["supplier_id"], result.name,
                          json.dumps(result.codes, ensure_ascii=False))
    return summary(run_id)


def summary(run_id: str) -> dict:
    records = store.list_records(run_id)
    hits = Counter()
    changed = 0
    empty = 0
    for record in records:
        codes = json.loads(record["norm_codes"] or "[]")
        hits.update(codes)
        if codes:
            changed += 1
        if not record["norm_name"]:
            empty += 1
    return {
        "total": len(records),
        "changed": changed,
        "unchanged": len(records) - changed,
        "empty": empty,
        "rule_hits": [{"code": code, "label": rules.RULE_LABELS[code], "count": hits[code]}
                      for code in rules.RULE_ORDER],
        "distinct": len({record["norm_name"] for record in records if record["norm_name"]}),
    }


def preview(raw: str) -> dict:
    result = rules.normalize(raw)
    return {
        "raw": raw,
        "normalized": result.name,
        "codes": result.codes,
        "labels": [rules.RULE_LABELS[code] for code in result.codes],
        "changed": result.name != raw.strip(),
    }
