"""法律后缀与行政区域标记剥离：顺序固定，剥离后长度不足即停止。"""
from __future__ import annotations

LEGAL_SUFFIXES = (
    "集团股份有限公司",
    "集团有限责任公司",
    "股份有限公司",
    "有限责任公司",
    "控股有限公司",
    "集团有限公司",
    "有限公司",
    "集团",
    "控股",
    "公司",
)

REGIONS = (
    "北京", "上海", "天津", "重庆", "广州", "深圳", "杭州", "南京", "苏州",
    "成都", "武汉", "西安", "青岛", "长沙", "合肥", "济南", "福州", "郑州",
    "昆明", "沈阳", "哈尔滨", "长春", "石家庄", "太原", "南昌", "贵阳", "南宁",
    "兰州", "银川", "乌鲁木齐", "大连", "无锡", "宁波", "厦门", "佛山", "东莞",
)

MIN_STEM = 2


def strip_legal_suffix(text: str) -> tuple:
    """反复剥离结尾法律后缀；剩余主体不足 2 字则保留原文。"""
    changed = False
    guard = 0
    while guard < 4:
        guard += 1
        hit = ""
        for suffix in LEGAL_SUFFIXES:
            if text.endswith(suffix) and len(text) - len(suffix) >= MIN_STEM:
                hit = suffix
                break
        if not hit:
            break
        text = text[: -len(hit)]
        changed = True
    return text, changed


def _region_token(token: str) -> bool:
    return any(token == region or token.startswith(region) for region in REGIONS)


def strip_region(text: str) -> tuple:
    """剥离括号内的地名与开头地名；开头剥离后仍需保留 4 字以上。"""
    changed = False
    guard = 0
    while guard < 4 and text.endswith(")"):
        guard += 1
        depth = 0
        for position in range(len(text) - 1, -1, -1):
            char = text[position]
            if char == ")":
                depth += 1
            elif char == "(":
                depth -= 1
                if depth == 0:
                    inner = text[position + 1: -1]
                    if _region_token(inner) and position >= MIN_STEM:
                        text = text[:position]
                        changed = True
                    break
        else:
            break
        if not text.endswith(")"):
            break
    for region in REGIONS:
        if not text.startswith(region):
            continue
        rest = text[len(region):]
        if rest[:1] in ("市", "省") and len(rest) - 1 >= 4:
            text, changed = rest[1:], True
            break
        if len(rest) >= 4:
            text, changed = rest, True
            break
    return text, changed
