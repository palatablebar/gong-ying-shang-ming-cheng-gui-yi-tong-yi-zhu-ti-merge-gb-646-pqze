"""分块候选：bigram 倒排桶；超大桶按上限跳过并单独计数。"""
from __future__ import annotations

import json

from ...config import MAX_BLOCK_SIZE, MAX_CANDIDATES
from . import ngram


def build(records, max_block_size: int = MAX_BLOCK_SIZE,
          max_candidates: int = MAX_CANDIDATES) -> dict:
    """返回 blocks / pairs / skipped / truncated。same pair 只出现一次。"""
    index = {}
    for record in sorted(records, key=lambda item: item["supplier_id"]):
        for gram in ngram.bigrams(record["norm_name"] or record["raw_name"]):
            index.setdefault(gram, []).append(record["supplier_id"])

    blocks, skipped = [], []
    pair_keys = {}
    for gram in sorted(index):
        members = sorted(index[gram])
        if len(members) < 2:
            continue
        if len(members) > max_block_size:
            skipped.append({"block_key": gram, "member_count": len(members)})
            continue
        blocks.append({"block_key": gram, "member_count": len(members)})
        for left_position in range(len(members)):
            for right_position in range(left_position + 1, len(members)):
                key = (members[left_position], members[right_position])
                pair_keys.setdefault(key, set()).add(gram)

    ordered = sorted(pair_keys)
    truncated = max(0, len(ordered) - max_candidates)
    ordered = ordered[:max_candidates]
    pairs = [
        {
            "pair_id": f"P-{position:05d}",
            "left_id": left,
            "right_id": right,
            "shared_keys": json.dumps(sorted(pair_keys[(left, right)]), ensure_ascii=False),
        }
        for position, (left, right) in enumerate(ordered, 1)
    ]
    return {"blocks": blocks, "pairs": pairs, "skipped": skipped, "truncated": truncated}
