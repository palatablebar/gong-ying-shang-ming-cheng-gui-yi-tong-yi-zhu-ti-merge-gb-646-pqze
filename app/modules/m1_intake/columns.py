"""列契约与单值归一：表头映射、前导零保形、空值哨兵、金额 Decimal 化。"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from ...config import COLUMN_ALIASES, COLUMNS, SENTINEL_VALUES
from ...reasons import (
    E_MISSING_COLUMN,
    F_AMOUNT_NEGATIVE,
    F_AMOUNT_SENTINEL,
    F_TAX_SENTINEL,
    Q_AMOUNT_INVALID,
)
from ...errors import DomainError

COLUMN_NAMES = tuple(name for name, _required in COLUMNS)
REQUIRED_COLUMNS = tuple(name for name, required in COLUMNS if required)
CENT = Decimal("0.01")

# 采信层只处理数字与金额相关的全角字符；名称归一的括号/后缀规则在 M2。
_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９．，－", "0123456789.,-")


def normalize_header(cells) -> list:
    """去 BOM、去空白、别名映射到契约字段名。"""
    header = []
    for cell in cells:
        text = cell.replace("\ufeff", "").replace("\u3000", " ").strip()
        header.append(COLUMN_ALIASES.get(text, text))
    return header


def map_columns(header) -> dict:
    index = {}
    for position, name in enumerate(header):
        if name in COLUMN_NAMES and name not in index:
            index[name] = position
    missing = [name for name in REQUIRED_COLUMNS if name not in index]
    if missing:
        raise DomainError(E_MISSING_COLUMN, ",".join(missing))
    return index


def cell(cells, index: dict, name: str) -> str:
    position = index.get(name)
    if position is None or position >= len(cells):
        return ""
    return cells[position]


def is_sentinel(raw: str) -> bool:
    return raw.strip().lower() in SENTINEL_VALUES


def clean_code(raw: str) -> str:
    """编码类字段按字符串保形，不做 int() 化，前导零原样保留。"""
    return raw.strip().strip("\ufeff")


def clean_text(raw: str) -> str:
    value = raw.strip()
    if is_sentinel(value):
        return ""
    return value


def clean_tax(raw: str) -> tuple:
    value = raw.strip()
    if value == "":
        return "", []
    if is_sentinel(value):
        return "", [F_TAX_SENTINEL]
    return value.replace(" ", "").upper(), []


def parse_amount(raw: str):
    """返回 (金额, 标记列表, 错误码)。金额四舍五入到分。"""
    value = raw.strip()
    if value == "" or is_sentinel(value):
        return Decimal("0.00"), [F_AMOUNT_SENTINEL], None
    normalized = value.translate(_FULLWIDTH_DIGITS)
    normalized = normalized.replace(",", "").replace("，", "").replace(" ¥", "").replace("¥", "")
    normalized = normalized.replace(" ", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None, [], Q_AMOUNT_INVALID
    flags = []
    if amount < 0:
        flags.append(F_AMOUNT_NEGATIVE)
    return amount.quantize(CENT, rounding=ROUND_HALF_UP), flags, None


def identical(left: dict, right: dict, fields) -> bool:
    return all(str(left.get(name, "")) == str(right.get(name, "")) for name in fields)


def differing_fields(left: dict, right: dict, fields) -> list:
    return [name for name in fields if str(left.get(name, "")) != str(right.get(name, ""))]
