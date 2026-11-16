"""运行清单 JSON：run_id、输入摘要、参数、计数、对账结果。"""
from __future__ import annotations

import json


def render(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
