"""M1 名录采信编排：解码 → 逐行校验 → 去重与冲突归因 → 落库。

输入摘要取 (文件名, sha256) 的字典序拼接，因此同一批文件必然得到同一个 run_id；
重跑命中已有批次时只复用结果，不新增行。
"""
from __future__ import annotations

import hashlib
import json

from ... import store
from ...config import RULE_VERSION, SAMPLE_DIR, SAMPLE_FILES
from ...errors import DomainError, NotFound
from ...manifest import combined_digest, run_id_for, utc_iso, utc_now
from ...reasons import (
    D_ID_CONFLICT,
    E_FILE_MISSING,
    Q_AMOUNT_INVALID,
    Q_DUP_ID_SAME,
    Q_ID_MISSING,
    Q_NAME_MISSING,
    Q_NAME_TOO_SHORT,
    Q_ROW_BLANK,
    Q_ROW_LONG,
    Q_ROW_SHORT,
)
from . import columns, decode, reader

PAYLOAD_FIELDS = ("supplier_no", "raw_name", "tax_id", "city", "bank_account",
                  "erp", "ref_master_id", "ytd_amount")


def _safe_name(name: str) -> str:
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise DomainError(E_FILE_MISSING, "文件名非法")
    return name


def ensure_run(force: bool = False) -> dict:
    latest = store.latest_run()
    if latest and not force:
        return latest
    return ingest(force=force)


def _quarantine(source, line_no, raw, code, detail=""):
    return {"source_file": source, "line_no": line_no, "raw_line": raw,
            "reason_code": code, "detail": detail}


def _row_record(index, cells, raw, source, line_no):
    values = {name: columns.cell(cells, index, name) for name in columns.COLUMN_NAMES}
    amount, amount_flags, amount_error = columns.parse_amount(values["ytd_amount"])
    tax_id, tax_flags = columns.clean_tax(values["tax_id"])
    return {
        "supplier_id": columns.clean_code(values["supplier_id"]),
        "supplier_no": columns.clean_code(values["supplier_no"]),
        "raw_name": values["name"].strip(),
        "tax_id": tax_id,
        "city": columns.clean_text(values["city"]),
        "bank_account": columns.clean_code(values["bank_account"]),
        "erp": columns.clean_text(values["erp_source"]),
        "ref_master_id": columns.clean_code(values["ref_master_id"]),
        "ytd_amount": str(amount if amount is not None else "0.00"),
        "flags": json.dumps(sorted(set(amount_flags + tax_flags)), ensure_ascii=False),
        "source_file": source,
        "line_no": line_no,
        "raw_line": raw,
    }, amount_error


