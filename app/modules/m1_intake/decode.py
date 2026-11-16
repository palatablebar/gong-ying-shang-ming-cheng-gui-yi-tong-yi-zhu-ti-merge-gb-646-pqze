"""编码探测与回退链：BOM 剥离、换行归一、失败带尝试顺序。"""
from __future__ import annotations

from dataclasses import dataclass, field

from ...config import ENCODING_CHAIN
from ...errors import DomainError
from ...reasons import E_DECODE_FAILED

BOM = b"\xef\xbb\xbf"

# 有 BOM 时必须先走 utf-8-sig（否则首列名残留 BOM）；无 BOM 时从 utf-8 起试。
BOM_CHAIN = ("utf-8-sig",) + tuple(item for item in ENCODING_CHAIN if item != "utf-8-sig")
PLAIN_CHAIN = tuple(item for item in ENCODING_CHAIN if item != "utf-8-sig")


@dataclass
class Decoded:
    text: str
    encoding: str
    bom_removed: bool
    attempts: tuple = field(default_factory=tuple)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def decode_bytes(data: bytes) -> Decoded:
    """按固定回退链解码；全部失败时抛出带尝试记录的领域错误。"""
    has_bom = data.startswith(BOM)
    bom_removed = has_bom
    tried = []
    for encoding in (BOM_CHAIN if has_bom else PLAIN_CHAIN):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            tried.append(encoding)
            continue
        return Decoded(
            text=normalize_newlines(text),
            encoding=encoding,
            bom_removed=bom_removed,
            attempts=tuple(tried + [encoding]),
        )
    raise DomainError(E_DECODE_FAILED, "回退链：" + ",".join(tried))


def strip_bom(text: str) -> str:
    return text.lstrip("\ufeff")
