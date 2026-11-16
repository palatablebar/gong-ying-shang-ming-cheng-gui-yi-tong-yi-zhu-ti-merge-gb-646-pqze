"""字符 2-gram 与 3-gram：分块与相似度的共同底座。"""
from __future__ import annotations

import re

_GRAM_PUNCT = re.compile(r"[\s()\[\]{}<>·・,，.。、;；:：'\"“”‘’_\-—–~～!！?？/\\|+&*#@%$^]+")


def clean(name: str) -> str:
    return _GRAM_PUNCT.sub("", name.lower())


def bigrams(name: str) -> set:
    text = clean(name)
    if len(text) < 2:
        return {text} if text else set()
    return {text[index:index + 2] for index in range(len(text) - 1)}


def trigrams(name: str) -> set:
    text = clean(name)
    if len(text) < 3:
        return {text} if text else set()
    return {text[index:index + 3] for index in range(len(text) - 2)}


def shared(left: str, right: str) -> list:
    return sorted(bigrams(left) & bigrams(right))


def coverage(name: str) -> dict:
    text = clean(name)
    return {"chars": len(text), "bigrams": len(bigrams(name)), "trigrams": len(trigrams(name))}
