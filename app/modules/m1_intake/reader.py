"""流式 CSV 解析：保留物理行号、识别分段重复表头、统计空行。"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field


@dataclass
class RawRecord:
    line_no: int
    cells: tuple
    raw: str
    end_line: int = 0


@dataclass
class Parsed:
    header: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    blank_lines: list = field(default_factory=list)
    segments: int = 1
    total_records: int = 0


def _is_blank(cells) -> bool:
    return all((cell or "").strip() == "" for cell in cells)


def parse_stream(text: str, has_header: bool = True) -> Parsed:
    """逐条读取；引号内换行不会被拆成两条记录。"""
    physical = text.splitlines()
    stream = io.StringIO(text, newline="")
    reader = csv.reader(stream)
    parsed = Parsed()
    previous_end = 0
    for cells in reader:
        start = previous_end + 1
        end = reader.line_num
        previous_end = end
        raw = "\n".join(physical[start - 1:end])
        parsed.total_records += 1
        if has_header and not parsed.header:
            parsed.header = list(cells)
            continue
        if _is_blank(cells):
            parsed.blank_lines.append(start)
            continue
        if has_header and list(cells) == parsed.header:
            parsed.segments += 1
            continue
        parsed.rows.append(RawRecord(line_no=start, cells=tuple(cells), raw=raw, end_line=end))
    return parsed


def empty_state(header, rows, blank_lines) -> str:
    """空态三态：仅表头 / 全空行 / 无数据行，三者结论不同。"""
    if rows:
        return ""
    if header and blank_lines:
        return "blank_rows"
    if header:
        return "header_only"
    return "no_row"
