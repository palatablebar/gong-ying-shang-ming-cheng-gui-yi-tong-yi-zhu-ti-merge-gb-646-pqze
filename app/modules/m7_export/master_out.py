"""主数据 CSV：一个主体一行，带成员、税号冲突与金额证据。"""
from __future__ import annotations

import csv
import io
from decimal import Decimal

HEADER = ("主体编号", "代表供应商号", "代表名称", "税号", "城市", "成员数",
          "本年累计(元)", "簇状态", "成员供应商号", "簇内税号")


def _status(cluster) -> str:
    return "税号冲突" if cluster["conflict"] else ("单记录" if cluster["member_count"] == 1 else "已合并")


def _cluster_taxes(cluster_id, by_cluster, records) -> list:
    taxes = {records[item].get("tax_id", "") for item in by_cluster.get(cluster_id, [])}
    return sorted(tax for tax in taxes if tax)


def render(clusters, members, records) -> str:
    by_cluster = {}
    for member in members:
        by_cluster.setdefault(member["cluster_id"], []).append(member["supplier_id"])
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for cluster in clusters:
        rep = records.get(cluster["rep_id"], {})
        writer.writerow([
            cluster["cluster_id"],
            cluster["rep_id"],
            rep.get("raw_name", ""),
            cluster["tax_id"],
            cluster["city"],
            cluster["member_count"],
            f"{Decimal(cluster['total_amount']):.2f}",
            _status(cluster),
            " ".join(sorted(by_cluster.get(cluster["cluster_id"], []))),
            ",".join(_cluster_taxes(cluster["cluster_id"], by_cluster, records)),
        ])
    return buffer.getvalue()


def render_members(clusters, members, records) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("主体编号", "供应商号", "名称", "税号", "本年累计(元)", "分摊(元)"))
    cluster_ids = {cluster["cluster_id"] for cluster in clusters}
    for member in members:
        if member["cluster_id"] not in cluster_ids:
            continue
        record = records.get(member["supplier_id"], {})
        writer.writerow([
            member["cluster_id"],
            member["supplier_id"],
            record.get("raw_name", ""),
            record.get("tax_id", ""),
            f"{Decimal(record.get('ytd_amount', '0')):.2f}",
            f"{Decimal(member['share_amount']):.2f}",
        ])
    return buffer.getvalue()
