"""分档阈值：≥0.92 自动、0.80-0.92 复核、其余拒绝。左闭右开界限固定。"""
from __future__ import annotations

from decimal import Decimal

from ...config import AUTO_THRESHOLD, REVIEW_THRESHOLD
from ...reasons import P_AUTO, P_REJECT, P_REVIEW

def band(score: Decimal) -> str:
    value = Decimal(str(score))
    if value >= AUTO_THRESHOLD:
        return "auto"
    if value >= REVIEW_THRESHOLD:
        return "review"
    return "reject"


def code_of(band_name: str) -> str:
    return {"auto": P_AUTO, "review": P_REVIEW}.get(band_name, P_REJECT)


def describe() -> dict:
    return {
        "auto": str(AUTO_THRESHOLD),
        "review": str(REVIEW_THRESHOLD),
        "weights": {"dice": "0.55", "ratio": "0.45"},
    }