def ingest(files=None, force: bool = False) -> dict:
    started = utc_now()
    names = tuple(_safe_name(name) for name in (files or SAMPLE_FILES))
    digests, file_stats = [], []
    accepted, quarantine, conflicts = [], [], []

    for source in names:
        path = SAMPLE_DIR / source
        if not path.is_file():
            raise NotFound(E_FILE_MISSING, source)
        data = path.read_bytes()
        file_sha = hashlib.sha256(data).hexdigest()
        digests.append((source, file_sha))
        decoded = decode.decode_bytes(data)
        parsed = reader.parse_stream(decoded.text)
        header = columns.normalize_header(parsed.header)
        index = columns.map_columns(header)
        state = reader.empty_state(header, parsed.rows, parsed.blank_lines)
        blank_in_data = len(parsed.blank_lines) if parsed.rows else 0
        data_rows = len(parsed.rows) + blank_in_data
        file_start = len(quarantine)

        for rec in parsed.rows:
            if len(rec.cells) < len(header):
                quarantine.append(_quarantine(source, rec.line_no, rec.raw, Q_ROW_SHORT,
                                              f"{len(rec.cells)}/{len(header)}"))
                continue
            if len(rec.cells) > len(header):
                quarantine.append(_quarantine(source, rec.line_no, rec.raw, Q_ROW_LONG,
                                              f"{len(rec.cells)}/{len(header)}"))
                continue
            record, amount_error = _row_record(index, rec.cells, rec.raw, source, rec.line_no)
            if not record["supplier_id"]:
                quarantine.append(_quarantine(source, rec.line_no, rec.raw, Q_ID_MISSING))
                continue
            if not record["raw_name"]:
                quarantine.append(_quarantine(source, rec.line_no, rec.raw, Q_NAME_MISSING))
                continue
            if len(record["raw_name"]) < 4:
                quarantine.append(_quarantine(source, rec.line_no, rec.raw, Q_NAME_TOO_SHORT))
                continue
            if amount_error:
                quarantine.append(_quarantine(source, rec.line_no, rec.raw, Q_AMOUNT_INVALID,
                                              record["ytd_amount"]))
                continue
            accepted.append(record)

        for line_no in parsed.blank_lines:
            if parsed.rows:
                quarantine.append(_quarantine(source, line_no, "", Q_ROW_BLANK))

        file_stats.append({
            "name": source,
            "sha256": file_sha,
            "bytes": len(data),
            "encoding": decoded.encoding,
            "bom_removed": decoded.bom_removed,
            "segments": parsed.segments,
            "data_rows": data_rows,
            "blank_rows": blank_in_data,
            "accepted": len([r for r in accepted if r["source_file"] == source]),
            "quarantined": len(quarantine) - file_start,
            "empty_state": state,
            "columns": len(header),
        })

    unique, seen = [], {}
    for record in accepted:
        previous = seen.get(record["supplier_id"])
        if previous is None:
            seen[record["supplier_id"]] = record
            unique.append(record)
            continue
        if columns.identical(previous, record, PAYLOAD_FIELDS):
            quarantine.append(_quarantine(record["source_file"], record["line_no"],
                                          record["raw_line"], Q_DUP_ID_SAME,
                                          f"保留 {previous['source_file']}:{previous['line_no']}"))
            continue
        changed = columns.differing_fields(previous, record, PAYLOAD_FIELDS)
        conflicts.append({
            "supplier_id": record["supplier_id"],
            "field": ",".join(changed),
            "kept": f"{previous['source_file']}:{previous['line_no']}",
            "rejected": f"{record['source_file']}:{record['line_no']}",
            "reason_code": D_ID_CONFLICT,
            "source_file": record["source_file"],
            "line_no": record["line_no"],
        })

    input_rows = sum(item["data_rows"] for item in file_stats)
    combined = combined_digest(digests)
    run_id = run_id_for(combined, RULE_VERSION)
    existing = store.get_run(run_id)
    if existing and not force:
        return existing

    elapsed = int((utc_now() - started).total_seconds() * 1000)
    counts = {
        "input_rows": input_rows,
        "accepted": len(unique),
        "quarantined": len(quarantine),
        "conflicts": len(conflicts),
        "files": len(file_stats),
    }
    run = {
        "run_id": run_id,
        "input_sha256": combined,
        "rule_version": RULE_VERSION,
        "params_json": json.dumps({"files": list(names), "force": force}, ensure_ascii=False),
        "created_at": utc_iso(started),
        "elapsed_ms": elapsed,
        "counts_json": json.dumps(counts, ensure_ascii=False, sort_keys=True),
        "files_json": json.dumps(file_stats, ensure_ascii=False),
    }
    store.clear_stage(run_id, "intake")
    store.clear_stage(run_id, "normalize")
    store.save_records(run_id, unique)
    store.save_quarantine(run_id, quarantine)
    store.save_conflicts(run_id, conflicts)
    store.save_run(run)
    return store.get_run(run_id)


def summary(run_id: str) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise NotFound(E_FILE_MISSING, run_id)
    return {
        "run_id": run["run_id"],
        "input_sha256": run["input_sha256"],
        "rule_version": run["rule_version"],
        "created_at": run["created_at"],
        "elapsed_ms": run["elapsed_ms"],
        "counts": json.loads(run["counts_json"] or "{}"),
        "files": file_diagnostics(run_id),
        "quarantined": len(store.list_quarantine(run_id)),
        "conflicts": len(store.list_conflicts(run_id)),
    }


def file_diagnostics(run_id: str) -> list:
    run = store.get_run(run_id)
    if not run:
        return []
    return json.loads(run.get("files_json") or "[]")


def load_records(run_id: str) -> list:
    return store.list_records(run_id)
