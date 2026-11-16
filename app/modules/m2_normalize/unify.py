"""字符级归一：全角转半角、括号统一、去空白、去标点、拉丁小写。"""
from __future__ import annotations

import re

_FULLWIDTH_START, _FULLWIDTH_END = 0xFF01, 0xFF5E
_OFFSET = 0xFEE0

BRACKETS = {
    "（": "(", "）": ")",
    "〔": "(", "〕": ")",
    "【": "[", "】": "]",
    "〖": "[", "〗": "]",
    "〈": "<", "〉": ">",
    "《": "<", "》": ">",
    "「": "(", "」": ")",
    "『": "(", "』": ")",
    "【": "[", "】": "]",
}

_SPACES = re.compile(r"[\s\u3000\u00a0]+")
_PUNCT = re.compile(r"[\s\u3000·・,，.。、;；:：'\"“”‘’_\-—–~～!！?？/\\|+&*#@%$^]+")


def to_halfwidth(text: str) -> str:
    """全角 ASCII 与全角空格转半角，其他字符原样保留。"""
    out = []
    for char in text:
        code = ord(char)
        if _FULLWIDTH_START <= code <= _FULLWIDTH_END:
            out.append(chr(code - _OFFSET))
        elif code == 0x3000:
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)


def unify_brackets(text: str) -> str:
    return "".join(BRACKETS.get(char, char) for char in text)


def strip_spaces(text: str) -> str:
    return _SPACES.sub("", text)


def strip_punctuation(text: str) -> str:
    return _PUNCT.sub("", text)


def lower_latin(text: str) -> str:
    return text.lower()


def collapse_double_brackets(text: str) -> str:
    """空括号与连续括号压平：'()' 与 '()()' 不产生新的名称。"""
    previous = None
    while previous != text:
        previous = text
        text = text.replace("()", "").replace("[]", "").replace("<>", "")
    return text
