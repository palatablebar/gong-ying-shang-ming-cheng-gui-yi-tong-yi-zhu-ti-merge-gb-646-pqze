"""付款边界 CSV：一个成员一行，每个成员金额只在可付或暂缓出现一次。"""
from __future__ import annotations

import csv
import io
from decimal import Decimal

HEADER = ("主体编号", "成员供应商号", "成员分摊(元)", "付款状态", "暂缓原因码", "待核候选对")


def render(result: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for cluster in result["held"] + result["payable"]:
        reasons = " ".join(cluster["hold_reasons"])
        pairs = " ".join(cluster["pending_pairs"])
        for member in cluster["members"]:
            writer.writerow([
                cluster["cluster_id"],
                member["supplier_id"],
                f"{Decimal(member['share_amount']):.2f}",
                member["status"],
                reasons,
                pairs,
            ])
    return buffer.getvalue()
