"""相似度：0.55 × 字符 bigram Dice + 0.45 × difflib 比率，结果量化到 6 位。

bigram 定义与 M3 分块共用同一函数，否则候选对与得分会对不上。
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher

from ...config import SCORE_SCALE, SIMILARITY_WEIGHT_DICE, SIMILARITY_WEIGHT_RATIO
from ..m3_blocks.ngram import bigrams


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(SCORE_SCALE, rounding=ROUND_HALF_UP)


def dice(left: str, right: str) -> Decimal:
    left_grams, right_grams = bigrams(left), bigrams(right)
    if not left_grams or not right_grams:
        return Decimal("0.000000")
    total = len(left_grams) + len(right_grams)
    return _quantize(Decimal(len(left_grams & right_grams) * 2) / Decimal(total))


def ratio(left: str, right: str) -> Decimal:
    scorer = SequenceMatcher(None, left, right, autojunk=False)
    return _quantize(Decimal(str(scorer.ratio())))


def score(left: str, right: str) -> dict:
    dice_value = dice(left, right)
    ratio_value = ratio(left, right)
    total = _quantize(dice_value * SIMILARITY_WEIGHT_DICE
                      + ratio_value * SIMILARITY_WEIGHT_RATIO)
    return {"dice": dice_value, "ratio": ratio_value, "score": total}
