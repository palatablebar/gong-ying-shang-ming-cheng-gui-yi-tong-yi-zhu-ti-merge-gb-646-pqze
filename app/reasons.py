"""原因码唯一来源：采信、归一、分块、相似、合并、复核、导出共用一张表。"""
from __future__ import annotations

# 采信层
E_NO_ROW = "E_NO_ROW"
E_HEADER_ONLY = "E_HEADER_ONLY"
E_BLANK_ROWS = "E_BLANK_ROWS"
E_MISSING_COLUMN = "E_MISSING_COLUMN"
E_FILE_MISSING = "E_FILE_MISSING"
E_DECODE_FAILED = "E_DECODE_FAILED"

# 质量与隔离
Q_ROW_SHORT = "Q_ROW_SHORT"
Q_ROW_LONG = "Q_ROW_LONG"
Q_ROW_BLANK = "Q_ROW_BLANK"
Q_ID_MISSING = "Q_ID_MISSING"
Q_NAME_MISSING = "Q_NAME_MISSING"
Q_NAME_TOO_SHORT = "Q_NAME_TOO_SHORT"
Q_AMOUNT_INVALID = "Q_AMOUNT_INVALID"
Q_DUP_ID_SAME = "Q_DUP_ID_SAME"

# 字段级标记（不隔离，随行记录）
F_AMOUNT_SENTINEL = "F_AMOUNT_SENTINEL"
F_TAX_SENTINEL = "F_TAX_SENTINEL"
F_AMOUNT_NEGATIVE = "F_AMOUNT_NEGATIVE"

# 引用一致性
X_REF_UNKNOWN = "X_REF_UNKNOWN"
X_REF_SELF = "X_REF_SELF"
X_REF_CYCLE = "X_REF_CYCLE"
X_REF_NOT_MASTER = "X_REF_NOT_MASTER"

# 候选对与相似判定
P_TAX_CONFLICT = "P_TAX_CONFLICT"
P_TAX_MATCH = "P_TAX_MATCH"
P_CITY_MISMATCH = "P_CITY_MISMATCH"
P_AUTO = "P_AUTO"
P_REVIEW = "P_REVIEW"
P_REJECT = "P_REJECT"
D_ID_CONFLICT = "D_ID_CONFLICT"

# 合并簇
C_CLUSTER_CONFLICT = "C_CLUSTER_CONFLICT"
C_SINGLETON = "C_SINGLETON"

# 复核与批次
V_STALE_DECISION = "V_STALE_DECISION"
V_UNKNOWN_PAIR = "V_UNKNOWN_PAIR"
V_UNKNOWN_RUN = "V_UNKNOWN_RUN"
V_BAD_DECISION = "V_BAD_DECISION"
V_BAD_WINDOW = "V_BAD_WINDOW"

_LABELS = {
    E_NO_ROW: "无数据行",
    E_HEADER_ONLY: "仅表头",
    E_BLANK_ROWS: "全空行",
    E_MISSING_COLUMN: "缺列",
    E_FILE_MISSING: "文件不存在",
    E_DECODE_FAILED: "解码失败",
    Q_ROW_SHORT: "列数不足",
    Q_ROW_LONG: "列数过多",
    Q_ROW_BLANK: "空行",
    Q_ID_MISSING: "缺供应商号",
    Q_NAME_MISSING: "缺名称",
    Q_NAME_TOO_SHORT: "名称过短",
    Q_AMOUNT_INVALID: "金额不可解析",
    Q_DUP_ID_SAME: "重复行已剔除",
    F_AMOUNT_SENTINEL: "金额为空值哨兵",
    F_TAX_SENTINEL: "税号为空值哨兵",
    F_AMOUNT_NEGATIVE: "金额为负数",
    X_REF_UNKNOWN: "主档号不存在",
    X_REF_SELF: "自引用",
    X_REF_CYCLE: "引用成环",
    X_REF_NOT_MASTER: "指向非主档",
    P_TAX_CONFLICT: "税号冲突",
    P_TAX_MATCH: "税号相同",
    P_CITY_MISMATCH: "城市不同",
    P_AUTO: "自动合并",
    P_REVIEW: "人工复核",
    P_REJECT: "不予合并",
    D_ID_CONFLICT: "同号不同值",
    C_CLUSTER_CONFLICT: "簇内税号冲突",
    C_SINGLETON: "单记录主体",
    V_STALE_DECISION: "复核版本过期",
    V_UNKNOWN_PAIR: "候选对不存在",
    V_UNKNOWN_RUN: "批次不存在",
    V_BAD_DECISION: "复核动作非法",
    V_BAD_WINDOW: "时间窗非法",
}

BLOCK_CODES = (E_NO_ROW, E_HEADER_ONLY, E_BLANK_ROWS, E_MISSING_COLUMN,
               E_FILE_MISSING, E_DECODE_FAILED)
QUARANTINE_CODES = (Q_ROW_SHORT, Q_ROW_LONG, Q_ROW_BLANK, Q_ID_MISSING, Q_NAME_MISSING,
                    Q_NAME_TOO_SHORT, Q_AMOUNT_INVALID, Q_DUP_ID_SAME)
FLAG_CODES = (F_AMOUNT_SENTINEL, F_TAX_SENTINEL, F_AMOUNT_NEGATIVE)
REFERENCE_CODES = (X_REF_UNKNOWN, X_REF_SELF, X_REF_CYCLE, X_REF_NOT_MASTER)
PAIR_CODES = (P_TAX_CONFLICT, P_TAX_MATCH, P_CITY_MISMATCH, P_AUTO, P_REVIEW, P_REJECT)
DECISION_CODES = (V_STALE_DECISION, V_UNKNOWN_PAIR, V_UNKNOWN_RUN, V_BAD_DECISION,
                  V_BAD_WINDOW)
CLUSTER_CODES = (C_CLUSTER_CONFLICT, C_SINGLETON)
ID_CODES = (D_ID_CONFLICT,)

GROUPS = {
    "block": BLOCK_CODES,
    "quarantine": QUARANTINE_CODES,
    "flag": FLAG_CODES,
    "reference": REFERENCE_CODES,
    "pair": PAIR_CODES,
    "cluster": CLUSTER_CODES,
    "id": ID_CODES,
    "decision": DECISION_CODES,
}


def label_of(code: str) -> str:
    return _LABELS.get(code, code)


def all_codes() -> dict:
    return dict(_LABELS)


def group_of(code: str) -> str:
    for name, codes in GROUPS.items():
        if code in codes:
            return name
    return "other"


def code_table() -> list:
    return [{"code": code, "label": label, "group": group_of(code)}
            for code, label in _LABELS.items()]
