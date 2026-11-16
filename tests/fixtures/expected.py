"""样例批次的期望值：由 sample_data/ 的六个脏文件固定。

改动样例数据时这份常量必须同步更新，否则测试失败是正确信号。
"""
from decimal import Decimal

RUN_ID = "MR-8FC3B362EC8F"

INPUT_ROWS = 73
ACCEPTED = 70
QUARANTINED = 2
CONFLICTS = 1

PAIRS = 106
PAIRS_AUTO = 46
PAIRS_REVIEW = 3
PAIRS_REJECT = 57

CLUSTERS = 38
MERGED_MEMBERS = 32
SINGLETONS = 19
CONFLICT_CLUSTERS = 1

AMOUNT_TOTAL = Decimal("1648046.17")
DISTINCT_NORMALIZED = 39

# 金鼎电子科技：通过空税号记录发生传递合并，簇内两个税号冲突。
CONFLICT_CLUSTER_ID = "C-0009"
CONFLICT_CLUSTER_REP = "S-0010"
CONFLICT_CLUSTER_TOTAL = Decimal("79200.00")
CONFLICT_CLUSTER_SHARES = (
    ("S-0010", Decimal("68000.00")),
    ("S-0028", Decimal("5200.00")),
    ("S-0071", Decimal("2600.00")),
    ("S-0072", Decimal("3400.00")),
)

# 同税号但名称仅部分相同：税额匹配优先于名称得分。
PAIR_TAX_MATCH = "P-00042"
PAIR_TAX_MATCH_SCORE = Decimal("0.772500")

# 同名不同城、税号不同：硬冲突拒绝。
PAIR_TAX_CONFLICT = "P-00015"

# 名称相同、城市不同、一侧无税号：降级为复核。
PAIR_CITY_MISMATCH = "P-00044"

# 名称近似、无税号：落在复核带。
PAIR_REVIEW = "P-00105"
PAIR_REVIEW_SCORE = Decimal("0.832778")

# 盛世文化传播与盛世文化：同税号但名称得分低，合计 22000 + 1500。
CLUSTER_SEQUENCE_TOTAL = Decimal("23500.00")
TAX_MATCH_CLUSTER_REP = "S-0012"
