"""运行清单：run_id、输入摘要、规则版本、参数与耗时。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import RULE_VERSION


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> datetime:
    raw = text.strip().replace(" ", "T")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined_digest(items) -> str:
    """按 (文件名, 摘要) 字典序拼接后取 sha256，保证与读取顺序无关。"""
    digest = hashlib.sha256()
    for name, file_sha in sorted(items):
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def run_id_for(combined_sha: str, rule_version: str = RULE_VERSION) -> str:
    """批次号由输入摘要与规则版本共同决定：规则升级后同输入会得到新批次。"""
    digest = hashlib.sha256()
    digest.update(combined_sha.encode("ascii"))
    digest.update(b"|")
    digest.update(rule_version.encode("utf-8"))
    return "MR-" + digest.hexdigest()[:12].upper()


def canonical_json(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_manifest(run: dict, files, reconcile: dict, reasons: list) -> dict:
    return {
        "run_id": run["run_id"],
        "rule_version": run.get("rule_version", RULE_VERSION),
        "created_at_utc": run["created_at"],
        "input_sha256": run["input_sha256"],
        "files": files,
        "parameters": json.loads(run.get("params_json") or "{}"),
        "elapsed_ms": run.get("elapsed_ms"),
        "counts": json.loads(run.get("counts_json") or "{}"),
        "reconcile": reconcile,
        "reason_codes": reasons,
    }
