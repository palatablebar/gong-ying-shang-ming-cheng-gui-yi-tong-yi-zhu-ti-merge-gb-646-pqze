"""归一规则序列：编号固定、可单独调用、结果与调用次数无关。"""
from __future__ import annotations

from dataclasses import dataclass

from . import suffix, unify

RULE_LABELS = {
    "N01": "全角转半角",
    "N02": "括号统一",
    "N03": "去空白",
    "N04": "去法律后缀",
    "N05": "去地名标记",
    "N06": "拉丁小写",
    "N07": "去标点",
}

RULE_ORDER = ("N01", "N02", "N03", "N04", "N05", "N06", "N07")


@dataclass
class Normalized:
    name: str
    codes: list


def normalize(raw: str) -> Normalized:
    codes = []
    text = raw.strip()
    step = unify.to_halfwidth(text)
    if step != text:
        codes.append("N01")
    text = step

    step = unify.unify_brackets(text)
    if step != text:
        codes.append("N02")
    text = step

    step = unify.strip_spaces(text)
    if step != text:
        codes.append("N03")
    text = step

    step, changed = suffix.strip_legal_suffix(text)
    if changed:
        codes.append("N04")
    text = step

    step, changed = suffix.strip_region(text)
    if changed:
        codes.append("N05")
    text = step

    step = unify.lower_latin(text)
    if step != text:
        codes.append("N06")
    text = step

    step = unify.strip_punctuation(unify.collapse_double_brackets(text))
    if step != text:
        codes.append("N07")
    text = step
    return Normalized(name=text, codes=codes)


def normalize_text(raw: str) -> str:
    return normalize(raw).name


def changed(raw: str) -> bool:
    return normalize(raw).name != raw.strip()
