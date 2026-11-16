"""簇内金额分摊：按权重比例，最大余额法补齐到分，合计守恒。"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

CENT = Decimal("0.01")


def _round_down(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_DOWN)


def allocate(total: Decimal, weights) -> list:
    """weights: [(supplier_id, Decimal)]；返回 [(supplier_id, Decimal)]，顺序同输入。"""
    total = Decimal(str(total)).quantize(CENT)
    if not weights:
        return []
    if total < 0:
        return [(key, -value) for key, value in allocate(-total, weights)]
    weight_sum = sum((Decimal(str(weight)) for _, weight in weights), Decimal("0"))
    if weight_sum == 0:
        even = [Decimal("1") for _ in weights]
        weight_sum = Decimal(len(weights))
        shares = [total * item / weight_sum for item in even]
    else:
        shares = [total * Decimal(str(weight)) / weight_sum for _, weight in weights]
    floors = [_round_down(share) for share in shares]
    remainder = total - sum(floors, Decimal("0"))
    units = int((remainder / CENT).to_integral_value(rounding=ROUND_DOWN))
    fractions = sorted(
        range(len(weights)),
        key=lambda index: (-(shares[index] - floors[index]), str(weights[index][0])),
    )
    for position in range(min(units, len(fractions))):
        floors[fractions[position]] += CENT
    return [(weights[index][0], floors[index]) for index in range(len(weights))]
