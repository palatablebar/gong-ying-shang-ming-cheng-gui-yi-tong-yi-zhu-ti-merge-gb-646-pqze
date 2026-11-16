"""隔离区 CSV：原始行号 + 原因码 + 原值，供人工复核。"""
from __future__ import annotations

import csv
import io

from ...reasons import label_of

HEADER = ("来源文件", "行号", "原因码", "原因", "详情", "原始内容")


def render(rows) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow([
            row["source_file"],
            row["line_no"],
            row["reason_code"],
            label_of(row["reason_code"]),
            row.get("detail", ""),
            (row.get("raw_line") or "").replace("\n", " "),
        ])
    return buffer.getvalue()


def render_conflicts(rows) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("供应商号", "差异字段", "保留来源", "剔除来源", "原因码", "原因"))
    for row in rows:
        writer.writerow([row["supplier_id"], row["field"], row["kept"], row["rejected"],
                         row["reason_code"], label_of(row["reason_code"])])
    return buffer.getvalue()
