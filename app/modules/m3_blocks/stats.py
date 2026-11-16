"""分块统计：桶数、候选对数、最大桶、被跳过的桶。"""
from __future__ import annotations


def summarize(blocks, pairs, skipped, truncated) -> dict:
    sizes = [block["member_count"] for block in blocks]
    return {
        "block_count": len(blocks),
        "pair_count": len(pairs),
        "max_block": max(sizes) if sizes else 0,
        "avg_block": round(sum(sizes) / len(sizes), 2) if sizes else 0.0,
        "singletons": sum(1 for size in sizes if size == 1),
        "skipped_blocks": len(skipped),
        "skipped_members": sum(item["member_count"] for item in skipped),
        "truncated_pairs": truncated,
    }
