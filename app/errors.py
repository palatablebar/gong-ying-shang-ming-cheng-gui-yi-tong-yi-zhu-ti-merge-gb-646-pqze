"""领域异常与 HTTP 映射：失败输入一律 4xx，带稳定原因码。"""
from __future__ import annotations

from .reasons import label_of


class DomainError(Exception):
    """带原因码的业务失败。"""

    def __init__(self, code: str, detail: str = "", status: int = 400):
        self.code = code
        self.detail = detail
        self.status = status
        super().__init__(f"{code} {detail}".strip())

    def as_body(self) -> dict:
        return {
            "reason_code": self.code,
            "reason": label_of(self.code),
            "detail": self.detail,
        }


class NotFound(DomainError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code, detail, status=404)


class Conflict(DomainError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code, detail, status=409)
