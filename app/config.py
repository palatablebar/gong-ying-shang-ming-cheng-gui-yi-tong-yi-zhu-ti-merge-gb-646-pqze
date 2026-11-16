"""跨模块唯一来源的常量：路径、规则版本、阈值、列契约、空值哨兵。"""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BASE_DIR / "sample_data"

APP_NAME = "供应商主数据台账"
RULE_VERSION = "em-1.3.0"

DB_PATH = Path(os.environ.get("MERGE_DB", str(BASE_DIR / "data" / "merge.db")))

# 采信顺序固定，保证同一批文件得到同一个输入摘要与 run_id。
SAMPLE_FILES = (
    "erp_a_primary_utf8.csv",
    "erp_b_alias_bom.csv",
    "erp_c_north_gb18030.csv",
    "erp_d_amounts.csv",
    "erp_e_header_only.csv",
    "erp_f_blank_rows.csv",
)

ENCODING_CHAIN = ("utf-8-sig", "utf-8", "gb18030")

# 列契约：字段名 -> (是否必填, 说明单位)
COLUMNS = (
    ("supplier_id", True),
    ("supplier_no", True),
    ("name", True),
    ("tax_id", False),
    ("city", False),
    ("bank_account", False),
    ("erp_source", False),
    ("ref_master_id", False),
    ("ytd_amount", False),
    ("last_update", False),
)

COLUMN_ALIASES = {
    "供应商编码": "supplier_id",
    "供应商号": "supplier_id",
    "供应商编号": "supplier_no",
    "编码": "supplier_no",
    "名称": "name",
    "供应商名称": "name",
    "税号": "tax_id",
    "纳税人识别号": "tax_id",
    "城市": "city",
    "开户行账号": "bank_account",
    "来源系统": "erp_source",
    "主档号": "ref_master_id",
    "本年累计": "ytd_amount",
    "更新时间": "last_update",
}

# 空值哨兵：集中定义，与"空串"语义分开（空串表示确实没有税号）。
SENTINEL_VALUES = frozenset({"-", "--", "n/a", "na", "null", "none", "未知", "无", "空", "/"})

SIMILARITY_WEIGHT_DICE = Decimal("0.55")
SIMILARITY_WEIGHT_RATIO = Decimal("0.45")
AUTO_THRESHOLD = Decimal("0.92")
REVIEW_THRESHOLD = Decimal("0.80")
SCORE_SCALE = Decimal("0.000001")

MAX_BLOCK_SIZE = 120
MAX_CANDIDATES = 4000

TZ_DISPLAY = "Asia/Shanghai"
PAGE_SIZE = 60
